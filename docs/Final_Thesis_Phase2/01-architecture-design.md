# 01 — Kiến trúc hệ thống AIOps RCA Platform

## 1. Định vị hệ thống

Hệ thống này **không phải** một sản phẩm giám sát thương mại. Nó là một **nền tảng nghiên cứu chạy được**, phục vụ ba mục đích đồng thời trên cùng một codebase:

| Mặt | Mô tả | Người dùng |
|---|---|---|
| Pipeline chạy được | Replay → detect → retrieve → judge → RCA → dashboard | Demo bảo vệ |
| Bộ khung thực nghiệm | Chạy config → sinh bảng chỉ số tái lập được | Luận văn |
| Mã nguồn mở | Repo có README reproduce | Cộng đồng, hội đồng |

Hệ quả thiết kế quan trọng: **không viết code demo riêng và code thực nghiệm riêng**. Cùng một pipeline, khác nhau ở nguồn dữ liệu đầu vào và chế độ ghi kết quả.

---

## 2. Hai chế độ vận hành

```text
replay mode (mặc định, dùng cho thực nghiệm + demo)
  Nezha dataset trên đĩa
    -> Stream Replayer phát lại theo watermark
    -> pipeline
    -> ghi vào ClickHouse + eval/results/<run_id>/

stream mode (dự phòng cho GĐ3, chỉ cần interface sẵn sàng)
  Kafka/Redpanda topic
    -> cùng pipeline
    -> ghi vào ClickHouse
```

Điểm chung: pipeline **không biết** nguồn dữ liệu đến từ đâu. Nó chỉ nhận `TelemetryWindow`. Việc này được đảm bảo bằng interface `SourceAdapter` (§5.1).

Trong GĐ2 chỉ implement `NezhaReplaySource`. `KafkaSource` để trống với `NotImplementedError` — có interface là đủ, không code sớm.

---

## 3. Sơ đồ tổng quan

```text
                    ┌──────────────────────────┐
   Nezha dataset ──►│  Stream Replayer         │
                    │  - watermark control     │
                    │  - speed multiplier      │
                    └────────────┬─────────────┘
                                 │  TelemetryWindow
                                 ▼
                    ┌──────────────────────────┐
                    │  Detector Service        │
                    │  - Isolation Forest 0.85 │
                    │  - Rescue Score gate     │
                    └────────────┬─────────────┘
                                 │  AlertCandidate
                                 ▼
                    ┌──────────────────────────┐
                    │  Retrieval Service       │  ◄── NHÁNH A
                    │  RetrievalStrategy:      │
                    │   · bm25_hybrid (baseline)
                    │   · temporal             │
                    │   · cross_modal          │
                    │   · graph                │
                    │   · hybrid_bm25_graph    │
                    └────────────┬─────────────┘
                                 │  RetrievalResult
                                 ▼
                    ┌──────────────────────────┐
                    │  Judge Service           │
                    │  - gemini-2.5-flash-lite │
                    │  - require_evidence      │
                    └────────────┬─────────────┘
                                 │  JudgedAlert (TRUE/FP/UNCERTAIN)
                                 │
                 ┌───────────────┴───────────────┐
                 │ (chỉ TRUE_ALERT, bất đồng bộ) │
                 ▼                               │
      ┌──────────────────────────┐               │
      │  RCA Agent               │ ◄── NHÁNH B   │
      │  1. Alert Grouping       │               │
      │  2. Propagation Analysis │               │
      │  3. Diagnostic Summary   │               │
      └────────────┬─────────────┘               │
                   │  Incident + DiagnosticReport │
                   ▼                              ▼
        ┌──────────────────┐         ┌──────────────────────┐
        │   PostgreSQL     │         │      ClickHouse      │
        │  incidents       │         │  fact_alert_eval     │
        │  diagnostics     │         │  fact_retrieval_trace│
        │  run_registry    │         │                      │
        └────────┬─────────┘         └──────────┬───────────┘
                 └─────────────┬────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  API (FastAPI)       │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Dashboard           │
                    │  timeline · alert    │
                    │  incident · experiment
                    └──────────────────────┘

        ┌──────────────────────────────────────┐
        │  Eval Harness (chạy độc lập, CLI)    │
        │  đọc config → chạy pipeline → results│
        └──────────────────────────────────────┘
```

---

