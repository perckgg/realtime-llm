# 04 — Lộ trình triển khai theo cột mốc

> **Bản 2026-10-18 (QĐ-014).** Lộ trình tổ chức theo **cột mốc** (M0, M1, …), không theo
> tuần. Mỗi mốc có kết quả kiểm chứng được (DoD); một số mốc là **cổng chặn** — không qua
> thì không sang mốc sau. Hạn ở bảng dưới là **mục tiêu mềm**, chỉ dùng để biết đang sớm
> hay trễ so với mốc bảo vệ. Giải pháp và giả thuyết: `08-research-direction.md`.
>
> Bản trước (QĐ-011) đánh số theo tuần lịch ("Tuần 8"), gây nhầm với "Tuần 3" của bản
> gốc. Ánh xạ cũ → mới ở §11.

**Cách dùng với AI coding agent:** chỉ nạp phần mốc đang làm (`docs/CURRENT-MILESTONE.md`)
vào context. Không nạp cả file, để agent không tự nhảy sang việc của mốc sau.

---

## 1. Tổng quan

| Mốc | Tên | Loại | Hạn mục tiêu | Trạng thái |
|---|---|---|---|---|
| M0 | Nền tảng dữ liệu + hạ tầng | Cổng chặn (nhãn) | 2026-09-07 | **Xong** — báo cáo `docs/milestones/M0-nen-tang.md` |
| M1 | Sửa detector, hợp đồng dữ liệu, port BM25 + judge | | 2026-10-25 | **Xong** (2026-10-19) — `docs/milestones/M1-detector-bm25-judge.md` |
| M2 | Eval harness + kiểm tra port | **Cổng chặn G-port** | 2026-11-01 | **Xong** (2026-10-19) — `docs/milestones/M2-harness-gport.md` |
| M3 | Service graph + C1 + tái lập paper | **Cổng chặn G-paper** | 2026-11-08 | **Xong** (2026-10-19) — `docs/milestones/M3-graph-c1-gpaper.md` |
| M4 | H0 — tái lập vấn đề trên split GĐ2 | Cổng chặn (hướng nghiên cứu) | 2026-11-15 | **Xong** (2026-10-29; V24 (b), GVHD đồng ý, QĐ-027) — `docs/milestones/M4-h0.md` |
| M5 | H1 — cơ chế thiên lệch xác nhận (trục thời gian / loại bằng chứng, QĐ-027) | | 2026-11-22 | **Chờ xem + V28** (mở 2026-10-29; QĐ-028) — `docs/milestones/M5-h1.md` |
| M6 | CTAV: C2 + C3 + C4, ablation trên `val`, chốt cấu hình | | 2026-12-06 | |
| M7 | Rescue Score (C5) + đăng ký giả thuyết | | 2026-12-13 | |
| M8 | Chạy `test` một lần | **Cổng chặn G-test** | 2026-12-20 | |
| M9 | RCA Agent: grouping, propagation, summary | | 2027-01-03 | |
| M10 | Platform end-to-end + dashboard dữ liệu thật | | 2027-01-10 | |
| M11 | Đánh giá bằng người + phân tích lỗi | | 2027-01-17 | |
| M12 | Đóng gói: số liệu, luận văn, repo, bảo vệ | | Bảo vệ tuần 2027-02-08 | |

Không có thời gian đệm. Trễ ở mốc nào thì quyết định ngay theo §9, không đợi.

---

## 2. Quy trình đóng một mốc

Mỗi mốc chỉ được coi là xong khi đủ ba thứ:

1. **DoD của mốc đạt**, có bằng chứng (số liệu, lệnh tái lập, commit).
2. **Báo cáo mốc** `docs/milestones/M<n>-<ten>.md` viết theo mẫu ở `docs/milestones/README.md`,
   gồm đúng bốn phần:
   - **Kết quả hiện tại** — DoD từng dòng kèm bằng chứng.
   - **Cần review gì** — những chỗ người dùng phải tự kiểm (file:dòng, con số cần chạy lại, logic rủi ro).
   - **Vấn đề cần bạn giải quyết** — quyết định/blocker, mỗi cái có phương án + khuyến nghị.
   - **Plan cho mốc tiếp theo** — việc, DoD, rủi ro đã biết.
