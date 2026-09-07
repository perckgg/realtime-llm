# 04 — Lộ trình triển khai 24 tuần

Mỗi tuần có một kết quả kiểm chứng được. Nếu cuối tuần không đạt, xem §8 để biết cắt gì.

**Cách dùng với AI coding agent:** chỉ nạp phần tuần đang làm vào context. Không nạp cả file, để agent không tự nhảy sang task tương lai.

---

## Tháng 1 — Nền tảng và kiểm chứng dữ liệu

### Tuần 1 — Kiểm tra dữ liệu trước, code sau

Đây là tuần **không viết code pipeline**. Rủi ro lớn nhất của toàn đề tài nằm ở đây.

| Task | Output |
|---|---|
| `scripts/verify_labels.py` — kiểm tra nhãn root-cause của Nezha | `docs/label-audit.md` |
| Kiểm tra trace có đủ `span_id` / `parent_span_id` | Ghi trong label-audit |
| `scripts/make_splits.py` — chia dev/val/test stratified, seed 42 | `data/splits/*.json` được commit |
| Khởi tạo repo, `pyproject.toml`, cấu trúc thư mục theo `01` §7 | Repo trống nhưng đúng cấu trúc |
| Copy `AGENTS.md`, `05`, `06` vào `docs/` | Agent có guardrail từ ngày đầu |

**DoD Tuần 1:**
- [ ] Biết chính xác có bao nhiêu fault window có nhãn root-cause
- [ ] Split được commit, không đổi nữa
- [ ] Nếu thiếu nhãn: đã ra quyết định (gán tay / đổi dataset) và ghi vào `docs/experiment-log.md`

**Cổng chặn:** không sang Tuần 2 nếu chưa trả lời được câu hỏi nhãn.

### Tuần 2 — Hạ tầng và port GĐ1

| Task | Output |
|---|---|
| `docker-compose.yml` profiles dev/full | `docker compose --profile dev up -d` chạy được |
| `infra/clickhouse/init.sql`, `infra/postgres/init.sql` theo `03` | Bảng được tạo tự động |
| `packages/schemas/` — toàn bộ model ở `03` §1 | Import được từ mọi service |
| Port `services/replayer` từ GĐ1 | Phát được 50 window |
| Port `services/detector` (Isolation Forest 0.85) | Sinh được AlertCandidate |

**DoD Tuần 2:**
- [ ] Một lệnh dựng được toàn bộ môi trường dev
- [ ] Replay 50 window → alert candidate ghi vào ClickHouse

### Tuần 3 — Interface và tái lập baseline GĐ1

**Đây là tuần quan trọng nhất của Tháng 1.**

| Task | Output |
|---|---|
| Định nghĩa 4 Protocol ở `01` §5 | `packages/schemas/protocols.py` |
| Port BM25 hybrid → `retrieval/bm25_hybrid.py` | Strategy đầu tiên |
| Port `services/judge` + LLM cache + local-first routing | Judge chạy được |
| `retrieval/registry.py` — ánh xạ tên → class | Config chọn được strategy |
| Chạy pipeline đầy đủ trên 300 window với cấu hình GĐ1 | So sánh với baseline |

**DoD Tuần 3 — cổng chặn nghiêm ngặt:**
- [ ] Precision ≈ 0.32 (±0.03), FPR ≈ 0.046 (±0.01) trên 300 window
- [ ] Nếu lệch nhiều hơn: **dừng, tìm nguyên nhân**, không đi tiếp

Lệch số liệu ở đây nghĩa là port sai. Mọi kết quả sau đó sẽ vô nghĩa.

### Tuần 4 — Eval harness và service graph

| Task | Output |
|---|---|
| `eval/harness/runner.py` — đọc config, chạy pipeline, ghi results | `python -m eval run --config X` |
| `eval/harness/metrics.py` — P/R/F1/FPR/coverage/latency | `metrics.json` |
| `eval/harness/stats.py` — bootstrap CI | CI trong metrics.json |
| `scripts/build_service_graph.py` + `packages/graph/` | Đồ thị NetworkX |
| Đo coverage của graph theo `02` §1.3 | `docs/graph-coverage.md` |

