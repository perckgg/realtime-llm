# 04 — Lộ trình triển khai 24 tuần

Mỗi tuần có một kết quả kiểm chứng được. Nếu cuối tuần không đạt, xem §8 để biết cắt gì.

**Cách dùng với AI coding agent:** chỉ nạp phần tuần đang làm vào context. Không nạp cả file, để agent không tự nhảy sang task tương lai.

> **Bản điều chỉnh 2026-10-18 (QĐ-011, QĐ-012).** GĐ2 chuyển từ "so sánh 5 biến thể
> RAG" sang **đề xuất giải pháp CTAV và chứng minh nó**, vẫn giữ platform để demo — xem
> `08-research-direction.md`. Tuần 3–7 (2026-09-14 → 2026-10-18) không có tiến độ GĐ2;
> lịch từ Tuần 8 được xếp lại theo ngày thật, giữ mốc bảo vệ Tuần 24. Số tuần là **tuần
> lịch** tính từ Tuần 1 = 2026-08-31.

| Chặng | Tuần | Ngày | Kết quả |
|---|---|---|---|
| 0. Nền tảng dữ liệu | 1–2 | 08-31 → 09-13 | **Xong** |
| 1. Tái lập | 8–10 | 10-19 → 11-08 | Port đúng (G-port), baseline paper đúng (G-paper), harness chạy |
| 2. Chứng minh trên `val` | 11–15 | 11-09 → 12-13 | H0, H1, CTAV (C2–C4), Rescue Score, đăng ký giả thuyết |
| 3. Test, RCA, platform | 16–19 | 12-14 → 2027-01-10 | Kết quả `test` (G-test), RCA, platform nối dữ liệu thật |
| 4. Đóng gói | 20–24 | 2027-01-11 → 02-14 | Đánh giá bằng người, số liệu chốt, luận văn, bảo vệ |

---

## Chặng 0 — Nền tảng và kiểm chứng dữ liệu (xong)

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
- [x] Biết chính xác có bao nhiêu fault window có nhãn root-cause
- [x] Split được commit, không đổi nữa
- [x] Nếu thiếu nhãn: đã ra quyết định (gán tay / đổi dataset) và ghi vào `docs/experiment-log.md`

**Cổng chặn:** không sang Tuần 2 nếu chưa trả lời được câu hỏi nhãn. — **QUA** (QĐ-001).

### Tuần 2 — Hạ tầng và port GĐ1

| Task | Output |
|---|---|
| `docker-compose.yml` profiles dev/full | `docker compose --profile dev up -d` chạy được |
| `infra/clickhouse/init.sql`, `infra/postgres/init.sql` theo `03` | Bảng được tạo tự động |
| `packages/schemas/` — toàn bộ model ở `03` §1 | Import được từ mọi service |
| Port `services/replayer` từ GĐ1 | Phát được 50 window |
| Port `services/detector` (Isolation Forest 0.85) | Sinh được AlertCandidate |

**DoD Tuần 2:**
- [x] Một lệnh dựng được toàn bộ môi trường dev
- [x] Replay 50 window → alert candidate ghi vào ClickHouse

**QUA** 2026-09-07 (QĐ-009, QĐ-010). Review 2026-10-18 tìm ra 6 điểm cần sửa ở detector (`08` §8.1) — sửa ở Tuần 8.

### Tuần 3–7 — không có tiến độ GĐ2

Ghi nhận trung thực. Phần việc của Tuần 3–4 cũ (interface, BM25, judge, harness, graph) dời sang Chặng 1.

---

## Chặng 1 — Tái lập (Tuần 8–10)

Mục tiêu: trước khi đề xuất gì mới, chứng minh pipeline GĐ2 **tái lập đúng** cả GĐ1 lẫn paper. Không qua hai cổng chặn này thì mọi kết quả sau vô nghĩa.

### Tuần 8 (10-19) — Sửa detector, hợp đồng dữ liệu, port BM25 + judge