## 4. Critical path và non-critical path

Kế thừa nguyên tắc từ dự án Gateway.

### 4.1 Critical path

```text
TelemetryWindow -> Detector -> Retrieval -> Judge -> JudgedAlert
```

Quy tắc:

- Không query ClickHouse trong vòng lặp xử lý window. Service graph và metadata nạp vào memory một lần, refresh theo lịch.
- Không chạy RCA Agent đồng bộ trong đường này.
- Mọi external call (LLM, DB) phải có timeout.
- Retrieval phải trả về trong `budget.timeout_ms`, quá hạn thì trả kết quả một phần kèm cờ `truncated=True`, không treo pipeline.

### 4.2 Non-critical path

```text
JudgedAlert(TRUE) -> hàng đợi -> RCA Agent -> Incident -> DiagnosticReport
```

Quy tắc:

- RCA Agent xử lý theo lô, không theo từng alert.
- Alert lỗi khi phân tích đi vào DLQ, ghi log rõ nguyên nhân, không nuốt lỗi.
- Toàn bộ path này có thể tắt bằng config `rca.enabled: false` khi chạy thực nghiệm Nhánh A.

---

## 5. Interface — phần quan trọng nhất của kiến trúc

Bốn interface dưới đây là xương sống. **Không được đổi signature** sau mốc M1 mà không cập nhật tài liệu này.

### 5.1 SourceAdapter

```python
from typing import Protocol, Iterator

class SourceAdapter(Protocol):
    name: str

    def stream(self) -> Iterator[TelemetryWindow]:
        """Phát ra window theo thứ tự thời gian, tôn trọng watermark."""
```

Implement trong GĐ2: `NezhaReplaySource`.

### 5.2 Detector

```python
class Detector(Protocol):
    name: str

    def score(self, window: TelemetryWindow) -> float:
        """Trả anomaly score đã chuẩn hóa [0, 1]."""

    def is_candidate(self, window: TelemetryWindow, score: float) -> bool:
        """Áp threshold. Rescue Score gate xử lý riêng ở tầng ngoài."""
```

Implement trong GĐ2: `IsolationForestDetector` (threshold 0.85).

### 5.3 RetrievalStrategy — trục chính của Nhánh A

```python
class RetrievalStrategy(Protocol):
    name: str

    def retrieve(
        self,
        candidate: AlertCandidate,
        budget: RetrievalBudget,
    ) -> RetrievalResult:
        ...
```

`RetrievalBudget`: `top_k`, `max_tokens`, `timeout_ms`.

`RetrievalResult`: `events: list[ContextEvent]`, `latency_ms: float`, `token_estimate: int`, `truncated: bool`, `debug: dict`.

**Quy tắc bất di bất dịch:** mọi biến thể RAG đều implement đúng interface này. Tham số riêng của từng biến thể (`hop`, `decay_factor`, `w_log`...) nằm trong constructor, đọc từ config — **không thêm vào signature của `retrieve`**.

Trường `debug` bắt buộc ghi lại vì sao mỗi event được chọn (score thành phần, khoảng cách graph, kênh nguồn). Đây là dữ liệu để chấm context precision thủ công và để viết phần phân tích trong luận văn.

### 5.4 Judge

```python
class Judge(Protocol):
    name: str

    def evaluate(
        self,
        candidate: AlertCandidate,
        context: RetrievalResult,
    ) -> JudgedAlert:
        """Trả về verdict TRUE_ALERT / FALSE_POSITIVE / UNCERTAIN kèm evidence."""
```

Implement: `LLMJudge` gọi một model API cố định (`gemini-2.5-flash-lite`, QĐ-013) qua cache; backend `mock` chỉ cho G-port.

---

## 6. Service breakdown

### 6.1 `services/replayer`

Trách nhiệm: đọc Nezha, dựng `TelemetryWindow`, phát theo watermark.

- Cấu hình: `speed_multiplier` (1.0 = thời gian thật, 0 = nhanh nhất có thể), `window_size`, `start_ts`, `end_ts`.
- Thực nghiệm luôn chạy `speed_multiplier: 0`. Demo chạy 10–60.
- Phải deterministic: cùng seed + cùng split → cùng chuỗi window.

### 6.2 `services/detector`

Trách nhiệm: chấm điểm bất thường, sinh `AlertCandidate`, áp Rescue Score gate.