**DoD Tuần 4:**
- [ ] `python -m eval run --config eval/configs/bm25_baseline.yaml` sinh đầy đủ 6 file output
- [ ] Có `docs/graph-coverage.md` với ba chỉ số coverage
- [ ] Nếu coverage fault window < 60%: ghi quyết định fallback vào experiment-log

**Deliverable Tháng 1:** repo chạy được, baseline tái lập, harness hoạt động, graph có số liệu, split chốt cứng.

---

## Tháng 2 — Graph RAG, Temporal RAG, Rescue Score

Thứ tự đã đổi so với bản định hướng gốc: Graph RAG lên trước vì rủi ro cao nhất và dùng chung với Nhánh B.

### Tuần 5–6 — Graph RAG

| Task | Output |
|---|---|
| `retrieval/graph.py` — BFS `hop` bước, trọng số `decay_factor ** distance` | Strategy `graph` |
| Ghi `debug`: `graph_distance`, `path` | Dữ liệu cho context precision |
| Chạy trên `val`, quét `hop ∈ {1, 2}`, `decay ∈ {0.4, 0.6, 0.8}` | 6 run |
| Nếu graph thưa: implement fallback về BM25 khi service không có trong graph | Ghi tỷ lệ fallback |

**DoD:** bảng kết quả 6 cấu hình graph trên val, có CI.

### Tuần 7 — Temporal RAG

| Task | Output |
|---|---|
| `retrieval/temporal.py` — window size ánh xạ tuyến tính từ anomaly score | Strategy `temporal` |
| Quét `window_min ∈ {2, 4}` phút, `window_max ∈ {12, 15, 20}` phút | 6 run trên val |

**DoD:** bảng kết quả temporal, so với baseline cố định ±8 phút.

### Tuần 8 — Ablation Rescue Score

| Task | Output |
|---|---|
| Tính trước `Λ_log`, `Φ_topo`, `Δ_time` cho mọi window, lưu ra file | `data/rescue_features.parquet` |
| Quét 147 tổ hợp (η1, η2, η3, τ) trên các giá trị đã tính | `eval/results/rescue_ablation/` |
| Vẽ đường cong τ vs (Recall, số lần gọi LLM) | Hình cho luận văn |
| Quyết định: giữ 3 tham số hay rút về 2 | Ghi vào experiment-log |

**DoD Tuần 8:**
- [ ] Có bộ (η1, η2, η3, τ) tối ưu trên val
- [ ] Có hình đường cong độ nhạy τ
- [ ] Ablation chạy xong trong dưới 2 giờ nhờ pre-compute + cache

---

## Tháng 3 — Hoàn tất Nhánh A

### Tuần 9 — Cross-modal RAG + khởi động Alert Grouping

| Task | Output |
|---|---|
| `retrieval/cross_modal.py` — 3 kênh BM25 + weighted fusion | Strategy `cross_modal` |
| Quét trọng số: `(0.5,0.3,0.2)`, `(0.33,0.33,0.34)`, `(0.3,0.5,0.2)` | 3+ run trên val |
| **Song song:** `rca_agent/grouping.py` — chỉ cần timestamp + graph | Module chạy độc lập |

Alert Grouping không phụ thuộc biến thể RAG nào thắng → bắt đầu ngay, đừng chờ Tháng 4.

### Tuần 10 — Hybrid BM25 + Graph (Weighted Context Fusion & RRF)

| Task | Output |
|---|---|
| `retrieval/hybrid_bm25_graph.py` — Weighted Context Fusion (α, β, γ) & RRF merge | Strategy `hybrid_bm25_graph` |
| Quét lưới (α, β, γ) cho Weighted Fusion; so sánh với RRF `k ∈ {20, 60}` | Run trên val (Paper core) |

Đây là biến thể lõi cho bài báo *Topology-Aware RAG + Weighted Context Fusion*.

### Tuần 11 — Chạy test split, chốt Nhánh A

**Lần đầu tiên chạm vào `test`.**

