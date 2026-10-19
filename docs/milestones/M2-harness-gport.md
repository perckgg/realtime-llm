# M2 — Eval harness + cổng chặn G-port

| | |
|---|---|
| Ngày đóng mốc | 2026-10-19 |
| Hạn mục tiêu | 2026-11-01 (sớm 13 ngày) |
| Kết luận | **QUA CÓ ĐIỀU KIỆN**: tầng 1, 2, 3a của G-port trùng GĐ1 tuyệt đối; tầng 3b (toàn pipeline với detector GĐ2) lệch FP +6, vượt ngưỡng ±1. Đã phân rã hết nguyên nhân, nằm ở detector và cách biểu diễn candidate, không ở mã port. **Cần bạn quyết định (V10)** |
| Commit | commit M2 (cùng commit với báo cáo này) |
| Quyết định liên quan | QĐ-017 (V7–V9), QĐ-018 (kết quả M2) |

## 1. Kết quả hiện tại

| DoD | Đạt? | Bằng chứng |
|---|---|---|
| Retrieval: 40 candidate Phase 4 → top-6 trùng doc ID | Đạt | 40/40, đúng thứ tự — `eval/results/gport_layers_phase4.json` |
| Judge mock: verdict trùng audit GĐ1 | Đạt | 30/30 |
| Toàn pipeline: 6 TP / 13 FP, lệch ≤ 1 mỗi ô | **Một phần** | Phần sau detector (tầng 3a): 6/13/10/271, trùng tuyệt đối. Toàn pipeline GĐ2 (3b): 6/19/10/265 |
| Detector: so phân phối điểm | Đạt (theo QĐ-009) | Spearman 0,79; candidate 41 vs 40, chung 32 |
| 6 file output `02` §3.3; pytest/mypy/ruff sạch | Đạt | 7 file (thêm `judged.jsonl`); 100 test; mypy `packages services eval`; ruff |
| Số candidate thật trên `val` + chi phí | Đạt | Bảng M2-2; QĐ-018 |
| Báo cáo 4 phần | Đạt | File này |

Việc đã làm:

| Việc | Output |
|---|---|
| 1. V9 + D6 | `IsolationForestDetector.top_features()`; `packages/schemas/nezha.py` (bỏ `packages` → `scripts`); tham số detector đọc từ config |
| 2. Harness | `py -m eval run --config X` — `eval/harness/runner.py`; ClickHouse tùy chọn (đã thử ghi thật); chế độ `stages: detector` |
| 3. Chỉ số | `eval/harness/metrics.py` (tập có telemetry + toàn bộ), `stats.py` (bootstrap CI, McNemar chính xác) |
| 4. G-port | `scripts/map_gd1_windows.py` → `eval/configs/gd1_phase4_windows.csv`; `eval/configs/gd1_phase4_parity.yaml`; `scripts/gport_layers.py` |
| 5. Candidate `val` | `eval/configs/val_detector_count.yaml` → `eval/results/val_detector_count_v1/` |

**Bảng M2-1. G-port theo tầng** (mỗi tầng nhận đúng đầu vào của GĐ1).

| Tầng | Kết quả | Đạt |
|---|---|---|
| 1. Retrieval BM25 | Top-6 trùng 40/40 | Đạt |
| 2. Judge mock | Verdict trùng 30/30 | Đạt |
| 3a. Gate + ngân sách + retrieval + judge + quyết định (candidate GĐ1) | 6/13/10/271 = GĐ1 | Đạt |
| 3b. Toàn pipeline GĐ2 | 6/19/10/265 — P 0,2400 vs 0,3158; R 0,375 = 0,375; FPR 0,0669 vs 0,0458 | Lệch FP +6 |
| 4. Detector | Spearman 0,79; trung bình điểm 0,604 vs 0,584 | So phân phối |

14 cửa sổ lệch ở 3b đều là normal. 6 cửa sổ do context khác: cả hai cùng chấm, nhưng
candidate GĐ2 mang cửa sổ thời gian và metric của GĐ2, nên truy vấn BM25 khác. 8 cửa sổ do
tập candidate của detector khác, kéo theo thứ tự tiêu 30 lần gọi khác.

**Phát hiện về Phase 4:** 10/13 FP của Phase 4 GĐ1 đến từ quy tắc "hết ngân sách →
route_alert" (cả 10 là normal); judge chỉ gây 3 FP.

**Bảng M2-2. Detector GĐ2 trên `val`** (threshold 0,85, fit dev).

| Tập | Cửa sổ | Candidate | TP | Recall detector (CI 95%) | FPR |
|---|---|---|---|---|---|
| Có telemetry (chính, QĐ-017) | 7.636 | 1.749 | 109 / 209 | 0,52 (0,45–0,59) | 0,221 |
| Toàn split | 28.898 | 5.677 | 109 / 209 | 0,52 | 0,194 |