Luồng:
```text
window
  -> Isolation Forest score
  -> nếu score >= 0.85          -> AlertCandidate (nguồn: metric)
  -> nếu score < 0.85:
       -> tính RescueScore(w)
       -> nếu RescueScore >= tau -> AlertCandidate (nguồn: rescue)
       -> ngược lại              -> bỏ qua
```

`RescueScore(w | A) = η1·Λ_log(w) + η2·Φ_topo(w, A) + η3·Δ_time(w, A)`

Ràng buộc: `η1, η2, η3 >= 0` và `η1 + η2 + η3 = 1`; `RescueScore ∈ [0, 1)` (cận trên không đạt được vì `Λ_log` là hàm bão hòa tiệm cận).

Các thành phần chuẩn hóa:
- `Λ_log(w) = 1 - exp(- N_err(w) / k_log) ∈ [0, 1)`: Mật độ log lỗi trong cửa sổ trượt (với `k_log = 10`, đếm log ERROR, FATAL, HTTP >= 500, exception). Hàm bão hòa giúp kháng log flood.
- `Φ_topo(w, A) = max_{s_a ∈ S_A} [1 / (1 + d_G^undirected(s_w, s_a))]`: Độ cận kề đồ thị phụ thuộc vô hướng giữa service `s_w` của window và tập service `S_A` đang có True Alert (bằng 0 nếu chưa có alert nào).
- `Δ_time(w, A) = max_{t_a ∈ T_A} exp(- |t_w - t_a| / σ_rescue)`: Độ cận kề thời gian với các alert đang nổ trong cụm sự cố `A` (`σ_rescue` mặc định 300 s).
- `η1, η2, η3, τ` đọc từ config, **không hardcode**. Ngưỡng kích hoạt: nếu `y_IF(w) == 0` và `RescueScore >= τ` thì phát hành `AlertCandidate(source="rescue")`.

Phải ghi lại `rescue_score` và các thành phần vào ClickHouse cho mọi window, kể cả window không được promote — cần dữ liệu này để vẽ biểu đồ độ nhạy của τ.

### 6.3 `services/retrieval`

Trách nhiệm: chứa 2 strategy, chọn theo config (QĐ-011 — thu gọn từ 5).

```text
retrieval/
  bm25_hybrid.py       # baseline, port từ GĐ1 (M1)
  hybrid_bm25_graph.py # C1 của CTAV: Weighted Context Fusion, port từ legacy/src/phase2/retrieval/ (M3)
  registry.py          # name -> class, dùng bởi config loader (M1)
```

Protocol, `RetrievalBudget`, `RetrievalResult` nằm ở `packages/schemas/` (`protocols.py`,
`models.py`), không có `base.py` riêng. Kho bằng chứng (log/trace Nezha) là
`packages/schemas/evidence.py`.

**`bm25_hybrid`** (M1, QĐ-016) — port nguyên văn `HybridRetriever` của GĐ1: cùng tokenizer,
BM25 (k1 = 1,5, b = 0,75), cosine hashing, `search = 0,6·bm25/(bm25+1) + 0,4·cos`,
`final = 0,45·search + 0,25·time + 0,20·metadata + 0,10·signal`, lề ±8 phút, `search_k` 60.
Hai khác biệt có chủ đích: (1) truy vấn **không chứa fault type** (lỗi paper §3.5);
(2) `pool="window"` — tập ứng viên là bằng chứng của `s_0` trong [t − lề, t + lề] lấy từ
kho Nezha đầy đủ, thống kê BM25 tính trên tập đó. `pool="global"` + `extra_query_terms`
giữ đúng hành vi GĐ1 (tìm toàn corpus rồi mới lọc thời gian), chỉ dùng cho G-port/G-paper.

**`hybrid_bm25_graph`** (C1, M3, QĐ-021) — port nguyên văn `TopologyAwareRetriever` của GĐ1:
pool = top-60 BM25 + mở rộng đồ thị vô hướng 2-hop (20 event gần thời điểm giữa cửa sổ nhất
mỗi service, trong ±8 phút); Fusion Score A4 (α 0,35, β 0,25, γ 0,40, τ 300 s), tie-break như
GĐ1. Cờ `bm25_pool`: `global` = đúng paper (BM25 toàn corpus, **không giới hạn thời gian**,
chỉ trên corpus cố định — parity, cấm trên val/test); `window` = GĐ2 (bằng chứng các service
trong 2-hop, ±8 phút, kho đầy đủ). Trên dữ liệu đầy đủ, với A4 không event lân cận nào vào
được top-6 (QĐ-021, Phát hiện 4).

