# M6 — CTAV: C2 + C3 + C4, chốt cấu hình

| | |
|---|---|
| Ngày đóng mốc | 2026-11-11 (việc xong 2026-11-01; V31 (a), V32 (a) chốt 2026-11-11 — QĐ-032) |
| Hạn mục tiêu | 2026-12-06 (sớm 35 ngày) |
| Kết luận | **QUA** — DoD đạt; V30 (c) xác nhận 2026-11-16 (QĐ-037); V31 (a), V32 (a) người dùng chốt 2026-11-11 (QĐ-032) |
| Commit | xem `git log` (commit "M6: CTAV ...") |
| Quyết định liên quan | QĐ-029, QĐ-030, **QĐ-031**, QĐ-032, QĐ-037 |

## 1. Kết quả hiện tại

| DoD / việc | Đạt? | Bằng chứng |
|---|---|---|
| 1. Ngưỡng nền `duration_ms` (C3) | Có | `RollingSpanBaseline` + baseline `dev`; `eval/results/m6_anchor_features_val_v1/` (phủ trượt 93%, `dev` 32%) |
| 2. `services/judge/policy.py` (C2 + C3) + unit test | Có | `tests/test_policy_routing.py` |
| 3. Quét θ, chọn trên `val`, 0 lần gọi LLM | Có | Bảng M6-4; `m6_ctav_select_val_v1`, `_v2` |
| 4. `services/judge/routing.py` (C4) + unit test | Có | `tests/test_policy_routing.py`, `tests/test_ctav.py` |
| 5. Quét ngân sách (H4) | Có | Bảng M6-7; `ctav_final_val_v1/ctav.json` → `budget_curve` |
| 6. Ablation H3 có CI | Có | Bảng M6-3, M6-5 |
| 7. `rca_agent/grouping.py` bản khởi động | Có | `services/rca_agent/grouping.py`, model `Incident`, `tests/test_grouping.py` |
| `eval/configs/ctav_final.yaml` chốt | Có | `ctav_final_val_v1` |
| θ chọn ghi experiment-log | Có | QĐ-031 |

**Cách đánh giá.** CTAV là hàm thuần của câu trả lời judge, nên `py -m eval ctav` replay hai run H0 đã chấm mọi
candidate (tầng 1 BM25, tầng 2 C1). Replay khớp hai run gốc 0 lệch khi tắt C2/C3; mô phỏng ngân sách 120 khớp ba
run `_b120` 0 lệch. **0 lần gọi LLM, 0 USD.**

**Diễn biến chọn cấu hình** (quy tắc ghi trước: F1 cao nhất trên `val` telemetry; hòa ⇒ ít lần gọi ⇒ FPR thấp):
1. Bước 1 (hai tầng, baseline trượt): chọn θ_topo 0,90 → ablation: **bỏ C4 tốt hơn** (ΔF1 +0,036 [+0,022; +0,049],
   rẻ hơn 1,6 USD) ⇒ theo H3 bỏ C4 (Phát hiện 9: TRUE_ALERT tầng 1 ở θ_local 0,80 sinh 261 FP / 15 TP).
2. Bước 2 (C1 mọi candidate, baseline là một chiều lưới): chọn `dev` p90, θ_topo 0,85 → bỏ C2 chỉ thêm 2 FP,
   ΔFPR CI [+0,0000; +0,0007] ⇒ theo QĐ-029 bỏ C2.
3. Chốt: **C1 cho mọi candidate → judge → θ 0,80 → C3 (`dev` p90)**.

**Bảng 1. H3 trên `val` tại cấu hình chốt** (7.636 cửa sổ có telemetry, 209 fault; Δ = biến thể − CTAV).

| Biến thể | TP | FP | P | R | F1 [CI95] | FPR | USD | ΔF1 [CI95] |
|---|---:|---:|---:|---:|---|---:|---:|---|
| **CTAV** | 29 | 51 | 0,363 | 0,139 | **0,201 [0,138; 0,264]** | 0,0069 | 3,28 | |
| + C2 | 29 | 49 | 0,372 | 0,139 | 0,202 | 0,0066 | 3,28 | +0,001 |
| bỏ C3 (= C1) | 55 | 606 | 0,083 | 0,263 | 0,126 | 0,0816 | 3,28 | −0,074 [−0,124; −0,027] |
| + C4 | 31 | 90 | 0,256 | 0,148 | 0,188 | 0,0121 | 5,14 | −0,013 [−0,030; +0,008] |
| C3 baseline trượt | 34 | 255 | 0,118 | 0,163 | 0,137 | 0,0343 | 3,28 | −0,064 [−0,109; −0,022] |

**Bảng 2. So với baseline (H2 sơ bộ, `val`).**

| | F1 [CI95] | Recall | FPR | CTAV − X: ΔF1 [CI95] |
|---|---|---:|---:|---|
| BM25 | 0,103 [0,072; 0,133] | 0,163 | 0,056 | +0,098 [+0,046; +0,149] |
| C1 | 0,126 [0,095; 0,156] | 0,263 | 0,082 | +0,074 [+0,027; +0,124] |
| LLM không RAG | 0,092 [0,056; 0,134] | 0,086 | 0,022 | +0,109 [+0,051; +0,174] |
| Detector-only | 0,111 [0,094; 0,131] | 0,522 | 0,221 | |

