# 02 — Dữ liệu và Quy trình Thực nghiệm

Tài liệu này quy định cách dùng dữ liệu và cách chạy thực nghiệm. **Vi phạm quy trình ở đây làm hỏng tính hợp lệ của luận văn**, nghiêm trọng hơn lỗi code.

---

## 1. Dữ liệu Nezha

### 1.1 Đặc điểm

Nezha (Yu và cs., 2023) là dataset multi-modal observability thu từ hai hệ microservices mẫu (TrainTicket và OnlineBoutique) với lỗi được tiêm có chủ đích. Ba nguồn: metric, log, trace.

Loại lỗi chính dùng trong đề tài: `network_delay`, `cpu_contention`, cùng các cửa sổ `normal`.

### 1.2 Việc bắt buộc làm ở Tuần 1: kiểm tra nhãn

Trước khi viết bất kỳ dòng code pipeline nào, chạy `scripts/verify_labels.py` và trả lời:

- [ ] Mỗi fault window có nhãn `root_cause_service` không?
- [ ] Nhãn ở mức service hay mức pod/container? Nếu mức pod, có ánh xạ được lên service không?
- [ ] Có bao nhiêu fault window có nhãn / tổng số fault window?
- [ ] Phân bố nhãn theo loại lỗi như thế nào?
- [ ] Trace có đủ `span_id` / `parent_span_id` để dựng call chain không?

Output: `docs/label-audit.md`, một trang, có bảng số liệu.

**Nếu nhãn root-cause không có sẵn:** dừng lộ trình, chọn một trong hai:
1. Gán tay dựa trên metadata fault injection (ước tính 2–3 ngày cho 300 window)
2. Chuyển sang RCAEval hoặc dataset khác có nhãn

Quyết định này phải xong trong Tuần 1. Phát hiện muộn ở Tháng 4 là không cứu được.

### 1.3 Service dependency graph

Dựng từ trace data bằng `scripts/build_service_graph.py`:

```text
Với mỗi trace:
  với mỗi span có parent_span_id:
    thêm cạnh (service_của_parent -> service_của_span)
Tổng hợp: cạnh có trọng số = số lần xuất hiện
Lọc: bỏ cạnh xuất hiện < min_edge_count (mặc định 5) để giảm nhiễu
```

**Đo coverage trước khi tin vào Graph RAG:**

| Chỉ số | Cách tính | Ngưỡng quyết định |
|---|---|---|
| Service coverage | % service xuất hiện trong graph / tổng service | < 80% → cảnh báo |
| Edge density | số cạnh / (số node × (số node - 1)) | ghi nhận |
| Fault window có service trong graph | % | **< 60% → kích hoạt fallback BM25** |

Kết quả đo ghi vào `docs/graph-coverage.md` ở mốc M3. Nếu graph quá thưa, đây **là một finding của luận văn**, không phải thất bại — ghi lại và phân tích tại sao.

---

## 2. Chia dữ liệu

### 2.1 Ba split, chốt cứng Tuần 1

| Split | Tỷ lệ | Dùng để | Được chạm bao nhiêu lần |
|---|---|---|---|
| `dev` | 20% | Debug, phát triển, thử nhanh | Không giới hạn |
| `val` | 30% | Tuning Rescue Score (η1, η2, η3, τ), chọn tham số Fusion Score (α, β, γ) | Không giới hạn |
| `test` | 50% | Báo cáo kết quả cuối trong luận văn | **Một lần, ở mốc M8** (QĐ-014) |

### 2.2 Cách chia

Stratified theo loại lỗi, đảm bảo mỗi split có đủ `network_delay`, `cpu_contention`, `normal` theo cùng tỷ lệ.

```python
# scripts/make_splits.py
SEED = 42
# stratify theo fault_type
# ghi ra data/splits/{dev,val,test}.json  -- danh sách window_id
```

File split được **commit vào git** và không được sinh lại. Nếu phải sinh lại (ví dụ sau khi gán nhãn tay), phải ghi lý do vào commit message và cập nhật tài liệu này.

### 2.3 Quy tắc test split