QĐ-022 (V16, V17): `k_graph` (mặc định 0 = C1-paper) giữ tối thiểu min(`k_graph`, số có sẵn)
chỗ trong top-k cho event có d_G ≥ 1 có Fusion Score cao nhất; phần còn lại theo thứ hạng,
thứ tự cuối vẫn theo Fusion Score (C1-quota). `engine`: `vectorized` (mặc định, chỉ mục theo
file phút + BM25 numpy, `services/retrieval/window_index.py`) hoặc `reference` (đường thuần
Python của port — oracle và phương án dự phòng); hai engine cho cùng top-k, cùng điểm từng bit.
Harness có thể chạy retrieval trên `retrieval.workers` process (chỉ kho Nezha).

Mỗi `ContextEvent` phải ghi `origin` và `graph_distance` — chính sách C2/C3 ở
`services/judge` cần hai trường này (`03` §1.3). QĐ-021 (V14): `origin = local` khi event
nằm ở `s_0` (d_G = 0), ngược lại `graph`; kênh tìm thấy (bm25 / graph) ghi ở
`debug.source_flags`.

> **Đã cắt ở QĐ-011** (giữ mô tả bên dưới để tham chiếu): `temporal` và `graph` thuần
> trở thành ablation của `hybrid_bm25_graph` (β = 1, γ = 1); `cross_modal` và chế độ RRF
> bị cắt, ghi vào `docs/ideas.md`.

Chi tiết từng biến thể (bản thiết kế cũ):

**`temporal`** — window size = ánh xạ tuyến tính từ anomaly score:
`window = window_min + (window_max - window_min) * normalized_score`.
Tham số: `window_min` (mặc định 2 phút), `window_max` (mặc định 15 phút). Baseline GĐ1 dùng cố định ±8 phút.

**`cross_modal`** — ba `BM25Index` riêng cho log, trace span, metric snapshot. Mỗi kênh lấy `top_k_channel` riêng, hợp nhất bằng weighted fusion `w_log`, `w_trace`, `w_metric` (chuẩn hóa tổng = 1).

**`graph`** — BFS từ service của alert, tối đa `hop` bước (mặc định 2), trọng số `decay_factor ** distance`. Cần `packages/graph` dựng sẵn đồ thị.

**`hybrid_bm25_graph` (Topology-Aware Retrieval with Weighted Context Fusion)** — Lõi đóng góp của bài báo và luận văn.
Hỗ trợ hai chế độ tính điểm:
1. **Weighted Context Fusion (`fusion_mode: "weighted"` — mặc định, cho Paper & Thesis):**
   `Score_fusion(c | s0, t0) = α·BM25_norm(c, q) + β·TimeSim(tc, t0) + γ·GraphSim(sc, s0)`
   - Ràng buộc: `α, β, γ >= 0` và `α + β + γ = 1`.
   - `BM25_norm(c, q) = (BM25(c, q) - min) / (max - min + ε)`: Chuẩn hóa Min-Max trên tập ứng viên.
   - `TimeSim(tc, t0) = exp(- |tc - t0| / τ_time)`: Hàm phân rã thời gian (`τ_time` mặc định 300 s).
   - `GraphSim(sc, s0) = 1 / (1 + d_G(sc, s0))`: Tương đồng topology dựa trên khoảng cách đồ thị có hướng `d_G` từ trace (`sc` là service của context, `s0` là service của alert). Khoảng cách càng lớn thì điểm tương đồng càng giảm về 0, khắc phục lỗi cộng trực tiếp khoảng cách.
2. **Reciprocal Rank Fusion (`fusion_mode: "rrf"` — baseline phụ không tham số):**
   Chạy BM25 và Graph song song, merge bằng: `score(d) = Σ 1 / (k + rank_i(d))`, `k` mặc định 60.

### 6.4 `services/judge`