| Task | Output |
|---|---|
| Chọn cấu hình tốt nhất của mỗi biến thể từ kết quả val | 5 config cuối |
| Chạy 5 cấu hình trên `test`, mỗi cấu hình 3 seed (42, 123, 2024) | 15 run |
| Tính CI bootstrap, dựng bảng so sánh | `eval/results/comparison_final/` |
| Chấm context precision thủ công trên 50 window | `eval/manual/` |

**DoD Tuần 11:**
- [ ] Bảng so sánh 5 biến thể trên test, có CI
- [ ] Kết luận biến thể tối ưu — hoặc kết luận "tương đương" nếu CI chồng lấn
- [ ] Context precision đã chấm

### Tuần 12 — Tuần đệm

Nếu không trễ: viết nháp chương Nhánh A của luận văn ngay khi số liệu còn nóng. Đừng để đến Tháng 6.

Nếu trễ: dùng tuần này để bắt kịp.

---

## Tháng 4 — RCA Agent

### Tuần 13 — Alert Grouping hoàn chỉnh

| Task | Output |
|---|---|
| Hoàn thiện `grouping.py` từ bản khởi động Tuần 9 | Module ổn định |
| Quét `T_group ∈ {180, 300, 600}` giây | Chọn giá trị tốt nhất trên val |
| Đo Alert Reduction Ratio trên cascade fault | Chỉ số đầu tiên của Nhánh B |
| Ghi `incidents` vào PostgreSQL | Dữ liệu cho UI |

**DoD:** Alert Reduction Ratio ≥ 30% trên network_delay windows.

### Tuần 14–15 — Fault Propagation Analysis

| Task | Output |
|---|---|
| `propagation.py` mức 1 — backward 1-hop, thuần thuật toán | Chạy trước, đo Hit@1 |
| `propagation.py` mức 2 — LLM lập luận ngược toàn call chain | Chạy sau |
| Trích xuất đặc trưng span: duration, status code, exception | Đầu vào cho cả 2 mức |
| Đo Hit@1/Hit@3 riêng cho mỗi mức | Bảng so sánh 1-hop vs full path |

**DoD:** cả hai mức chạy được, có số liệu so sánh. Nếu mức 2 không hoạt động, giữ mức 1 và báo cáo — đã dự phòng trong bảng rủi ro.

### Tuần 16 — Tích hợp end-to-end lần đầu

| Task | Output |
|---|---|
| Tích hợp biến thể RAG tối ưu từ Tuần 11 vào pipeline agent | Pipeline liền mạch |
| `rca_agent/pipeline.py` điều phối 3 bước | Chạy được từ đầu đến cuối |
| Chạy trên 300 window val | Kết quả sơ bộ |

**DoD Tuần 16:** từ replay đến incident chạy không lỗi, có Hit@1/Hit@3 sơ bộ.

---

## Tháng 5 — Diagnostic Summary, Dashboard, tối ưu

### Tuần 17 — Diagnostic Summary

| Task | Output |
|---|---|
| `summarizer.py` — prompt sinh JSON theo schema `03` §2 | LLM output có cấu trúc |
| Validator + bảng `diagnostic_rejected` | JSON valid rate đo được |
| Áp `require_evidence` | Report không có evidence bị chặn |
| Chặn câu lệnh thực thi trong `suggested_actions` | Đúng phạm vi GĐ2 |

**DoD:** JSON valid rate ≥ 0.95 trên val.

### Tuần 18 — Dashboard

Quyết định công nghệ đầu tuần:

| Lựa chọn | Thời gian | Chọn khi |
|---|---|---|
| Streamlit | ~1 tuần | Tiến độ đã trễ |
| React + Recharts + react-flow | ~2 tuần | Đúng tiến độ |

Bốn màn hình, không hơn: Timeline · Alert detail · Incident detail · Experiment comparison.

**DoD:** cả 4 màn hình hiển thị được dữ liệu thật, có loading/empty state.

### Tuần 19 — Chạy quy mô đầy đủ