- Không chạy thực nghiệm trên `test` trước mốc M8 và trước khi đăng ký giả thuyết ở M7 (QĐ-011, QĐ-014)
- Không tuning bất kỳ tham số nào dựa trên kết quả `test`
- Nếu lỡ nhìn kết quả `test` sớm, phải ghi lại vào `docs/experiment-log.md` — luận văn trung thực về việc này vẫn tốt hơn luận văn giấu

---

## 3. Config thực nghiệm

### 3.1 Cấu trúc file config

Mọi thực nghiệm chạy từ một file YAML trong `eval/configs/`. Không có ngoại lệ.

```yaml
# eval/configs/graph_rag.yaml
run_id: graph_rag_v1          # duy nhất, không tái sử dụng
seed: 42
split: val                     # dev | val | test
n_windows: 300

source:
  type: nezha_replay
  speed_multiplier: 0

detector:
  type: isolation_forest
  threshold: 0.85

rescue:
  enabled: true
  eta1: 0.5                    # trọng số mật độ log lỗi (Λ_log)
  eta2: 0.3                    # trọng số độ cận kề topology (Φ_topo)
  eta3: 0.2                    # trọng số độ cận kề thời gian (Δ_time)
  tau: 0.6

retrieval:
  type: graph                  # tên trong registry.py
  top_k: 6
  max_tokens: 4000
  timeout_ms: 500
  fusion_mode: weighted        # weighted (chính, paper core) | rrf (baseline)
  params:
    alpha: 0.4                 # trọng số BM25 norm
    beta: 0.3                  # trọng số TimeSim
    gamma: 0.3                 # trọng số GraphSim
    hop: 2
    decay_factor: 0.6

judge:
  type: llm
  backend: api                 # QĐ-013: một model API cố định, không local-first, không fallback
  model: gemini-2.5-flash-lite
  temperature: 0
  require_evidence: true
  cache: true

rca:
  enabled: false               # tắt khi chạy thực nghiệm Nhánh A
```

### 3.2 Quy tắc đặt `run_id`

Format: `<biến_thể>_<mục_đích>_v<số>`. Ví dụ: `graph_rag_val_v1`, `hybrid_test_final_v1`.

`run_id` là **duy nhất và không tái sử dụng**. Chạy lại với tham số khác = `run_id` mới. Kết quả cũ không bao giờ bị ghi đè.

### 3.3 Output bắt buộc của mỗi run

```text
eval/results/<run_id>/
  metrics.json           # chỉ số tổng hợp + CI
  per_window.csv         # 1 dòng / window
  retrieval.jsonl        # debug trace retrieval
  config.snapshot.yaml   # bản sao config đã dùng
  git_commit.txt         # commit hash lúc chạy
  runtime.json           # thời gian chạy, số lần gọi LLM, cache hit rate
```

Thư mục này được **commit vào git**. Đây là bằng chứng tái lập của luận văn.

---

## 4. Định nghĩa chỉ số

### 4.1 Nhánh A — chất lượng phân loại

| Chỉ số | Công thức | Ghi chú |
|---|---|---|
| Precision | TP / (TP + FP) | TP = alert được judge là TRUE và window thật sự có lỗi |
| Recall | TP / (TP + FN) | FN gồm cả window có lỗi mà detector không sinh candidate |
| F1 | 2PR / (P + R) | |
| FPR | FP / (FP + TN) | |

**Lưu ý quan trọng về Recall:** phải tính trên **toàn bộ fault window trong split**, không chỉ trên các window mà detector đã sinh candidate. Nếu chỉ tính trên candidate, Recall sẽ bị thổi phồng.

**Tập chấm chính (QĐ-017):** chỉ số chính tính trên các cửa sổ **có telemetry** — Nezha có
ít nhất một file log/trace trong ±8 phút quanh cửa sổ. Nezha chỉ ghi log/trace quanh các
lần tiêm lỗi (100% fault nhưng ~25% normal có), nên trên toàn split, judge có
`require_evidence` "đúng" một cách tầm thường với ~75% normal. Toàn split vẫn báo cáo làm
số phụ. Mask tính từ danh sách file của dataset, không dùng nhãn.

### 4.2 Nhánh A — chất lượng retrieval

| Chỉ số | Định nghĩa |
|---|---|
| Context coverage | % fault window có ≥ 1 context event được retrieve |
| Retrieval latency | Trung bình và P95 của `latency_ms` mỗi lần gọi retrieve |
| Avg context tokens | Trung bình `token_estimate` |
| Context precision | % context event thực sự liên quan đến fault — **chấm thủ công** trên mẫu ngẫu nhiên ≥ 50 window |