Port từ GĐ1. Giữ nguyên:
- Prompt template và cấu trúc output 3 nhãn
- `require_evidence_for_true_alert`: verdict TRUE_ALERT bị hạ xuống UNCERTAIN nếu LLM không nêu được evidence cụ thể
- ~~Local-first: thử llama3.2:3b trước, fallback Gemini Flash Lite~~ — **bỏ ở QĐ-013**: một model API cố định `gemini-2.5-flash-lite`, không fallback sang model khác. Lỗi API: retry có trần, hết retry ⇒ `manual_review` + ghi log
- Response cache tương thích file với GĐ1: `sha256(provider | model | prompt | "max=<max_tokens>|t=0")`, thêm `"|repeat=n"` khi `repeat = n > 0` (mặc định 0 ⇒ trùng key GĐ1) để đo phương sai bằng cách gọi lại thật (`08` §4.1, `03` §6)
- Mỗi bản ghi lưu model id/phiên bản API trả về
- Backend `mock` của GĐ1 — chỉ dùng cho cổng chặn G-port, không dùng cho số liệu khoa học

Thêm mới cho CTAV (QĐ-011, `08` §4):

```text
judge/
  prompt.py      # prompt GĐ1 nguyên văn (M1)
  cache.py       # cache JSONL, key GĐ1 + repeat (M1)
  backends.py    # GeminiBackend (gemini-2.5-flash-lite), MockBackend (M1)
  llm_judge.py   # port GĐ1: verdict thô + require_evidence + ngưỡng 0,80 đối xứng của GĐ1 (M1)
  registry.py    # config judge: -> LLMJudge (M1)
  policy.py      # C2 asymmetric gating (θ_local, θ_topo) + C3 evidence anchoring
  routing.py     # C4: tầng 1 BM25 -> judge; UNCERTAIN/thiếu bằng chứng -> tầng 2 topology -> judge
```

- `policy.py` là hàm thuần trên (verdict thô, `RetrievalResult`, graph) → verdict cuối;
  chạy lại được trên verdict đã cache mà **không gọi LLM**, nên quét θ rất rẻ.
- Verdict thô và verdict sau policy đều được ghi lại, để đo đóng góp của từng thành phần (H3).

### 6.5 `services/rca_agent`

```text
rca_agent/
  grouping.py     # Nhiệm vụ 1
  propagation.py  # Nhiệm vụ 2
  summarizer.py   # Nhiệm vụ 3
  pipeline.py     # điều phối 3 bước
```

**`grouping.py`** — thuần thuật toán, không gọi LLM:
```text
1. Gom alert theo cửa sổ trượt T_group (mặc định 300s)
2. Trong mỗi cụm thời gian, dựng đồ thị con từ service dependency graph
3. Mỗi thành phần liên thông = 1 Incident
```
Không phụ thuộc biến thể RAG nào → **bản khởi động làm song song ở M6**.

**`propagation.py`** — hai mức, implement mức 1 trước:
- Mức 1 (bắt buộc): từ span lỗi ở frontend đi ngược 1 hop, chọn immediate upstream service có dấu hiệu bất thường
- Mức 2 (nếu kịp): LLM lập luận ngược toàn bộ call chain, chọn span đầu tiên bất thường

Cả hai mức đều phải chạy được và đo Hit@1 riêng — so sánh chúng là một kết quả của luận văn.

**`summarizer.py`** — gọi LLM một lần cho mỗi Incident, output theo JSON schema ở `03-schemas-and-contracts.md`. Áp `require_evidence` tương tự judge: không có evidence span cụ thể thì không phát hành chẩn đoán.

### 6.6 `services/api`

FastAPI, chỉ đọc, không có logic nghiệp vụ.

```text
GET  /runs                        # danh sách run thực nghiệm
GET  /runs/{run_id}/metrics       # bảng chỉ số của một run
GET  /alerts?run_id=&verdict=     # danh sách alert có phân trang
GET  /alerts/{alert_id}           # chi tiết + context đã retrieve + debug
GET  /incidents?run_id=           # danh sách incident
GET  /incidents/{incident_id}     # chi tiết + propagation graph + diagnostic
GET  /health
```

### 6.7 `services/web`

Bốn màn hình, không hơn:

1. **Timeline** — alert theo thời gian, màu theo verdict
2. **Alert detail** — bằng chứng RAG đã truy xuất, lý do LLM ra verdict
3. **Incident detail** — đồ thị lan truyền + báo cáo chẩn đoán JSON
4. **Experiment comparison** — bảng so sánh các run, đọc từ `eval/results/`