3. **Người dùng đã xem báo cáo** và trả lời các vấn đề chặn mốc sau.

Quyết định và lần chạy thực nghiệm vẫn ghi chi tiết ở `docs/experiment-log.md` (QĐ-xxx);
báo cáo mốc tổng hợp và dẫn chiếu về đó. Sau đó cập nhật `docs/CURRENT-MILESTONE.md` sang
mốc mới và bảng §1.

---

## M0 — Nền tảng dữ liệu + hạ tầng (xong)

Gộp Tuần 1–2 của bản gốc.

| Việc | Output |
|---|---|
| `scripts/verify_labels.py` — kiểm tra nhãn root-cause, trace `span_id`/`parent_span_id` | `docs/label-audit.md` |
| `scripts/make_splits.py` — dev/val/test nhóm theo lần tiêm lỗi, vùng đệm 600 s, seed 42 | `data/splits/*.json` đã commit |
| `docker-compose.yml` profiles dev/full; `infra/*/init.sql` theo `03` | `docker compose --profile dev up -d` |
| `packages/schemas/` (model `03` §1 tới `AlertCandidate`), `loaders.py` | Import được từ mọi service |
| Port `services/replayer` → `NezhaReplaySource`; `services/detector` → `IsolationForestDetector` | Replay 50 window → candidate vào ClickHouse |

**DoD:** đạt (QĐ-001..010). Review 2026-10-18 tìm ra 6 điểm cần sửa ở detector → chuyển sang M1.

---

## M1 — Sửa detector, hợp đồng dữ liệu, port BM25 + judge (xong)

Phần việc Tuần 3 của bản gốc, cộng các điểm sửa từ review.

