# M7 — Rescue Score (C5) + đăng ký giả thuyết

| | |
|---|---|
| Ngày đóng mốc | **chưa đóng** — Rescue xong 2026-11-11; đăng ký giả thuyết là bản nháp, chờ V29, V33, V34 |
| Hạn mục tiêu | 2026-12-13 |
| Kết luận | Việc 1–2 xong; việc 3 (đăng ký) **chưa** — DoD M7 chưa đạt |
| Commit | xem `git log` ("M7: Rescue Score ..." và "M7: draft hypothesis registration") |
| Quyết định liên quan | QĐ-032, **QĐ-033**, mục "Đăng ký giả thuyết H0–H5" cuối `docs/experiment-log.md` |

## 1. Kết quả hiện tại

| Việc / DoD | Đạt? | Bằng chứng |
|---|---|---|
| 1. Tính trước Λ_log, Φ_topo, Δ_time cho mọi cửa sổ | Có | `scripts/build_rescue_features.py` → `eval/results/m7_rescue_features_val_v1/` (28.898 cửa sổ, 0 LLM) |
| 2. Quét 147 tổ hợp, đường τ, giữ 3 hay rút 2 | Có | `eval/results/m7_rescue_val_v1/` (`rescue.json`, `points.csv`); **rút về 2** (Φ_topo, Δ_time) |
| 2b. Chỉ chấm cửa sổ được cứu | Có | `m7_rescue_val_c1_v1`: 1.459 lần gọi, 1,03 USD theo token, 0 lỗi |
| 3. Đăng ký H0–H5 + danh sách config `test`, commit riêng | **Nháp** | Cuối `docs/experiment-log.md`; chờ V29, V33, V34 |
| DoD: giả thuyết commit trước khi chạm `test` | Chưa | `test` chưa bị chạm (không config nào dùng `split: test`) |

**Cách làm.** A = cảnh báo của chính CTAV chốt (không nhãn, nhân quả, 300 s). Cửa sổ được cứu không quay lại A
⇒ cả lưới tính offline; hợp 1.459 cửa sổ được cứu của 147 tổ hợp (đều khả thi, ≤ +50% lần gọi) chấm một lần
bằng prompt C1, rồi áp chính sách CTAV (θ 0,80, C3 `dev` p90). Quy tắc chọn (gồm "off") và quy tắc rút gọn
ghi trong code trước khi chấm.

**Bảng 1. Rescue trên CTAV** (`val`, 7.636 cửa sổ telemetry, 209 fault).

| | η (Λ, Φ, Δ) | τ | +lần gọi | TP | FP | R | F1 [CI95] | FPR |
|---|---|---:|---:|---:|---:|---:|---|---:|
| CTAV | | | 0 | 29 | 51 | 0,139 | 0,201 [0,138; 0,264] | 0,0069 |
| CTAV + C5 (chọn) | (0; 0,4; 0,6) | 0,8 | 52 | 31 | 67 | 0,148 | 0,202 [0,143; 0,261] | 0,0090 |

Δ (C5 − CTAV): F1 +0,001 [−0,014; +0,022]; Recall +0,010 [0,000; +0,025]; Precision −0,046 [−0,089; −0,010];
FPR +0,0022 [+0,0011; +0,0034]; McNemar p = 0,0013 (16 cửa sổ CTAV đúng / C5 sai, 2 ngược lại).

**Bảng 2. Đường τ** (η = (0; 0,4; 0,6)): recall phẳng 0,148 từ τ 0,3 đến 0,8 (chỉ 0,139 ở 0,9) trong khi số cửa
sổ được cứu giảm 1.286 → 52 và FPR giảm 0,0137 → 0,0090. Hạ τ chỉ thêm FP. Bảng đầy đủ: QĐ-033 Bảng M7-2.