| Task | Output |
|---|---|
| Sửa D1–D6 (`08` §8.1); chốt Q1–Q5 (`08` §9) | Detector đúng; quyết định ghi experiment-log |
| Định nghĩa 4 Protocol ở `01` §5 | `packages/schemas/protocols.py` |
| Model `ContextEvent` (có `origin`, `graph_distance`), `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (có trường policy) theo `03` §1.3–1.4, §1.6 | `packages/schemas/models.py` |
| Loader log/trace Nezha → kho bằng chứng (evidence store) | `packages/schemas/evidence.py` |
| Port BM25 hybrid; **bỏ tag fault type khỏi truy vấn** (lỗi paper §3.5) | `services/retrieval/bm25_hybrid.py` + test chặn rò nhãn |
| Port judge: prompt, 3 nhãn, `require_evidence`, cache (key có `repeat`), client `gemini-2.5-flash-lite` (QĐ-013, không local-first), **backend `mock`** của GĐ1 | `services/judge/` |
| `retrieval/registry.py` — ánh xạ tên → class | Config chọn được strategy |

**DoD Tuần 8:**
- [ ] `py -m pytest`, `mypy packages services`, `ruff check .` đều sạch
- [ ] Một candidate dev đi hết BM25 → judge (mock và LLM thật) → `JudgedAlert` có `debug` đầy đủ
- [ ] Unit test: cache key, không rò tag fault type, `require_evidence`

### Tuần 9 (10-26) — Eval harness + cổng chặn G-port

| Task | Output |
|---|---|
| `eval/harness/runner.py` — đọc config, chạy pipeline, ghi results | `py -m eval run --config X` |
| `eval/harness/metrics.py` — P/R/F1/FPR/coverage/latency/tokens/số lần gọi/chi phí | `metrics.json` |
| `eval/harness/stats.py` — bootstrap CI **và McNemar cặp** | CI + p-value trong metrics.json |
| Ánh xạ `paper_300` (window GĐ1 120 s) → `window_id` GĐ2; ghi rõ lệch một bước (cửa sổ GĐ1 nhìn tới, buffer GĐ2 nhìn lui) | `scripts/map_gd1_windows.py` |
| `eval/configs/gd1_phase4_parity.yaml` — đúng cấu hình GĐ1 Phase 4: threshold 0.95, fit 1.000 cửa sổ đầu, gate 0.80/0.98, ngân sách 30 lần gọi, judge mock, top-6 | Config parity |

**DoD Tuần 9 — cổng chặn G-port (QĐ-012):** so **từng tầng, mỗi tầng nhận đúng đầu vào của GĐ1**, để lỗi port lộ ra đúng chỗ:
- [ ] Retrieval: đưa 40 candidate từ audit GĐ1 vào BM25 GĐ2 → top-6 trùng doc ID với audit GĐ1; mọi khác biệt giải thích được
- [ ] Judge mock: cùng candidate + context GĐ1 → verdict trùng audit GĐ1
- [ ] Toàn pipeline: P = 0.3158 (6 TP, 13 FP), FPR = 0.0458, recall 0.375; lệch tối đa 1 cửa sổ mỗi ô ma trận nhầm lẫn, giải thích được
- [ ] Detector: so phân phối điểm với `detector_only_audit` (không đòi trùng tuyệt đối vì đơn vị cửa sổ khác — QĐ-009)
- [ ] Sinh đủ 6 file output của `02` §3.3

Lệch hơn mức trên = port sai. **Dừng và sửa**, không sang Tuần 10.

### Tuần 10 (11-02) — Service graph, port C1, cổng chặn G-paper

| Task | Output |
|---|---|
| `scripts/build_service_graph.py` + `packages/graph/` — port `legacy/src/phase2/retrieval/graph_builder.py` | Đồ thị NetworkX |
| Đo coverage của graph theo `02` §1.3 | `docs/graph-coverage.md` |
| Port Fusion Score (C1): `fusion_ranker.py`, `topology_candidate_expander.py` → `hybrid_bm25_graph` (2-hop, α = 0.35, β = 0.25, γ = 0.40, τ = 300 s) | `services/retrieval/hybrid_bm25_graph.py` |
| `eval/configs/paper_viewA_replay.yaml` — `paper_500`, gemini-2.5-flash-lite, cache GĐ1 | Config tái lập paper |

**DoD Tuần 10 — cổng chặn G-paper:**
- [ ] Tái lập Table 1 của paper (full budget) **từ cache, không gọi API**: BM25 F1 0.7030 / FP 7; Topology F1 0.4759 / FP 137
- [ ] Cache hit 100%. Cache miss nghĩa là prompt GĐ2 khác GĐ1 → port sai, điều tra
- [ ] `docs/graph-coverage.md` có ba chỉ số; nếu coverage fault window < 60%: ghi fallback vào experiment-log

**Deliverable Chặng 1:** pipeline GĐ2 tái lập đúng GĐ1 và paper; harness có CI + McNemar; graph có số liệu.

---

## Chặng 2 — Chứng minh trên `val` (Tuần 11–15)

Mọi tuning ở chặng này chỉ trên `val`. Không chạm `test`.

### Tuần 11 (11-09) — H0: tái lập vấn đề trên split GĐ2

| Task | Output |
|---|---|
| Chạy BM25, C1 (topology chưa hiệu chỉnh), LLM-không-RAG, detector-only trên `val`; judge chốt ở Q1; ngân sách giới hạn + toàn bộ; 3 lần chạy | `eval/results/h0_*` |
| Ablation retrieval-only (không gọi LLM) lưới α, β, γ — gồm temporal-only (β = 1), graph-only (γ = 1) | Bảng ablation C1 |
| Viết nháp chương "Bài toán" của luận văn từ paper | Nháp chương |

**DoD:** bảng H0 có CI và McNemar. Nếu **không** tái lập được (topology không tăng FPR trên split GĐ2): dừng, ghi experiment-log, trao đổi GVHD trước khi đi tiếp — câu chuyện của luận văn phải viết lại.

### Tuần 12 (11-16) — H1: cơ chế thiên lệch xác nhận

| Task | Output |
|---|---|
| Chọn mẫu cố định (seed 42) gồm cửa sổ normal + toàn bộ fault candidate của `val` | `eval/samples/h1_val.json` |
| Giữ k = 6, thay tỷ lệ bằng chứng mở rộng qua graph 0 / 33 / 67 / 100%; thêm biến thể xáo thứ tự | `eval/results/h1_*` |

**DoD:** đồ thị FPR theo tỷ lệ bằng chứng graph, có CI; kết luận H1 (giữ hoặc bác bỏ) ghi experiment-log.

### Tuần 13 (11-23) — C2 + C3: chính sách quyết định

| Task | Output |
|---|---|
| `services/judge/policy.py` — asymmetric gating (θ_local, θ_topo) + evidence anchoring | Module + unit test |
| Áp policy lên verdict **đã cache** từ Tuần 11 — không gọi LLM mới | Chạy lại rẻ |
| Quét θ_topo; chọn trên `val` | Đường cong θ_topo vs (Recall, FPR) |
| **Song song:** `rca_agent/grouping.py` bản khởi động (chỉ cần timestamp + graph) | Module chạy độc lập |

**DoD:** đường cong θ_topo; bộ (θ_local, θ_topo) chọn trên `val` ghi experiment-log.

### Tuần 14 (11-30) — C4 + ablation H3, chốt CTAV

| Task | Output |
|---|---|
| `services/judge/routing.py` — BM25 trước, topology chỉ khi UNCERTAIN / không có bằng chứng | Module + unit test |
| Quét ngân sách gọi LLM (H4) | Đường cong F1 theo ngân sách |
| Ablation H3: CTAV đầy đủ, bỏ C2, bỏ C3, bỏ C4 | Bảng ablation `val` |

**DoD:** `eval/configs/ctav_final.yaml` chốt; bảng H3 trên `val` có CI.

### Tuần 15 (12-07) — Rescue Score + đăng ký giả thuyết

| Task | Output |
|---|---|
| Tính trước `Λ_log`, `Φ_topo`, `Δ_time` cho mọi window | `data/rescue_features.parquet` |
| Quét 147 tổ hợp (η1, η2, η3, τ) trên giá trị đã tính | `eval/results/rescue_ablation/` |
| Vẽ đường cong τ vs (Recall, số lần gọi LLM); quyết định giữ 3 hay rút về 2 tham số | Hình + experiment-log |
| **Đăng ký giả thuyết H0–H5** với ngưỡng định lượng, danh sách config sẽ chạy trên `test` | Mục "Đăng ký giả thuyết" trong experiment-log, commit riêng |

**DoD:** giả thuyết đã commit **trước** khi chạy bất kỳ thứ gì trên `test`.

**Deliverable Chặng 2:** CTAV chốt cấu hình; bằng chứng H0, H1, H3 trên `val`; giả thuyết đăng ký.

---

## Chặng 3 — Test, RCA, platform (Tuần 16–19)

### Tuần 16 (12-14) — cổng chặn G-test

**Lần đầu tiên chạm vào `test`.**

| Task | Output |
|---|---|
| Chạy các config đã đăng ký trên `test`: BM25, C1, CTAV, ablation C2/C3/C4, LLM-không-RAG, detector-only; 3 lần chạy | `eval/results/comparison_final/` |
| Bootstrap CI + McNemar; bảng H0–H4 | Bảng chính của luận văn |
| Chấm context precision thủ công trên 50 window | `eval/manual/` |

**DoD:** bảng H0–H4 trên `test`; kết luận H2 viết ra **dù kết quả là gì** — "CTAV không vượt BM25" cũng là kết quả hợp lệ, phải báo cáo trung thực.

### Tuần 17 (12-21) — Alert Grouping + Propagation mức 1

| Task | Output |
|---|---|
| Hoàn thiện `grouping.py`; quét `T_group ∈ {180, 300, 600}` s trên `val` | Module ổn định |
| Alert Reduction Ratio trên cascade fault; ghi `incidents` vào PostgreSQL | Chỉ số đầu tiên của Nhánh B |
| `propagation.py` mức 1 — backward 1-hop thuần thuật toán; Hit@1/Hit@3 trên `val` | Kết quả sơ bộ H5 |

**DoD:** ARR ≥ 30% trên network_delay; có Hit@1/Hit@3 mức 1.

### Tuần 18 (12-28) — Diagnostic Summary (+ Propagation mức 2 nếu kịp)

| Task | Output |
|---|---|
| `summarizer.py` — JSON theo schema `03` §2; validator + `diagnostic_rejected`; `require_evidence`; chặn câu lệnh thực thi trong `suggested_actions` | JSON valid rate đo được |
| `propagation.py` mức 2 — LLM lập luận ngược toàn call chain (**cắt đầu tiên nếu trễ**, §8) | So sánh 1-hop vs full path |

**DoD:** JSON valid rate ≥ 0.95 trên `val`.

### Tuần 19 (2027-01-04) — Platform: tích hợp end-to-end, nối dashboard dữ liệu thật

| Task | Output |
|---|---|
| `rca_agent/pipeline.py` điều phối CTAV → grouping → propagation → summary | Chạy được từ đầu đến cuối |
| `services/api` (FastAPI) — endpoint khớp `services/web/src/api/types.ts` | API đọc ClickHouse/Postgres |
| Nối 4 màn hình dashboard (MVP đã có, QĐ-007) sang API thật; hiển thị nguồn gốc bằng chứng và lý do policy | Dashboard dữ liệu thật |
| Chế độ demo **offline từ cache** (không cần mạng/API key) | Demo an toàn lúc bảo vệ |
| Chạy end-to-end trên `test` → kết quả chính thức H5; đo E2E latency, token, cache hit | `runtime.json` |

**DoD:** `docker compose --profile dev up -d` + replay → 4 màn hình hiển thị dữ liệu thật, có loading/empty state; chạy được khi rút mạng.

**Deliverable Chặng 3:** kết quả chính thức cả hai nhánh trên `test`; platform demo được.

---

## Chặng 4 — Đóng gói (Tuần 20–24)

### Tuần 20 (01-11) — Đánh giá bằng người + phân tích lỗi

| Task | Output |
|---|---|
| Lấy mẫu 30 incident, chấm 3 tiêu chí theo `02` §4.4; nếu có thể nhờ người thứ hai chấm 20% | `eval/manual/diagnostic_quality.csv` |
| Phân tích ca sai: FP còn lại của CTAV thuộc loại nào, vì sao; ca RCA sai | Nguyên liệu chương thảo luận |
| Tổng duyệt demo lần 1 | Ghi lại lỗi demo |

### Tuần 21 (01-18) — Chốt số liệu và hình vẽ

- Tổng hợp toàn bộ chỉ số H0–H5, chi phí, độ trễ.
- Hình: bảng so sánh, đường cong θ_topo, đường cong ngân sách, đường cong τ, đồ thị H1, đồ thị lan truyền mẫu.
- Mọi hình sinh từ script trong `eval/`, không vẽ tay.

### Tuần 22–23 (01-25 → 02-07) — Viết và dọn dẹp

- Viết luận văn (chương Bài toán đã có nháp từ Tuần 11).
- Dọn repo, README hướng dẫn reproduce, chọn license, công khai GitHub.
- Kiểm tra: người lạ clone repo có chạy lại được bảng kết quả không?
- Tổng duyệt demo lần 2. **Lưu ý:** Tết Nguyên đán 2027 rơi vào khoảng 2027-02-06 — chốt bản luận văn trước Tết.

### Tuần 24 (02-08) — Bảo vệ

- Slide.
- Kịch bản demo 5 phút: xem `08-research-direction.md` §6.

---

## 8. Ngưỡng cắt scope khi trễ tiến độ

Không còn tuần đệm (Tuần 12 cũ đã dùng hết do Tuần 3–7 trễ). Cắt theo thứ tự này, từ trên xuống:

| Ưu tiên cắt | Hạng mục | Ảnh hưởng |
|---|---|---|
| 1 | Propagation mức 2 — LLM full path (Tuần 18) | Chỉ báo cáo 1-hop. Đã dự phòng. |
| 2 | Rescue Score (Tuần 15) rút về 2 tham số hoặc bỏ C5 | Paper cho thấy Context Rescue không promote thêm candidate nào; ảnh hưởng nhỏ đến H2 |
| 3 | Đánh giá bằng người 30 → 15 incident (Tuần 20) | Giảm độ tin cậy, vẫn có số liệu |
| 4 | Màn hình Experiment động → bảng tĩnh sinh từ script | Demo vẫn đủ 3 màn hình chính |
| 5 | Số lần chạy của các ablation phụ 3 → 2 (không áp cho H2) | CI rộng hơn ở ablation phụ |

**Không bao giờ cắt:**
- Cổng chặn G-port (Tuần 9), G-paper (Tuần 10), G-test (Tuần 16)
- Eval harness + bootstrap CI + McNemar
- H0, H2, và ít nhất C2 trong H3 — đây là phần "chứng minh" GVHD yêu cầu
- Đăng ký giả thuyết trước khi chạm `test`
- Platform demo end-to-end: Timeline, Alert detail, Incident detail chạy trên dữ liệu thật

Đây là những thứ giữ cho luận văn hợp lệ. Cắt chúng thì phần còn lại không còn giá trị.

---

## 9. Nhịp làm việc hàng tuần

| Thời điểm | Việc |
|---|---|
| Đầu tuần | Đọc phần tuần này trong file, chép vào `docs/CURRENT-WEEK.md`, nạp vào context của coding agent |
| Trong tuần | Mỗi task xong → commit + cập nhật `experiment-log.md` nếu có chạy thực nghiệm |
| Cuối tuần | Đối chiếu DoD. Chưa đạt → quyết định: bù tuần sau hay cắt theo §8 |
| Cuối mỗi chặng | Gửi GVHD bản tóm tắt 1 trang: đã làm gì, số liệu gì, rủi ro gì |