| Việc | Output |
|---|---|
| D1–D6 (`08` §8.1): metric thiếu → giá trị gần nhất của pod + cờ thiếu (Q3); replayer phát lịch sử liên tục, split chỉ lọc cửa sổ được chấm (Q4); `score()` không trạng thái ẩn; mypy/ruff sạch; chặn `run_id` trùng; việc nhỏ | Detector đúng + số đo trước/sau |
| 4 Protocol theo `01` §5 | `packages/schemas/protocols.py` |
| `ContextEvent` (có `origin`, `graph_distance`), `RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (có trường CTAV) theo `03` §1.3–1.4 | `packages/schemas/models.py` |
| Loader log/trace Nezha → kho bằng chứng | `packages/schemas/evidence.py` |
| Port BM25 hybrid; **bỏ tag fault type khỏi truy vấn** (lỗi paper §3.5) | `services/retrieval/bm25_hybrid.py` |
| Port judge: prompt, 3 nhãn, `require_evidence`, cache (key có `repeat`), client `gemini-2.5-flash-lite` (QĐ-013), backend `mock` | `services/judge/` |
| `retrieval/registry.py` | Config chọn được strategy |

**DoD M1:**
- [ ] `py -m pytest`, `py -m mypy packages services`, `py -m ruff check .` sạch
- [ ] Một candidate dev đi hết BM25 → judge (mock và Gemini thật) → `JudgedAlert` có `debug` đầy đủ
- [ ] Unit test: cache key, không rò tag fault type, `require_evidence`, cách điền metric thiếu, lịch sử buffer liên tục
- [ ] QĐ-015 ghi kết quả D1/D2 (số đo trước/sau)

---

## M2 — Eval harness + cổng chặn G-port (xong)

| Việc | Output |
|---|---|
| `eval/harness/runner.py` — đọc config, chạy pipeline, ghi results | `py -m eval run --config X` |
| `eval/harness/metrics.py` — P/R/F1/FPR/coverage/latency/tokens/số lần gọi/chi phí | `metrics.json` |
| `eval/harness/stats.py` — bootstrap CI **và McNemar cặp** | CI + p-value |
| Ánh xạ `paper_300` (window GĐ1 120 s) → `window_id` GĐ2; ghi rõ lệch một bước | `scripts/map_gd1_windows.py` |
| `eval/configs/gd1_phase4_parity.yaml` — threshold 0.95, fit 1.000 cửa sổ đầu, gate 0.80/0.98, ngân sách 30, judge mock, top-6 | Config parity |
| Đếm số candidate thật trên `val` → ước tính chi phí API mỗi run; chốt Q2 | Ghi experiment-log |

**DoD M2 — cổng chặn G-port (QĐ-012):** so **từng tầng, mỗi tầng nhận đúng đầu vào của GĐ1**:
- [ ] Retrieval: 40 candidate từ audit GĐ1 → top-6 BM25 GĐ2 trùng doc ID; mọi khác biệt giải thích được
- [ ] Judge mock: cùng candidate + context → verdict trùng audit GĐ1
- [ ] Toàn pipeline: P = 0.3158 (6 TP, 13 FP), FPR = 0.0458, recall 0.375; lệch ≤ 1 cửa sổ mỗi ô ma trận nhầm lẫn, giải thích được
- [ ] Detector: so phân phối điểm với `detector_only_audit` (không đòi trùng tuyệt đối — QĐ-009)
- [ ] Đủ 6 file output của `02` §3.3

Lệch hơn mức trên = port sai. **Dừng và sửa**, không sang M3.

---

## M3 — Service graph + C1 + cổng chặn G-paper (xong)

| Việc | Output |
|---|---|
| `scripts/build_service_graph.py` + `packages/graph/` — port `legacy/src/phase2/retrieval/graph_builder.py` | Đồ thị NetworkX |
| Coverage của graph theo `02` §1.3 | `docs/graph-coverage.md` |
| Port Fusion Score (C1): `fusion_ranker.py`, `topology_candidate_expander.py` → `hybrid_bm25_graph` (2-hop, α = 0.35, β = 0.25, γ = 0.40, τ = 300 s) | `services/retrieval/hybrid_bm25_graph.py` |
| `eval/configs/paper_viewA_replay.yaml` — `paper_500`, cache `legacy/outputs/phase2/step7_rerun/quality_full_budget/cache/` | Config tái lập paper |

**DoD M3 — cổng chặn G-paper:**
- [ ] Tái lập Table 1 của paper (full budget) **từ cache, không gọi API**: BM25 F1 0.7030 / FP 7; Topology F1 0.4759 / FP 137
- [ ] Cache hit 100%. Cache miss = prompt GĐ2 khác GĐ1 → port sai, điều tra
- [ ] `docs/graph-coverage.md` có ba chỉ số; coverage fault window < 60% → ghi fallback vào experiment-log

---

## M4 — H0: tái lập vấn đề trên split GĐ2 (xong, 2026-10-29)

| Việc | Output |
|---|---|
| Tăng tốc C1 giữ nguyên ngữ nghĩa (V17, QĐ-022) — **xong** | `engine: vectorized`, `retrieval.workers` |
| C1-quota `k_graph` (V16 b, QĐ-022); chọn `k_graph` trên `val` (V18, QĐ-024) — **xong, `k_graph = 1`** | `services/retrieval/hybrid_bm25_graph.py`; `eval/results/m4_kgraph_*` |
| Chốt judge + prompt GĐ2 (V19, V20, QĐ-023) — **xong**: `gemini-2.5-flash`, `drop_metrics: ["PodSuccessRate(%)"]` | `judge.drop_metrics` |
| BM25, C1-paper (`k_graph = 0`), C1-quota (`k_graph = 1`), LLM-không-RAG, detector-only trên `val` (tập có telemetry); Gemini; ngân sách giới hạn + toàn bộ — **xong** (QĐ-026, 2026-10-28): C1 tăng recall + FPR so với BM25, không do bằng chứng lân cận (Phát hiện 7) | `eval/results/h0_*` |
| Ablation retrieval-only (không gọi LLM) lưới α, β, γ — gồm temporal-only (β = 1), graph-only (γ = 1) — **xong** (QĐ-025): giữ trọng số paper | `eval/results/m4_fusion_ablation_val_v1/` |
| Nháp chương "Bài toán" của luận văn từ paper + Phát hiện 1–6 — **xong** | `docs/drafts/chuong-bai-toan.md` |

Cập nhật 2026-10-20: ba dòng đầu được thêm sau M3 (V16–V20, xem báo cáo M3 §3 và QĐ-022..024); trạng thái ablation và H0 theo QĐ-025, QĐ-026.

**DoD M4 — cổng chặn hướng nghiên cứu:** bảng H0 có CI + McNemar. Nếu **không** tái lập
được (topology không tăng FPR trên split GĐ2): dừng, ghi experiment-log, trao đổi GVHD
trước khi đi tiếp — câu chuyện luận văn phải viết lại.

Kết quả: tái lập hiện tượng, không tái lập cơ chế (Phát hiện 7) ⇒ V24 (b): đổi trục C2, C3, H1
từ "khoảng cách đồ thị" sang "độ gần thời gian / loại bằng chứng", giữ khung CTAV (QĐ-027; GVHD
đồng ý 2026-10-29).

---

## M5 — H1: cơ chế thiên lệch xác nhận

Đổi trục theo QĐ-027: biến can thiệp là độ gần thời gian và loại bằng chứng, không còn là khoảng
cách đồ thị.

| Việc | Output |
|---|---|
| Mẫu cố định (seed 42): candidate normal có telemetry + toàn bộ fault candidate của `val`; pool bằng chứng cục bộ của mỗi candidate lấy từ `build_pool` | `eval/samples/h1_val.json` |
| Giữ k = 6, tỷ lệ event trong ±60 s quanh t₀: 0 / 33 / 67 / 100% (cùng loại bằng chứng) | `eval/results/h1_time_*` |
| Giữ k = 6 và độ gần thời gian, đổi thành phần trace ↔ log | `eval/results/h1_modality_*` |
| Xáo thứ tự cùng một tập event | `eval/results/h1_order_*` |
| Đối chứng âm: tỷ lệ lân cận 0 / 100% (k = 6) | `eval/results/h1_graph_*` |
| Đo phương sai LLM: `repeat ∈ {0, 1, 2}` trên tập con (QĐ-013) | Độ lệch giữa các lần gọi |

Chi phí ước tính: mỗi điều kiện ≈ 1.200 lần gọi ≈ 1,6–1,9 USD (QĐ-027).

**DoD M5:** đường tỷ lệ TRUE_ALERT trên normal (và recall trên fault) theo từng biến can thiệp, có
CI; kết luận H1 (giữ / bác bỏ) và đặc trưng chọn cho C2 ghi experiment-log.

---

## M6 — CTAV: C2 + C3 + C4, chốt cấu hình

| Việc | Output |
|---|---|
| Ngưỡng nền `duration_ms` theo service + operation trên `dev` (cho C3, QĐ-027) | `data/span_baseline.parquet` |
| `services/judge/policy.py` — asymmetric gating theo hồ sơ bằng chứng (θ_local, θ_topo; đặc trưng từ H1) + evidence anchoring vào bằng chứng bất thường tại s₀ (QĐ-027); áp lên verdict **đã cache** từ M4 | Module + unit test |
| Quét θ_topo; chọn trên `val` | Đường cong θ_topo vs (Recall, FPR) |
| `services/judge/routing.py` — BM25 trước, topology khi UNCERTAIN / thiếu bằng chứng | Module + unit test |
| Quét ngân sách gọi LLM (H4) | Đường cong F1 theo ngân sách |
| Ablation H3: CTAV đầy đủ, bỏ C2, bỏ C3, bỏ C4 | Bảng ablation `val` |
| **Song song:** `rca_agent/grouping.py` bản khởi động (chỉ cần timestamp + graph) | Module chạy độc lập |

**DoD M6:** `eval/configs/ctav_final.yaml` chốt; bảng H3 trên `val` có CI; θ chọn ghi experiment-log.

---

## M7 — Rescue Score (C5) + đăng ký giả thuyết

| Việc | Output |
|---|---|
| Tính trước `Λ_log`, `Φ_topo`, `Δ_time` cho mọi window | `data/rescue_features.parquet` |
| Quét 147 tổ hợp (η1, η2, η3, τ); đường cong τ vs (Recall, số lần gọi LLM); giữ 3 hay rút 2 tham số | `eval/results/rescue_ablation/` |
| **Đăng ký giả thuyết H0–H5** với ngưỡng định lượng + danh sách config sẽ chạy trên `test` | Mục "Đăng ký giả thuyết" trong experiment-log, commit riêng |

**DoD M7:** giả thuyết đã commit **trước** khi chạy bất kỳ thứ gì trên `test`.

---

## M8 — Cổng chặn G-test

**Lần đầu tiên chạm vào `test`.**

| Việc | Output |
|---|---|
| Chạy config đã đăng ký: BM25, C1, CTAV, ablation C2/C3/C4, LLM-không-RAG, detector-only | `eval/results/comparison_final/` |
| Bootstrap CI + McNemar; bảng H0–H4 | Bảng chính của luận văn |
| Chấm context precision thủ công trên 50 window | `eval/manual/` |

**DoD M8:** bảng H0–H4 trên `test`; kết luận H2 viết ra **dù kết quả là gì** — "CTAV không
vượt BM25" cũng là kết quả hợp lệ, phải báo cáo trung thực.

---

## M9 — RCA Agent

| Việc | Output |
|---|---|
| Hoàn thiện `grouping.py`; quét `T_group ∈ {180, 300, 600}` s trên `val`; ghi `incidents` vào PostgreSQL | Alert Reduction Ratio |
| `propagation.py` mức 1 — backward 1-hop thuần thuật toán | Hit@1/Hit@3 trên `val` |
| `propagation.py` mức 2 — LLM full call chain (**cắt đầu tiên nếu trễ**, §9) | So sánh 1-hop vs full path |
| `summarizer.py` — JSON theo `03` §2; validator + `diagnostic_rejected`; `require_evidence`; chặn câu lệnh thực thi | JSON valid rate |

**DoD M9:** ARR ≥ 30% trên network_delay; Hit@1/Hit@3 mức 1; JSON valid rate ≥ 0.95 trên `val`.

---

## M10 — Platform end-to-end + dashboard dữ liệu thật

| Việc | Output |
|---|---|
| `rca_agent/pipeline.py` điều phối CTAV → grouping → propagation → summary | Chạy từ đầu đến cuối |
| `services/api` (FastAPI) — endpoint khớp `services/web/src/api/types.ts` | API đọc ClickHouse/Postgres |
| Nối 4 màn hình dashboard (MVP đã có, QĐ-007) sang API thật; hiện nguồn gốc bằng chứng + lý do policy | Dashboard dữ liệu thật |
| Chế độ demo **offline từ cache** (không cần mạng/API key) | Demo an toàn lúc bảo vệ |
| Chạy end-to-end trên `test` → kết quả chính thức H5; E2E latency, token, cache hit | `runtime.json` |

**DoD M10:** `docker compose --profile dev up -d` + replay → 4 màn hình hiển thị dữ liệu thật,
có loading/empty state; chạy được khi rút mạng; kịch bản demo `08` §6 chạy trọn.

---

## M11 — Đánh giá bằng người + phân tích lỗi

| Việc | Output |
|---|---|
| Mẫu 30 incident, chấm 3 tiêu chí theo `02` §4.4; người thứ hai chấm 20% nếu có thể | `eval/manual/diagnostic_quality.csv` |
| Phân tích ca sai: FP còn lại của CTAV, ca RCA sai | Nguyên liệu chương thảo luận |
| Tổng duyệt demo lần 1 | Danh sách lỗi demo |

---

## M12 — Đóng gói và bảo vệ

- Chốt số liệu H0–H5, chi phí, độ trễ; mọi hình sinh từ script trong `eval/`.
- Viết luận văn (chương Bài toán đã có nháp từ M4); chốt bản trước Tết (~2027-02-06).
- Dọn repo, README reproduce, license, công khai GitHub; kiểm tra người lạ clone chạy lại được bảng kết quả.
- Tổng duyệt demo lần 2; slide; bảo vệ.

---

## 9. Ngưỡng cắt scope khi trễ tiến độ

Cắt theo thứ tự này, từ trên xuống:

| Ưu tiên cắt | Hạng mục | Ảnh hưởng |
|---|---|---|
| 1 | Propagation mức 2 — LLM full path (M9) | Chỉ báo cáo 1-hop. Đã dự phòng. |
| 2 | Rescue Score (M7) rút về 2 tham số hoặc bỏ C5 | Paper cho thấy Context Rescue không promote thêm candidate nào; ảnh hưởng nhỏ đến H2 |
| 3 | Đánh giá bằng người 30 → 15 incident (M11) | Giảm độ tin cậy, vẫn có số liệu |
| 4 | Màn hình Experiment động → bảng tĩnh sinh từ script (M10) | Demo vẫn đủ 3 màn hình chính |
| 5 | Số lần gọi lặp đo phương sai 3 → 2 trên ablation phụ (không áp cho H2) | CI rộng hơn ở ablation phụ |

**Không bao giờ cắt:**
- Cổng chặn G-port (M2), G-paper (M3), G-test (M8)
- Eval harness + bootstrap CI + McNemar
- H0, H2, và ít nhất C2 trong H3 — đây là phần "chứng minh" GVHD yêu cầu
- Đăng ký giả thuyết trước khi chạm `test` (M7)
- Platform demo end-to-end: Timeline, Alert detail, Incident detail chạy trên dữ liệu thật (M10)
- Báo cáo mốc sau mỗi mốc (§2)

---

## 10. Nhịp làm việc

| Thời điểm | Việc |
|---|---|
| Bắt đầu mốc | Chép phần mốc vào `docs/CURRENT-MILESTONE.md`, nạp vào context coding agent |
| Trong mốc | Mỗi việc xong → commit + `experiment-log.md` nếu có chạy thực nghiệm |
| Kết thúc mốc | Đối chiếu DoD → viết báo cáo mốc (§2) → người dùng review → mới sang mốc sau |
| Trễ hạn mục tiêu | Ghi vào phần "Vấn đề cần bạn giải quyết" của báo cáo; quyết định bù hay cắt theo §9 |
| Sau M3, M8, M10 | Gửi GVHD bản tóm tắt 1 trang lấy từ báo cáo mốc |

---

## 11. Ánh xạ từ các bản trước

| Mốc | Bản gốc (tuần công việc) | Bản QĐ-011 (tuần lịch) |
|---|---|---|
| M0 | Tuần 1–2 | Tuần 1–2 |
| M1 | Tuần 3 (phần interface, BM25, judge) | Tuần 8 |
| M2 | Tuần 3 (cổng chặn) + Tuần 4 (harness) | Tuần 9 |
| M3 | Tuần 4 (graph) + Tuần 5–6 + Tuần 10 (fusion) | Tuần 10 |
| M4 | — (mới, H0) | Tuần 11 |
| M5 | — (mới, H1) | Tuần 12 |
| M6 | Tuần 10 (fusion ablation) + mới C2–C4 | Tuần 13–14 |
| M7 | Tuần 8 (Rescue) | Tuần 15 |
| M8 | Tuần 11 | Tuần 16 |
| M9 | Tuần 13–15, 17 | Tuần 17–18 |
| M10 | Tuần 16, 18, 19 | Tuần 19 |
| M11 | Tuần 20 | Tuần 20 |
| M12 | Tuần 21–24 | Tuần 21–24 |