Màn hình 3 và 4 là hai màn hình gây ấn tượng nhất khi bảo vệ. Ưu tiên đánh bóng chúng.

### 6.8 `eval/harness`

CLI độc lập (M2: `run`; `compare`, `ablation` thêm khi cần ở M4/M7):

```bash
py -m eval run --config eval/configs/<tên>.yaml
```

`eval/harness/runner.py` replay Nezha theo thời gian (lịch sử liên tục, QĐ-015) qua
detector → gate GĐ1 (tùy chọn) → retrieval → judge; `metrics.py` tính P/R/F1/FPR (recall trên
**mọi** fault window), coverage, độ trễ, token, số lần gọi, chi phí — trên tập **có
telemetry** (chính) và toàn bộ (phụ) (QĐ-017); `stats.py`: bootstrap CI 95% + McNemar chính xác.
`stages: detector` chỉ chạy detector (đếm candidate). Không ghi đè `eval/results/<run_id>/`.

Output vào `eval/results/<run_id>/` (`02` §3.3):
```text
metrics.json         # chỉ số tổng hợp + CI, hai tập telemetry / all
per_window.csv       # một dòng mỗi window: nhãn, has_telemetry, điểm, gate, verdict, latency, token
retrieval.jsonl      # RetrievalResult của mỗi lần retrieve
judged.jsonl         # JudgedAlert của mỗi lần chấm
config.snapshot.yaml
git_commit.txt
runtime.json         # thời gian, số lần gọi LLM/API, cache hit rate
```

---

## 7. Cấu trúc repository

```text
aiops-rca-platform/
  AGENTS.md                    # bootstrap cho AI coding agent
  README.md
  docker-compose.yml           # profiles: dev, full
  .env.example
  pyproject.toml

  services/
    replayer/
    detector/
    retrieval/
    judge/
    rca_agent/
    api/
    web/

  packages/
    schemas/                   # pydantic models, dùng chung mọi service
    graph/                     # service dependency graph builder
    llm/                       # client API (gemini-2.5-flash-lite), cache, retry có trần
    storage/                   # ClickHouse + Postgres client

  eval/
    harness/
    configs/
    results/                   # commit vào git

  data/
    nezha/                     # gitignore, có script tải
    splits/                    # commit vào git

  infra/
    clickhouse/init.sql
    postgres/init.sql
    redpanda/

  docs/                        # bộ tài liệu này

  scripts/
    verify_labels.py
    build_service_graph.py
    seed_demo.py
    reset_local_env.sh

  tests/
```

---

## 8. Deployment

### 8.1 Docker Compose profiles

```yaml
services:
  clickhouse:  { profiles: ["dev", "full"] }
  postgres:    { profiles: ["dev", "full"] }
  ollama:      { profiles: ["dev", "full"] }
  api:         { profiles: ["dev", "full"] }
  web:         { profiles: ["dev", "full"] }
  redpanda:    { profiles: ["full"] }
  prometheus:  { profiles: ["full"] }
  grafana:     { profiles: ["full"] }
```

Chạy thực nghiệm chỉ cần `dev`. Redpanda chỉ cần khi demo stream mode hoặc GĐ3.

```bash
docker compose --profile dev up -d      # hằng ngày
docker compose --profile full up -d     # demo đầy đủ
```

### 8.2 Yêu cầu tài nguyên

Profile `dev` nên chạy được trên máy 16GB RAM. Nếu Ollama + ClickHouse quá nặng, cho phép chạy Ollama ngoài Docker.

---

## 9. Những gì KHÔNG thuộc kiến trúc này

Ghi rõ để tránh tranh cãi sau:

- Không Kubernetes
- Không multi-tenant, không workspace, không user management
- Không authentication phức tạp — API chỉ chạy local
- Không billing, không quota
- Không vector database (BM25 và graph là đủ, thêm vector store là một biến thể RAG thứ 6 không nằm trong kế hoạch)
- Không agent framework bên ngoài (LangChain, AutoGen...) — tác tử ở đây là ba bước tuần tự có kiểm soát, không cần framework
- Không runbook thực thi tự động

Xem `06-scope-guard.md` để biết cách xử lý khi có đề xuất thêm những thứ trên.