Chi phí mỗi run trên tập chính ≈ 1.749 × 0,00038 USD ≈ **0,67 USD**. Giới hạn thật sự là tốc
độ: khoảng 2 giờ mỗi run ở mức 15 lần gọi/phút của GĐ1.

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| R1 | Quy tắc ánh xạ cửa sổ GĐ1 [T, T+120) → mẫu cuối của GĐ2 | `scripts/map_gd1_windows.py` (docstring), `eval/configs/gd1_phase4_windows.csv` | Mọi so sánh tầng 3b, 4 phụ thuộc vào nó; lưới GĐ1 trôi 1 s so với mẫu |
| R2 | Gate / ngân sách / quyết định của harness | `eval/harness/runner.py:142` (`Gate`), `:167` (`_decision`) | Đã trùng GĐ1 ở tầng 3a, nhưng mặc định GĐ2 (gate tắt, không ngân sách, hết ngân sách → manual_review) chưa chạy trên dữ liệu thật |
| R3 | Chỉ số: recall tính trên mọi fault window; manual_review không tính là alert; CI bootstrap multinomial | `eval/harness/metrics.py:25-70`, `stats.py` | Đây là số đi vào luận văn; `tests/test_harness.py` có ca kiểm tay |
| R4 | `parity_query_terms` đọc nhãn — chỉ được bật trong config parity | `eval/harness/runner.py:179` (`run`), `eval/configs/gd1_phase4_parity.yaml` | Bật nhầm ở config GĐ2 là rò nhãn. Harness chỉ cài hàm này khi cờ bật; nên thêm kiểm tra cấm cờ khi `split` là val/test (đề xuất M3) |
| R5 | Mask `has_telemetry` | `packages/schemas/evidence.py` (`has_telemetry`) | Định nghĩa tập chấm chính của cả luận văn (QĐ-017) |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| V10 | **G-port tầng 3b lệch FP +6** (> ±1). Các tầng nhận đầu vào GĐ1 (1, 2, 3a) đều trùng tuyệt đối. Phần lệch đến từ detector (cửa sổ 60 s so với 120 s, đã chấp nhận ở QĐ-009) và từ việc candidate GĐ2 mang dữ liệu của GĐ2 | (a) Coi G-port là đạt, vì tiêu chí ±1 giả định cùng một detector; ghi phân rã vào luận văn. (b) Viết thêm một "detector chế độ GĐ1" (cửa sổ 120 s, chuẩn hoá z-score, đặc trưng GĐ1) chỉ để tầng 3b khớp; ~1 ngày, không dùng cho kết quả khoa học. (c) Nới tiêu chí thành "lệch chỉ ở normal, TP/FN trùng" | **(a)**. Chứng minh port đúng đã nằm ở tầng 3a; (b) chỉ tái tạo lại GĐ1 chứ không kiểm thêm gì của GĐ2 | **Có**: roadmap ghi "lệch hơn mức trên ⇒ dừng". Cần bạn chốt trước M3 |
| V11 | Tốc độ gọi API: ~2 giờ mỗi run trên tập chính ở mức 15 lần/phút; M4 có nhiều run (BM25, C1, LLM-không-RAG, lưới α/β/γ chỉ retrieval, repeat × 3) | (a) Kiểm tra tier API key, nâng `max_calls_per_minute` (bậc trả phí của flash-lite cho phép cao hơn nhiều); (b) giữ 15/phút, chạy qua đêm | **(a)** — bạn xem tier key trong Google AI Studio rồi báo tôi giới hạn | Không chặn M3; ảnh hưởng lịch M4 |
| V1 | Mail GVHD (nên kèm V7, V8 và phát hiện Phase 4) | | | Nên trước M4 |

## 4. Plan cho mốc tiếp theo (M3 — service graph + C1 + G-paper)

1. `scripts/build_service_graph.py` + `packages/graph/`: port `legacy/src/phase2/retrieval/graph_builder.py` (NetworkX, có hướng, từ trace).
2. `docs/graph-coverage.md`: ba chỉ số coverage theo `02` §1.3.
3. `services/retrieval/hybrid_bm25_graph.py` (C1): port `fusion_ranker.py` + `topology_candidate_expander.py`; 2-hop, α 0,35 / β 0,25 / γ 0,40, τ 300 s; mỗi event ghi `origin`, `graph_distance`; chế độ parity như BM25.
4. Nửa topology của G-paper: mở rộng `dump_gd1_prompts.py` / `check_gd1_parity.py` sang biến thể `topology_aware_fusion_top6`, đòi trúng 489/489 cache. Thêm `eval/configs/paper_viewA_replay.yaml`.
5. Chặn `parity_query_terms` trên val/test (R4).

DoD (`04` M3): tái lập Table 1 của paper từ cache, không gọi API (BM25 đã đạt ở M1:
F1 0,7030 / FP 7; còn Topology F1 0,4759 / FP 137); cache hit 100%; `docs/graph-coverage.md`.

Rủi ro: port fusion ranker phải trùng từng byte prompt (graph từ trace GĐ1, thứ tự duyệt
BFS, cách cắt top-k); graph GĐ1 dựng trên corpus đã lọc theo nhãn — cần graph riêng cho GĐ2
dựng trên toàn bộ trace.

## Phụ lục

**Sai lệch so với plan.**
- G-port thêm tầng 3a (đầu vào là candidate GĐ1) để khoanh vùng lỗi, vì tầng 3b không thể trùng khi detector khác (QĐ-009).
- Parity dùng `budget_exhausted_action: route_alert` theo hành vi của lần chạy Phase 4 đã commit, khác code GĐ1 hiện tại.
- Q2 đã chốt bằng QĐ-017; việc 5 chỉ còn là ước chi phí.

**Nguyên liệu cho luận văn.**
- Bảng M2-1: kiểm chứng port theo tầng (chương Thực nghiệm, mục tái lập).
- Phát hiện Phase 4 (10/13 FP do quy tắc ngân sách): chương Bài toán / đánh giá lại GĐ1.
- Bảng M2-2: detector trên `val`, tập có telemetry so với toàn bộ.

**Lệnh tái lập M2.**

```bash
py scripts/map_gd1_windows.py                                    # ~30 s
py scripts/dump_gd1_prompts.py --split phase4 --max-total-calls 40
py -m eval run --config eval/configs/gd1_phase4_parity.yaml      # run_id mới nếu đã có
py scripts/gport_layers.py --run gd1_phase4_parity_v1            # Bảng M2-1
py -m eval run --config eval/configs/val_detector_count.yaml     # Bảng M2-2, ~5 phút
```