**H4 (`val`):** ở 120 lần gọi CTAV F1 0,028 (3 TP / 0 FP) ≥ không-RAG 0,000; trội BM25 / C1 / không-RAG ở mọi
mức ngân sách (ước lượng điểm). Bảng M6-7 trong QĐ-031.

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Phương pháp đổi hình: CTAV chốt **không còn C2, C4** — chỉ còn C1 + C3 | QĐ-031, `08` §4, `eval/configs/ctav_final.yaml` | Đổi luận điểm của luận văn (tên "Calibrated", "two-tier"); cần GVHD biết (như V29) |
| 2 | Recall CTAV 0,139 < C1 0,263 (Phát hiện 10) — CTAV giảm FP chứ không giữ recall topology | QĐ-031 Bảng M6-6 | Mâu thuẫn mục tiêu (A) trong `AGENTS.md` / `06`: "giữ mức tăng recall của topology" |
| 3 | Ngưỡng `dev` thắng một phần vì 15 service không thể neo (Phát hiện 11) | QĐ-031; `m6_anchor_features_val_v1` | Số trên `test` có thể đổi mạnh nếu phân bố service khác |
| 4 | Lần nhìn `val` thứ hai (bước 2) và chiều "baseline" thêm vào lưới sau khi thấy bước 1 | `m6_ctav_select_val_v2.yaml` (chú thích đầu file) | Số `val` của cấu hình chốt lạc quan; chỉ `test` không thiên lệch |
| 5 | Logic replay (đặc biệt cộng token / lần gọi theo tầng, ngân sách) | `eval/harness/ctav.py` `Replay.run`; `tests/test_ctav.py` | Mọi số H3/H4 dựa vào đây; đã kiểm khớp run gốc nhưng chỉ khi tắt C2/C3 |
| 6 | Escalation `weak_fp` là mở rộng của C4 so với `08` (gốc: chỉ UNCERTAIN / không bằng chứng) | `services/judge/routing.py` docstring | Thiết kế thêm dựa trên số `val`; C4 đã bị bỏ nên tác động chỉ ở ablation |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| ~~V30~~ | Nguồn ngưỡng nền C3 (agent tự quyết khi chạy tự động) | (a) trượt 60 phút; (b) `dev`; (c) để quy tắc chọn | **Đã chốt (c) 2026-11-16 (QĐ-037)**: dựng cả hai, quy tắc chọn `dev` p90 (giữ trượt 60 phút làm ablation ở M8) | Không |
| V31 | Chấp nhận cấu hình chốt dù `dev` không phủ 15 service (Phát hiện 11)? | (a) giữ `ctav_final.yaml` như quy tắc chọn; (b) dùng baseline trượt (F1 0,137, vẫn > BM25, phủ 93%); (c) M7 thêm biến thể "`dev`, thiếu thì trượt" — cần thêm một lần nhìn `val` | (a) và đăng ký (b) làm ablation bắt buộc ở M8 để đo rủi ro | **M7** (đăng ký giả thuyết) |
| V32 | Viết lại H2 / mục tiêu (A) theo Phát hiện 10? | (a) giữ H2 nguyên văn, M8 báo trung thực "vế recall không đạt"; (b) M7 đăng ký lại H2 thành "FPR giảm, F1 tăng, recall không thấp hơn BM25 quá δ" | (a) — đổi giả thuyết sau khi thấy `val` là tối ưu theo dữ liệu | M7 |
| V29 | GVHD chưa biết V28 (b), nay thêm việc bỏ C2/C4 | Báo GVHD cùng lúc | Báo trước khi đăng ký M7 | M7 |
| V26 | Billing chưa đối chiếu | | Như cũ | Không |
| V27 | Phạm vi chấm `test` ở M8 | Với cấu hình chốt, CTAV trên `test` chỉ cần run C1 (+ BM25, không-RAG cho so sánh) | Quyết định khi mở M8 | M8 |

## 4. Plan cho mốc tiếp theo (M7 — Rescue Score + đăng ký giả thuyết)

- Việc: (1) chốt V31, V32, báo GVHD (V29); (2) tính trước `Λ_log`, `Φ_topo`, `Δ_time`; quét 147 tổ hợp Rescue
  (η1, η2, η3, τ); chỉ chấm cửa sổ được "cứu" (≈ 4 USD) — với cấu hình chốt, chấm bằng prompt C1;
  (3) đăng ký H0–H5 với ngưỡng định lượng và danh sách config chạy trên `test` (gồm ablation C2/C3/C4 và C3
  baseline trượt), commit riêng.
- Chuẩn bị M8: `scripts/build_anchor_features.py` cần config `test` (run C1/BM25 của `test` chưa có); ngưỡng
  `dev` đã cố định.
- DoD M7: giả thuyết đã commit trước khi chạy bất kỳ thứ gì trên `test`.
- Rủi ro: Rescue thêm candidate nhưng C3 có thể chặn gần hết nếu service không có ngưỡng `dev`.

## Phụ lục

- **Sai lệch so với plan:** V30 tự quyết (chế độ tự chạy); thêm `weak_fp` vào C4; thêm bước chọn lại thứ hai
  trên `val` sau khi H3 bỏ C4. Tất cả ghi ở QĐ-031.
- **Nguyên liệu luận văn:** Bảng M6-3..M6-7 (QĐ-031); `ctav.json` của ba run chứa đủ điểm lưới (đường θ cho
  cả hai chế độ, cả hai baseline), ablation, McNemar, đường ngân sách có CI.
- **Lệnh tái lập:** cuối QĐ-031.