**Quy trình chấm context precision thủ công:**
1. Lấy mẫu ngẫu nhiên 50 window từ `retrieval.jsonl` với seed cố định
2. Với mỗi event, gán nhãn: liên quan / không liên quan / không chắc
3. Ghi vào `eval/manual/context_precision_<run_id>.csv`
4. Nếu có thể, nhờ người thứ hai chấm 20% mẫu để tính độ đồng thuận

### 4.3 Nhánh B — chất lượng RCA

| Chỉ số | Định nghĩa |
|---|---|
| Hit@1 | % incident mà root cause service thật nằm ở vị trí 1 trong đề xuất |
| Hit@3 | % incident mà root cause service thật nằm trong top-3 |
| Alert Reduction Ratio | 1 − (số incident / số alert đơn lẻ), đo trên cascade fault |
| JSON valid rate | % diagnostic report pass schema validation |
| E2E latency | Từ lúc nhận TRUE_ALERT đến lúc phát hành DiagnosticReport |

**Ánh xạ incident → ground truth:** một incident gom nhiều alert. Ground truth của incident = root cause service của fault đã tiêm trong khoảng thời gian đó. Nếu một incident chứa alert từ nhiều fault khác nhau, đánh dấu là `ambiguous` và loại khỏi tính Hit@k, nhưng **phải báo cáo số lượng bị loại**.

### 4.4 Đánh giá chất lượng chẩn đoán bằng người (mốc M11)

Mẫu 30 incident, chấm theo ba tiêu chí, thang 0–2:

| Tiêu chí | 0 | 1 | 2 |
|---|---|---|---|
| Đúng root cause | Sai | Gần đúng (service liền kề) | Đúng |
| Bằng chứng hợp lệ | Bịa hoặc không liên quan | Liên quan một phần | Đúng và đủ |
| Gợi ý xử lý dùng được | Vô nghĩa | Chung chung | Cụ thể, khả thi |

Ghi vào `eval/manual/diagnostic_quality.csv`.

---

## 5. Xử lý thống kê

### 5.1 Vấn đề

Nezha chỉ có khoảng 300–500 window. Chênh lệch F1 giữa hai biến thể có thể nằm hoàn toàn trong nhiễu. Báo cáo điểm số đơn lẻ và tuyên bố "biến thể X tốt nhất" là kết luận không vững.

### 5.2 Bắt buộc

Mọi chỉ số báo cáo trong luận văn phải kèm **khoảng tin cậy 95% bằng bootstrap**:

```python
# eval/harness/stats.py
def bootstrap_ci(per_window_results, metric_fn, n_boot=1000, seed=42):
    """Resample per-window với hoàn lại, tính metric mỗi lần, lấy percentile 2.5 và 97.5."""
```

Ngoài ra, mỗi cấu hình chạy với **ít nhất 3 seed khác nhau** (42, 123, 2024) và báo cáo trung bình ± độ lệch chuẩn.

So sánh hai phương pháp trên **cùng tập cửa sổ** (CTAV vs BM25, CTAV vs C1...) phải kèm
**McNemar test chính xác** trên đúng/sai từng cửa sổ, như paper đã làm (QĐ-011):

```python
# eval/harness/stats.py
def mcnemar_exact(correct_a: list[bool], correct_b: list[bool]) -> float:
    """p-value hai phía trên các cặp bất đồng (b, c)."""
```

### 5.3 Giả thuyết đăng ký trước

Giả thuyết H0–H5 và tiêu chí bác bỏ nằm ở `08-research-direction.md` §5. Bản có ngưỡng
định lượng được commit vào `docs/experiment-log.md` ở mốc M7, **trước** lần chạy `test`
duy nhất. Không sửa giả thuyết sau khi đã thấy kết quả `test`.

### 5.4 Cách phát biểu kết luận

| Tình huống | Cách viết đúng |
|---|---|
| CI không chồng lấn | "Biến thể X vượt trội có ý nghĩa so với Y" |
| CI chồng lấn | "Các biến thể cho kết quả tương đương trên quy mô dữ liệu này; chênh lệch nằm trong khoảng nhiễu" |
| X tốt hơn nhưng latency cao hơn nhiều | Trình bày như một đánh đổi, không tuyên bố thắng tuyệt đối |