| Task | Output |
|---|---|
| Chạy end-to-end trên 500 window test | Kết quả chính thức Nhánh B |
| Đo E2E latency, token cost, cache hit rate | `runtime.json` |
| Tối ưu bottleneck nếu latency quá cao | Ghi lại trước/sau |

### Tuần 20 — Đánh giá bằng người

| Task | Output |
|---|---|
| Lấy mẫu 30 incident, chấm 3 tiêu chí theo `02` §4.4 | `eval/manual/diagnostic_quality.csv` |
| Nếu có thể: nhờ người thứ hai chấm 20% để tính đồng thuận | Độ tin cậy cao hơn |
| Phân tích các trường hợp sai | Nguyên liệu cho phần thảo luận luận văn |

**Deliverable Tháng 5:** hệ thống hoàn chỉnh, demo được, có đủ số liệu cả hai nhánh.

---

## Tháng 6 — Đóng gói

### Tuần 21 — Chốt số liệu và hình vẽ

- Tổng hợp toàn bộ chỉ số: Hit@1, Hit@3, Alert Reduction, JSON valid rate, FP reduction, latency, token cost
- Vẽ hình: bảng so sánh RAG variants, đường cong τ, đồ thị lan truyền mẫu, biểu đồ cost/quality trade-off
- Mọi hình sinh từ script trong `eval/`, không vẽ tay

### Tuần 22–23 — Viết và dọn dẹp

- Viết luận văn (chương Nhánh A đã có nháp từ Tuần 12)
- Dọn repo, viết README có hướng dẫn reproduce
- Chọn license, công khai GitHub
- Kiểm tra: người lạ clone repo có chạy lại được bảng kết quả không?

### Tuần 24 — Bảo vệ

- Slide
- **Kịch bản demo 5 phút** (đã viết nháp từ Tháng 4):
  1. `docker compose --profile dev up` → replay chạy, alert vào timeline
  2. Click alert bị phân loại False Positive → xem context RAG và lý do LLM bác bỏ
  3. Chuyển sang cascade fault → 7 alert gom thành 1 Incident
  4. Mở Incident → đồ thị lan truyền + diagnostic JSON chỉ đúng root cause
  5. Tab Experiment → bảng so sánh 5 biến thể, sinh tự động
- Tổng duyệt ít nhất 2 lần

---

## 8. Ngưỡng cắt scope khi trễ tiến độ

Cắt theo thứ tự này, từ trên xuống:

| Ưu tiên cắt | Hạng mục | Ảnh hưởng |
|---|---|---|
| 1 | Hybrid BM25 + Graph (Tuần 10) | So sánh 4 biến thể thay vì 5. Chấp nhận được. |
| 2 | Backward tracing mức 2 (Tuần 15) | Chỉ báo cáo 1-hop. Đã dự phòng trong bảng rủi ro. |
| 3 | Dashboard React → Streamlit (Tuần 18) | Xấu hơn nhưng demo vẫn đủ. |
| 4 | Đánh giá bằng người 30 → 15 incident (Tuần 20) | Giảm độ tin cậy, vẫn có số liệu. |
| 5 | Cross-modal RAG (Tuần 9) | So sánh 3 biến thể. Bắt đầu ảnh hưởng đến đóng góp. |

**Không bao giờ cắt:**
- Kiểm tra nhãn Tuần 1
- Tái lập baseline Tuần 3
- Eval harness Tuần 4
- Chạy test split đúng quy trình Tuần 11
- Bootstrap CI

Đây là những thứ giữ cho luận văn hợp lệ. Cắt chúng thì phần còn lại không còn giá trị.

---

## 9. Nhịp làm việc hàng tuần

| Thời điểm | Việc |
|---|---|
| Đầu tuần | Đọc phần tuần này trong file, nạp vào context của coding agent |
| Trong tuần | Mỗi task xong → commit + cập nhật `experiment-log.md` nếu có chạy thực nghiệm |
| Cuối tuần | Đối chiếu DoD. Chưa đạt → quyết định: bù tuần sau hay cắt theo §8 |
| Cuối tháng | Gửi GVHD bản tóm tắt 1 trang: đã làm gì, số liệu gì, rủi ro gì |