**Phát hiện 12.** C5 không thêm được recall: cả lưới chỉ cứu tối đa 2 TP trên 100 fault detector bỏ sót. Nút
thắt ở judge (21 fault được đưa vào: 16 bị C1 trả lời FALSE_POSITIVE, 3 bị C3 hạ). Λ_log gần như luôn 0 (13
cửa sổ > 0) vì log lỗi của Nezha nằm ở pod không có cửa sổ (`frontend`).

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Quy tắc chọn giữ C5 chỉ vì ΔF1 +0,0013 (đổi 2 TP lấy 16 FP) | `eval/harness/rescue.py` `_select`; QĐ-033 | Theo chữ của quy tắc thì "giữ", theo ý nghĩa thống kê thì không đóng góp và FPR tệ hơn (V34) |
| 2 | A = cảnh báo CTAV, không lan truyền dây chuyền, cửa sổ hoạt động 300 s | `scripts/build_rescue_features.py`, `services/detector/rescue.py` | Thiết kế này agent tự chọn (spec không nói rõ A); lan truyền dây chuyền có thể cứu thêm nhưng cần gọi LLM theo vòng |
| 3 | Bản nháp đăng ký: ngưỡng δ = 0,05, tiêu chí từng H, danh sách config `test` | cuối `docs/experiment-log.md` | Không sửa được sau M8 |
| 4 | Runner chế độ `rescue.windows` (chỉ chấm cửa sổ trong danh sách) | `eval/harness/runner.py` `_rescue_windows` + nhánh rescue trong `run()` | Số lần gọi / chi phí M8 của C5 dựa vào đây |
| 5 | Đường dẫn kết quả lệch roadmap (`eval/results/...` thay vì `data/rescue_features.parquet`) | QĐ-033 | Chỉ là vị trí file, có snapshot config |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| V29 | GVHD chưa biết V28 (b), việc bỏ C2/C4 (QĐ-031), nay thêm kết quả C5 (QĐ-033) | Báo GVHD cùng lúc | Báo trước khi chốt đăng ký | **Đăng ký → M8** |
| V33 | δ trong vế "recall ≥ C1 − δ" của H2 | (a) δ = 0,05 cố định; (b) δ = ½ mức tăng recall của C1 so với BM25 đo trên `test`; (c) giá trị khác | (a) — chọn trước, không nhìn theo `val` (trên `val` CTAV cần δ ≥ 0,124 nên vế này dự kiến không đạt, đúng tinh thần V32 (a)) | Đăng ký |
| V34 | Vai trò C5 ở M8 | (a) theo quy tắc: phương pháp chính = CTAV + C5; (b) phương pháp chính = CTAV, C5 chỉ là ablation H3 (một điểm, không quét); (c) bỏ C5, không chạy trên `test` | (b) — ΔF1 không có ý nghĩa, FPR tệ hơn có ý nghĩa; vẫn đo trên `test` để luận văn có kết quả C5 (≈ 1 USD) | Đăng ký |
| V30 | Nguồn ngưỡng nền C3 (agent tự quyết ở M6) | | Bạn xác nhận | Không |
| V26 | Billing chưa đối chiếu | | Như cũ | Không |
| V27 | Phạm vi chấm `test` ở M8 | | Quyết định khi mở M8 | M8 |

## 4. Plan cho mốc tiếp theo

- Đóng M7: bạn báo GVHD (V29), chốt V33, V34 ⇒ agent sửa bản nháp thành "ĐÃ ĐĂNG KÝ", commit riêng.
- M8 (G-test): tạo config `test` theo danh sách đăng ký; chạy BM25, C1, không-RAG một lần; build anchor
  features `test`; replay CTAV + ablation; C5 theo V34; compare + McNemar. Ngân sách M8 17 USD (8 nếu V27
  "chỉ telemetry"), cộng ≈ 1 USD nếu chạy C5.
- Rủi ro: Phát hiện 11 (15 service không có ngưỡng `dev`) — nếu `test` nhiều service này thì CTAV mất recall.

## Phụ lục

- **Sai lệch so với plan:** vị trí file kết quả (QĐ-033); A định nghĩa là cảnh báo CTAV không lan truyền dây
  chuyền (agent tự chọn khi chạy tự động); +50% lần gọi đo so với CTAV chốt (5.677).
- **Nguyên liệu luận văn:** Bảng M7-1, M7-2 (QĐ-033); `eval/results/m7_rescue_val_v1/points.csv` (đủ 147
  điểm + "off"), `rescue.json` → `tau_curve`, `faces`, `face_pairs`, `comparison`.
- **Code:** `services/detector/rescue.py`, `scripts/build_rescue_features.py`, `eval/harness/rescue.py`,
  `py -m eval rescue`, `rescue.windows` trong runner; test `tests/test_rescue.py`.
- **Lệnh tái lập:** cuối QĐ-033.