Kết luận "các biến thể tương đương" **là một kết quả nghiên cứu hợp lệ** và dễ bảo vệ hơn nhiều so với kết luận gượng ép. Không được ép số liệu.

---

## 6. Ablation Rescue Score & Fusion Score (mốc M7 & M4)

### 6.1 Không gian tham số Rescue Score (mốc M7 — Luận văn)

Công thức: `RescueScore(w | A) = η1·Λ_log(w) + η2·Φ_topo(w, A) + η3·Δ_time(w, A) >= τ`

```text
η1, η2, η3 ∈ {0, 0.2, 0.4, 0.6, 0.8, 1.0}, ràng buộc η1 + η2 + η3 = 1
τ          ∈ {0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9}
```

Số tổ hợp hợp lệ của (η1, η2, η3) với ràng buộc tổng = 1 là 21, nhân 7 giá trị τ = 147 cấu hình. Chạy trên `val` split.

### 6.2 Chạy thế nào cho rẻ

- Bật LLM cache. Cùng một prompt chỉ gọi LLM một lần trong toàn bộ ablation.
- Tính trước `Λ_log`, `Φ_topo`, `Δ_time` cho mọi window một lần, lưu ra file `data/rescue_features.parquet`. Ablation chỉ là tổ hợp tuyến tính trên các giá trị đã tính — không cần chạy lại pipeline 147 lần.

Đây là tối ưu quan trọng nhất của mốc M7. Nếu không làm, ablation sẽ mất nhiều ngày và tốn tiền API.

### 6.3 Tiêu chí chọn

Chọn bộ tham số tối đa hóa F1 trên `val`, với ràng buộc số lần gọi LLM tăng không quá 50% so với không bật rescue.

Vẽ đường cong: trục x = τ, trục y trái = Recall, trục y phải = số lần gọi LLM. Đây là hình quan trọng của luận văn.

### 6.4 Khi nào rút gọn công thức

Nếu ablation cho thấy một thành phần chiếm ưu thế rõ rệt (ví dụ η2 tối ưu ≈ 0), rút về công thức hai tham số và ghi rõ lý do. Điều này đã được dự phòng trong bảng rủi ro của bản định hướng — thực hiện nó không phải thất bại.

### 6.5 Ablation Fusion Score (mốc M4 — Paper & Luận văn)

> QĐ-011: lưới này chạy **retrieval-only** (không gọi LLM) trên `val`, và gồm luôn
> temporal-only (β = 1) và graph-only (γ = 1) thay cho hai strategy `temporal`, `graph`
> đã cắt. Ablation của CTAV (C2/C3/C4, θ_topo) xem `08` §5 và `04` mốc M6.

Công thức xếp hạng context: `Score_fusion(c | s0, t0) = α·BM25_norm(c, q) + β·TimeSim(tc, t0) + γ·GraphSim(sc, s0)`

```text
α, β, γ ∈ {0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}, ràng buộc α + β + γ = 1
```

Quét lưới tham số trên `val` để tìm bộ (α, β, γ) tối ưu hóa Context Precision và F1 chẩn đoán downstream, chứng minh định hướng: *Topology-Aware RAG vượt trội so với chỉ dùng từ khóa (α=1) hoặc chỉ dùng thời gian (β=1)*.

---

## 7. Nhật ký thực nghiệm

Duy trì `docs/experiment-log.md`, mỗi mục một dòng:

```text
| Ngày | run_id | Split | Mục đích | Kết quả chính | Ghi chú |
```

Ghi cả những lần chạy thất bại và lý do. Đây là nguồn để viết phần "quá trình thực nghiệm" trong luận văn, và là bằng chứng bạn không cherry-pick kết quả.

---

## 8. Checklist trước khi báo cáo một con số cho GVHD

- [ ] Con số này sinh từ `eval/results/`, không phải tính tay
- [ ] Có `run_id` và `git_commit` tương ứng
- [ ] Chạy trên đúng split (val cho tuning, test cho kết quả cuối)
- [ ] Có khoảng tin cậy hoặc độ lệch chuẩn qua nhiều seed
- [ ] Đã ghi vào `experiment-log.md`
