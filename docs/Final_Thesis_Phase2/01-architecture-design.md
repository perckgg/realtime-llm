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
                    │  - local-first routing   │
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

Bốn interface dưới đây là xương sống. **Không được đổi signature** sau Tuần 3 mà không cập nhật tài liệu này.

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

Implement: `LLMJudge` với local-first routing.

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

Trách nhiệm: chứa 5 strategy, chọn theo config.

```text
retrieval/
  base.py              # Protocol + RetrievalBudget + RetrievalResult
  bm25_hybrid.py       # baseline, port từ GĐ1
  temporal.py          # cửa sổ thích nghi theo anomaly score
  cross_modal.py       # 3 kênh log/trace/metric + weighted fusion
  graph.py             # lan rộng theo service dependency graph
  hybrid_bm25_graph.py # Weighted Context Fusion (chính) / RRF merge (phụ)
  registry.py          # name -> class, dùng bởi config loader
```

Chi tiết từng biến thể:

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
- Local-first: thử llama3.2:3b trước, fallback Gemini Flash Lite khi timeout/lỗi/output không parse được
- Response cache theo `hash(prompt + model + temperature)`

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
Không phụ thuộc biến thể RAG nào → **có thể code từ Tuần 9**.

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

CLI độc lập:

```bash
python -m eval run --config eval/configs/graph_rag.yaml
python -m eval compare --runs bm25_baseline,temporal,graph,cross_modal,hybrid
python -m eval ablation --config eval/configs/rescue_ablation.yaml
```

Output vào `eval/results/<run_id>/`:
```text
metrics.json      # chỉ số tổng hợp + confidence interval
per_window.csv    # một dòng mỗi window: verdict, ground truth, latency, tokens
retrieval.jsonl   # debug trace của retrieval, phục vụ chấm context precision
config.snapshot.yaml
git_commit.txt
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
    llm/                       # client, cache, local-first router
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
