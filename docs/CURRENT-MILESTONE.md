# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Trạng thái — 2026-11-16

| Mốc | Trạng thái | Báo cáo / quyết định |
|---|---|---|
| M0 | QUA | `docs/milestones/M0-nen-tang.md` |
| M1 | QUA | `docs/milestones/M1-detector-bm25-judge.md`; QĐ-015..017 |
| M2 | QUA | `docs/milestones/M2-harness-gport.md`; QĐ-018, QĐ-019 |
| M3 | QUA (đóng 2026-10-19) | `docs/milestones/M3-graph-c1-gpaper.md`; QĐ-020, QĐ-021 |
| M4 | QUA (đóng 2026-10-29; GVHD đồng ý V24 (b)) | `docs/milestones/M4-h0.md`; QĐ-022..027 |
| M5 | QUA (đóng 2026-11-01; H1 giữ một phần, V28 (b)) | `docs/milestones/M5-h1.md`; QĐ-028, QĐ-029 |
| M6 | QUA (đóng 2026-11-11; H3 bỏ C2, C4; V30 (c), V31 (a), V32 (a)) | `docs/milestones/M6-ctav.md`; QĐ-030..032, QĐ-037 |
| M7 | QUA (đóng 2026-11-14; H0–H5 đã đăng ký, commit `be2b985`; V33 (a), V34 (b)) | `docs/milestones/M7-rescue-dang-ky.md`; QĐ-033, QĐ-034 |
| M8 | **QUA (đóng 2026-11-16; người dùng đã xem báo cáo, V36 (a) — QĐ-039; M8: xong phần API)** — hoàn tất 2026-11-16 (21.094 gọi mới, 0 lỗi, 15,85 USD theo token): **H0 đạt, H2 không đạt** (do 61% fault rơi vào 32 service thiếu ngưỡng `dev`; đối chứng `C3-trượt` đạt F1 0,120), **H3 & H4 đạt** | `docs/milestones/M8-g-test.md`; QĐ-034..039 |
| M9 | **Xong mọi việc 2026-11-17, chờ người dùng xem báo cáo (V46)** — M9-A `val` (2026-11-16) + M9-B `test` (2026-11-17): **H5 không được chấp nhận** (Hit@1 0,471; Hit@3 0,471; ΔHit@1 = 0; 0 lỗi cascade); 0,2772 USD theo token | `docs/milestones/M9-rca.md`; QĐ-037, QĐ-039..042 |

M8 tóm tắt (QĐ-038, QĐ-039): G-test trên `test` (11.985 cửa sổ telemetry, 346 fault), 21.094 lần gọi mới, 15,85 USD
theo token, 0 lỗi judge. **H0 chấp nhận** (C1 − BM25: ΔRecall +0,179, ΔFPR +0,0744). **H2 không được chấp nhận**:
CTAV 14 TP / 64 FP, F1 0,066 so với BM25 0,091 (ΔF1 −0,025 [−0,067; +0,014]); đạt vế FPR, không đạt vế F1 và vế
recall (−0,237). Nguyên nhân: 32 / 42 service (61,0% fault) không có ngưỡng `dev` p90 nên C3 hạ trọn 67 / 67 TP của
C1 ở đó (Phát hiện 11); ablation `c3_rolling_baseline` đạt 47 TP / 391 FP, F1 0,120 — chỉ là phân tích cơ chế.
**H3 đạt** (C3 đóng góp; xác nhận bỏ C2, C4; C5 +0 TP / +1 FP), **H4 đạt** (120 lần gọi: 0,034 so với 0,017).
V36 (a): H5 chính thức trên 78 cảnh báo `ctav_final_test_v1`, kèm dòng độ nhạy trên 438 cảnh báo C3-trượt.

M7 tóm tắt (QĐ-033): Rescue Score tính offline với A = cảnh báo CTAV; 147/147 tổ hợp khả thi, hợp 1.459 cửa
sổ chấm một lần (1,03 USD theo token). Quy tắc chọn η = (0; 0,4; 0,6), τ = 0,8 ⇒ công thức rút về 2 thành phần
(Λ_log không đóng góp); +2 TP / +16 FP, ΔF1 +0,001 [−0,014; +0,022], ΔFPR +0,0022 [+0,0011; +0,0034]
(Phát hiện 12: nút thắt ở judge, không ở cổng Rescue). H0–H5 **đã đăng ký 2026-11-14** ở cuối experiment-log
(QĐ-034): δ = 0,05; phương pháp chính = CTAV, C5 chỉ là một điểm ablation H3.

M6 tóm tắt (QĐ-031): CTAV đánh giá bằng replay verdict H0 đã cache (`py -m eval ctav`, 0 USD). H3 trên `val`
bỏ C4 (chạy C1 cho mọi candidate rẻ hơn và F1 cao hơn) và C2 (ΔFPR CI chạm 0). Cấu hình chốt
`eval/configs/ctav_final.yaml` = C1 + θ 0,80 + C3 (`dev` p90): F1 0,201 [0,138; 0,264] vs BM25 0,103,
FPR 0,007 vs 0,056, nhưng recall 0,139 < C1 0,263 (Phát hiện 10); 15 service không có ngưỡng `dev`
(Phát hiện 11; V31 (a): giữ cấu hình, C3-trượt là ablation bắt buộc ở M8 — QĐ-032).

M4 tóm tắt: H0 trên `val` tái lập **hiện tượng** (C1-paper − BM25: ΔRecall +0,100 [+0,052; +0,155],
ΔFPR +0,025 [+0,020; +0,031], McNemar có ý nghĩa; ΔF1 CI chứa 0) nhưng **không tái lập cơ chế**
(Phát hiện 7): C1-quota ≡ C1-paper; khác biệt do C1 chọn trace span sát t₀; mọi biến thể có judge F1
≈ detector-only. V24 → (b) đổi trục C2, C3, H1 sang độ gần thời gian / loại bằng chứng, giữ khung
CTAV (QĐ-027; GVHD đồng ý 2026-10-29).

M5 tóm tắt: H1 giữ một phần (QĐ-028). TRUE_ALERT tăng theo độ gần thời gian và cao hơn với trace, nhưng
chững lại từ 67% và tác động cả recall. Không chọn đặc trưng C2 từ H1; V28 (b): M6 chỉ quét θ trên verdict
đã cache, trọng tâm giảm FP sang C3 (QĐ-029).

---

## Mốc hiện tại: M9 — RCA Agent
## Mở 2026-11-16 (QĐ-039)

Chia hai phần theo QĐ-037 (prompt P2, P3 ở `docs/prompts/M8-M12-prompts.md`). **M9-A chỉ dùng `val`**; cấu hình RCA
chốt ở `eval/configs/rca_final.yaml` bằng commit riêng **trước** khi chạm `test`. **M9-B chạy `test` một lần** bằng
đúng file đó; sau khi thấy số `test` không sửa tham số, không chạy biến thể khác. M9 dùng QĐ-040..044, V40..V44.

### Việc

**M9-A — trên `val`** (đầu vào: 80 cảnh báo của `ctav_final_val_v1`: 29 TP, 51 FP; replay 0 USD)

1. - [x] Harness RCA `py -m eval rca --config ...`: đọc cảnh báo CTAV của một run, gom incident, định vị root cause,
   chấm Hit@1 / Hit@3 mức service theo nhãn root-cause (QĐ-001) có CI bootstrap; ghi `incidents` vào PostgreSQL (`03` §4)
2. - [x] Grouping (`services/rca_agent/grouping.py` đã có + `tests/test_grouping.py`): quét `T_group ∈ {180, 300, 600}` s;
   Alert Reduction Ratio chung và riêng trên incident cascade / `network_delay`; quy tắc chọn `T_group` (kể cả khi hoà)
   viết vào code trước khi xem số
3. - [x] `propagation.py` mức 1 (lan truyền ngược 1-hop thuần thuật toán) + baseline "service có anomaly score cao nhất
   trong incident"; báo cả hai kèm ΔHit@1 ghép cặp có CI
4. - [x] ~~`propagation.py` mức 2 (LLM full call chain)~~ — đã cắt theo `04` §9 ưu tiên 1 (QĐ-037); ghi vào QĐ và báo cáo M9
5. - [x] `summarizer.py`: JSON theo `03` §2, validator + `diagnostic_rejected`, `require_evidence`, chặn câu lệnh thực thi;
   test bằng backend `mock` trước, rồi đo JSON valid rate bằng Gemini thật (M8 đã xong phần API; ngân sách 1 USD, ngưỡng dừng 2 USD)
6. - [x] Chốt `eval/configs/rca_final.yaml` (`T_group`, quy tắc xếp hạng, prompt summarizer), commit riêng
7. - [x] Nháp `docs/milestones/M9-rca.md` (phần `val`) + `docs/drafts/ch5-rca-val.md` (bảng + đoạn văn cho §5.9, mô tả RCA cho Ch4)

Kết quả M9-A trên `val` (QĐ-041, `rca_final_val_v1`): `T_group` 180 s, mức 1 dấu hiệu `alert`; 80 cảnh báo → 26 incident
(11 có nhãn, 1 `ambiguous`, 14 không ứng với lỗi); Hit@1 = Hit@3 = 0,636 [0,364; 0,909] = baseline (ΔHit@1 0,000);
ARR 0,675 chung, **0,250 trên `network_delay` (DoD ≥ 0,30 không đạt)**; JSON valid rate 26 / 26. Chờ người dùng: V40, V44.

**M9-B — trên `test`** (điều kiện vào: `rca_final.yaml` đã commit; M8 QUA — đã đạt, QĐ-039)

8. - [x] `rca_final_test.yaml` = `rca_final.yaml` chỉ đổi `split` / run đầu vào / `run_id`; in diff, commit trước khi chạy
9. - [x] Chạy một lần trên **78 cảnh báo của `ctav_final_test_v1`** (14 TP, 64 FP) — **chỉ số chính thức của H5** theo bản đăng ký
   `be2b985`: Hit@1 ≥ 0,60; Hit@3 ≥ 0,80; cận dưới CI ΔHit@1 (RCA − baseline) > 0; Alert Reduction ≥ 30% trên incident cascade.
   Báo kèm số fault `test` không có cảnh báo CTAV nào, tách Hit@k "trên incident có cảnh báo" và "trên mọi lần tiêm lỗi"
10. - [x] **Dòng độ nhạy (V36 (a), QĐ-039):** cùng `rca_final.yaml`, không đổi tham số, trên 438 cảnh báo của ablation
    `c3_rolling_baseline` (47 TP, 391 FP); ghi nhãn "độ nhạy, ngoài bản đăng ký", không dùng cho kết luận H5
11. - [x] QĐ: H5 tính ở M9-B qua harness thay vì ở M10 (M10 phải tái lập đúng tập incident này); hoàn tất
    `docs/milestones/M9-rca.md` 4 phần; thêm §5.9 vào `docs/drafts/ch5-ket-qua-test.md`; chuyển file này sang M10

Kết quả M9-B trên `test` (QĐ-042, `rca_final_test_v1`, chạy một lần, dấu vân tay `b0c54fa68ef65535`): 78 cảnh báo ở 5
service → 38 incident (17 có nhãn, 3 `ambiguous`, 18 không ứng với lỗi; 0 incident nhiều service). **H5 không được chấp
nhận:** Hit@1 = Hit@3 = 8 / 17 = 0,471 [0,235; 0,706] = baseline; ΔHit@1 0,000 [0,000; 0,000]; ARR cascade không tính
được (0 / 50 lần tiêm lỗi là cascade); 29 / 50 lần tiêm lỗi không có cảnh báo CTAV nào. Độ nhạy (ngoài bản đăng ký, 438
cảnh báo): Hit@1 0,208 so với baseline 0,229; ARR cascade 0,704. JSON valid rate 38 / 38 và 114 / 114.
**Mục "chuyển file này sang M10" của việc 11 chưa làm:** đóng mốc cần người dùng xem báo cáo (`04` §2) — V46.

**DoD M9** (`04` M9, đo trên `val`): ARR ≥ 30% trên `network_delay`; có Hit@1 / Hit@3 mức 1 và baseline; JSON valid rate
≥ 0,95; **và** bảng kiểm định H5 trên `test` (lộ trình gộp M9-B, QĐ-037). Không đạt ngưỡng nào thì báo đúng con số, nêu
nguyên nhân từ dữ liệu, không nới định nghĩa chỉ số. Hạn 2027-01-03.

**Trước khi chạy:** bật Docker Desktop + `docker compose --profile dev up -d` (ghi PostgreSQL, `tests/test_storage.py`);
lúc mở mốc 2026-11-16 không có container nào đang chạy.

**Rủi ro đã biết:** mẫu nhỏ — 80 cảnh báo trên `val`, 78 trên `test` (chỉ ở 10 service có ngưỡng `dev`, khuyết 11 / 20
service có fault) ⇒ ít incident, CI của Hit@k rộng; dòng độ nhạy V36 (a) là đối sách, không thay chỉ số chính thức.

### Vấn đề cần chốt

| # | Vấn đề | Khuyến nghị | Chặn gì |
|---|---|---|---|
| ~~V26~~ | Billing chưa đối chiếu | Đóng (QĐ-034): người dùng báo billing đã reset, số dư ≈ 1.000.000 đ | |
| ~~V27~~ | Phạm vi chấm `test` | Người dùng chốt **toàn bộ candidate** 2026-11-14 (QĐ-034) | |
| ~~V29~~ | Báo GVHD V28 (b), bỏ C2/C4, kết quả C5 | Người dùng đã gửi 2026-11-14 (QĐ-034) và chốt tự giải quyết phần GVHD (QĐ-037); không chặn | |
| ~~V33~~ | δ của H2 | Người dùng chốt (a) δ = 0,05 (QĐ-034) | |
| ~~V34~~ | Vai trò C5 ở M8 | Người dùng chốt (b) chỉ ablation H3 một điểm (QĐ-034) | |
| ~~V30~~ | Nguồn ngưỡng nền cho C3 | Người dùng chốt (c) 2026-11-16 (QĐ-037): dựng cả hai, quy tắc chọn `dev` p90 (QĐ-031) ⇒ M6 **QUA** | |
| ~~V35~~ | Chấm context precision thủ công 50 cửa sổ (`04` M8) | Người dùng chốt (a) 2026-11-16 (QĐ-037): đã xuất `eval/manual/context_precision_test_v1.csv` (mù, 525 dòng) + hướng dẫn; người dùng chấm sau | Không chặn bảng H0–H4 / M9 |
| ~~V36~~ (chốt (a) 2026-11-16, QĐ-039) | Đầu vào cảnh báo cho H5 (RCA Agent) trên `test` ở M9-B: CTAV đóng băng chỉ phát 78 cảnh báo trên 10 service có ngưỡng `dev` (khuyết 11 service có fault) | Khuyến nghị **(a)** (báo cáo M8 §3): giữ chỉ số chính H5 trên 78 cảnh báo `ctav_final_test_v1` đúng cam kết `be2b985`, **kèm** dòng độ nhạy trên 438 cảnh báo của `c3_rolling_baseline` | Không chặn M9-A (`val`); chốt trước M9-B (`test`) |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | | Không |
| V4–V6 | File `legacy/` chưa commit; file rác gốc repo; câu "LLM không RAG thất bại" là số mock | | Không |

Các vấn đề V16–V24 đã chốt: xem báo cáo M4 §3 và QĐ-022..027. V28: báo cáo M5 §3 và QĐ-029.

---

## Ngân sách API (ghi 2026-10-29; số dư cập nhật 2026-11-14, QĐ-034)

**Credit còn lại (người dùng báo 2026-11-14, sau khi billing reset):** ≈ 1.000.000 đ ≈ **38 USD** (ước theo
≈ 26.000 đ/USD). Số 48 USD ghi 2026-10-29 không còn dùng. Đơn giá thực đo (QĐ-026, M5): ≈ 0,0014 USD / lần gọi theo token với prompt có 6 bằng chứng
(≈ 2.000 token vào / 310 ra); ≈ 0,0006 USD với prompt không bằng chứng; billing ≈ 1,14 × số theo token
(ngày 2026-10-28). Số dưới đây là **ước tính đã nhân 1,14, không phải số billing thật**: hệ số này chỉ
suy từ một lần đối chiếu, giá trong code và số dư credit chưa được đối chiếu (V26).

| Mốc | Phần tốn API | Ngân sách | Ngưỡng dừng |
|---|---|---|---|
| M5 (còn lại) | Xong: 753 lần gọi, 1,0093 USD **theo token** (billing thật chưa biết) | 1,5 USD | 3 USD |
| M6 | Xong: 0 lần gọi (replay cache H0, QĐ-031) | 2 USD | 4 USD — đổi prompt judge = lập lại ngân sách trước khi chạy |
| M7 | Xong phần Rescue: 1.459 lần gọi, 1,03 USD **theo token** (`m7_rescue_val_c1_v1`) | 4 USD | 6 USD |
| M8 | **Xong phần API** (`test` một lần, toàn bộ candidate — V27): **15,85 USD theo token** / 21.094 câu mới (`bm25` 8,87 + `c1_k0` 4,71 + `norag` 1,10 + `C5` 0,09 + `repeat` 1,08) | 18 USD | 20 USD (người dùng đã duyệt vượt ở QĐ-037) |
| M9 | **Xong: 178 lần gọi, 0,2772 USD theo token** (`val` 0,0436 / 26; `test` đăng ký 0,0495 / 38; độ nhạy 0,1841 / 114 — QĐ-041, QĐ-042) | 1 USD | 2 USD |
| M10–M12 | Demo offline từ cache; đánh giá bằng người | 0 | 1 USD |
| Dự phòng | Chạy lại do lỗi pipeline / đổi prompt | 8 USD | — |
| **Tổng còn phải chi (M9–M12 + dự phòng)** | | **≈ 9 USD** (riêng M9 ≈ 1 USD; người dùng báo ngày 2026-11-16 trước đợt chạy cuối còn ≈ 300k đ, đợt cuối chỉ tiêu thêm **1,29 USD theo token** ≈ 35–44k đ) | |

**Đã tiêu (ước tính theo token, không phải billing; không gồm request lỗi, retry, request bị ngắt):**
M4 ≈ 8,6 USD; M5 ≈ 9,48 USD / 6.988 lần gọi: 2026-10-29 ≈ 8,47 USD (`ref_flat` 1,77, `order_rev` 1,77,
`time_0/33/67` 0,80 / 0,75 / 0,76, `near_trace` 0,84, `near_log` 0,89, `neighbor_trace` 0,876 tính từ
`usage` trong cache), 2026-11-01 1,0093 USD (`neighbor_trace` 0,0016, `repeat` 1 0,5022, `repeat` 2 0,5056);
M7 ≈ 1,03 USD / 1.459 lần gọi; **M8 (hoàn tất 2026-11-16) = 15,8464 USD / 21.094 lần gọi mới trong cache**
(`h0_test_bm25_v1` 8,8715 / 13.699; `h0_test_c1_k0_v1` 4,7072 / 3.299; `h0_test_norag` `_v1 + _v2` 1,0976 / 3.287;
`m8_rescue_test_c1_v1` 0,0897 / 61; 4 run `repeat` 1,0804 / 748); **M9 (2026-11-16..17) = 0,2772 USD / 178 lần gọi**
(`rca_final_val_v1` 0,0436 / 26; `rca_final_test_v1` 0,0495 / 38; `rca_sens_test_c3rolling_v1` 0,1841 / 114; cache 40.429 dòng).

**Quy tắc (áp cho mọi mốc):**
1. Trước mỗi lần chạy có gọi API: ước số lần gọi mới (trừ phần trúng cache) × đơn giá theo **token của
   đúng loại prompt** — không dùng đơn giá của run khác loại (bài học QĐ-026).
2. Điều kiện / config mới: chạy thử một điều kiện trước, đọc `runtime.json` (`estimated_usd_by_tokens`),
   rồi mới chạy phần còn lại.
3. Một mốc chạm **ngưỡng dừng** ⇒ dừng, báo người dùng, không tự chạy tiếp.
4. Ghi chi phí thực của mỗi lần chạy vào experiment-log (QĐ của mốc) và cập nhật dòng "Đã tiêu" ở đây.
5. Người dùng đặt spend cap ở AI Studio ≈ 40 USD làm chốt chặn cuối.

---

## Ghi chú bàn giao — 2026-11-17 (M9-B xong, M9 chờ người dùng xem)

**Trạng thái:** người dùng cho chạy M9-B (V44 (a)). M9 xong mọi việc 1–11; báo cáo `docs/milestones/M9-rca.md` đủ 4
phần; §5.9 đã thêm vào `docs/drafts/ch5-ket-qua-test.md`; QĐ-042. **Chưa chuyển file này sang M10**: chờ người dùng xem
báo cáo M9 và chốt V46 (đóng M9), V45 (cách trình bày H5 không đạt).
**Commit:** `7ebe57a` (hai config `test`, trước khi chạy) → commit kết quả `test` + tài liệu. Chưa push.
`eval/configs/rca_final.yaml` không bị sửa sau `77786ec`; không có biến thể nào khác chạy trên `test`.
**Số `test` (con số đăng ký):** Hit@1 = Hit@3 = 8 / 17 = 0,471 [0,235; 0,706], bằng baseline; ΔHit@1 0,000; ARR cascade
không tính được (0 lỗi cascade); ARR chung 0,513 [0,362; 0,626]; JSON valid rate 38 / 38. **H5 không được chấp nhận.**
Độ nhạy (438 cảnh báo, ngoài bản đăng ký): Hit@1 0,208 / baseline 0,229; Hit@3 0,313; ARR cascade 0,704.
**Chi phí M9:** 178 lần gọi, 0,2772 USD theo token (ngân sách 1 USD).
**Kiểm:** 239 test qua (gồm `tests/test_storage.py` và test ghi PostgreSQL thật); `mypy packages services` sạch;
`ruff` chỉ còn E402 cũ ở `scripts/`. Chưa ai đọc nội dung các báo cáo chẩn đoán (M11); chưa đo E2E latency (M10).
**Việc đầu tiên phiên sau:** người dùng xem `docs/milestones/M9-rca.md` (mục 1B, §3), chốt V45, V46 ⇒ đóng M9, cập
nhật `04` §1, mở M10 (prompt P4). M10 phải tái lập đúng 38 incident của `rca_final_test_v1` (QĐ-042). Docker cần bật
(`docker compose --profile dev up -d`); PostgreSQL đang giữ 4 run RCA (2 `val`, 2 `test`).

## Ghi chú bàn giao — 2026-11-16 (M9-A xong, chờ M9-B)

**Trạng thái:** M9-A việc 1–7 xong (QĐ-040, QĐ-041; bản nháp `docs/milestones/M9-rca.md`, `docs/drafts/ch5-rca-val.md`).
Phiên này không đọc, không chạy, không tạo gì thuộc `test`. Commit: `e455004` (code + quy tắc chọn, trước số `val`) →
`77786ec` (**chỉ** `eval/configs/rca_final.yaml`) → commit kết quả + tài liệu. Chưa push.
**Cấu hình chốt (`rca_final.yaml`, dấu vân tay phương pháp `b0c54fa68ef65535`):** `T_group` 180 s; mức 1 với dấu hiệu
`alert`, đệm 60 s; cascade = lần tiêm lỗi có cảnh báo ở ≥ 2 service; summarizer `gemini-2.5-flash`, prompt
`rca-summary-v1` (`8c1d50e6ba757ee6`), `max_evidence` 12, `require_evidence`; bootstrap 1.000 mẫu, seed 42.
**Số `val`:** 80 cảnh báo → 26 incident (11 có nhãn, 1 `ambiguous`, 14 không ứng với lỗi); Hit@1 = Hit@3 = 7 / 11 = 0,636
[0,364; 0,909], **bằng baseline** (ΔHit@1 0,000 [0,000; 0,000]: 25 / 26 incident chỉ có một service); Hit@1 trên mọi
lần tiêm lỗi 6 / 30; ARR 0,675 [0,600; 0,730] chung, 0,667 cascade (1 lần tiêm lỗi), **0,250 [0,000; 0,500] trên
`network_delay` — DoD ≥ 0,30 không đạt** (chỉ 3 / 9 lần tiêm có cảnh báo, 4 cảnh báo → 3 incident là trần);
JSON valid rate 26 / 26 = 1,000. Chi phí 0,0436 USD theo token (26 lần gọi).
**Kiểm:** 239 test qua (gồm `tests/test_storage.py` và test ghi PostgreSQL thật — Docker đang bật); `mypy packages
services` sạch; `ruff` chỉ còn E402 cũ ở `scripts/`.
**Chưa làm / chưa kiểm:** mức 2 (cắt, QĐ-037); chưa có ai đọc nội dung 26 báo cáo (M11); `packages/storage/README.md`
vẫn ghi "PostgreSQL client chưa có" (ngoài vùng file P2 — code ghi nằm ở `services/rca_agent/store.py`, V42); chưa đo
E2E latency đúng nghĩa (M10; số 2,64 s / incident ở QĐ-041 chỉ là định vị + một lần gọi LLM).
**Chờ người dùng trước M9-B:** V40 (định nghĩa cascade ≥ 2 service), V44 (đồng ý sang M9-B dù DoD ARR `network_delay`
không đạt trên `val`); V41–V43 không chặn (báo cáo M9 §3).
**Việc đầu tiên phiên M9-B (prompt P3):** bật Docker; tạo `eval/configs/rca_final_test.yaml` = `rca_final.yaml` chỉ đổi
`split: test`, thêm `h5_test: true`, `input.alerts_run` / `input.evidence_run` sang run `test`, `run_id`; in diff, commit,
chạy một lần, kiểm harness in `method fingerprint b0c54fa68ef65535`. Dòng độ nhạy V36 (a): cùng tham số với
`input: {ctav_config: ..., variant: c3_rolling_baseline, evidence_run: ...}` và `run_id` riêng (đường này đã kiểm trên
`val`: 289 cảnh báo = TP + FP của `ctav.json`). Harness tự ước chi phí và dừng nếu vượt 1 USD.

## Ghi chú bàn giao — 2026-11-16 (đóng M8, mở M9)

**Trạng thái:** người dùng đã xem báo cáo M8 và chốt **V36 (a)** ⇒ M8 đóng, M9 mở (QĐ-039). Phiên này chỉ sửa tài
liệu (experiment-log, báo cáo M8, file này, `04` §1, `milestones/README.md`); chưa viết code M9, 0 lần gọi API.
Code RCA hiện có: `services/rca_agent/grouping.py` + `tests/test_grouping.py`; chưa có `propagation.py`,
`summarizer.py`, harness `eval/harness/rca*.py`, lệnh con `py -m eval rca`.
**Việc đầu tiên phiên sau:** bật Docker, chạy M9-A theo prompt P2 (`docs/prompts/M8-M12-prompts.md`; điều kiện
"M8 xong phần API" đã đạt nên summarizer được gọi Gemini thật, ngân sách 1 USD). Không chạm `test` trước khi
`eval/configs/rca_final.yaml` được commit riêng.
**Còn chờ người dùng:** V35 (chấm 525 dòng context precision, hạn trước M12); mail GVHD
`docs/drafts/2026-11-16-mail-gvhd-gtest.md` mới soạn, chưa ghi nhận đã gửi.

## Ghi chú bàn giao — hoàn tất M8 ngày 2026-11-16 (**M8: xong phần API**)

**Trạng thái:**
- **M8: xong phần API** (cache `data/llm_cache/gemini.jsonl` đạt 40.251 dòng = +1.179 dòng trong phiên này, **0 lỗi judge** ở tất cả các run). Phiên M9 đã được gỡ khóa hoàn toàn để gọi Gemini thật trong ngân sách M9 (1 USD).
- **Toàn bộ việc 1–10 của M8 đã xong (QĐ-038):** `h0_test_norag_v2` (370 gọi mới = 0,12 USD), 3 bản `_b120_v1` (0 USD, khớp 100% đường ngân sách), `ctav_final_test_v1` + `m8_finding11_{test,val}_v1` (0 USD), chuỗi C5 một điểm `m8_rescue_*_test_v1` (61 gọi mới = 0,09 USD; +0 TP, +1 FP), 4 run tuần tự `h0_test_{bm25,c1_k0}_rep{1,2}_v1` (748 gọi mới = 1,08 USD; đồng thuận 99,0% và 99,5%), `h0_test_compare_{bm25ref,c1ref}_v1` + `m8_test_tables_v1`, mẫu mù `eval/manual/context_precision_test_v1.csv` + hướng dẫn, hoàn tất `docs/drafts/ch5-ket-qua-test.md` (§5.7.1–§5.8.6), báo cáo `docs/milestones/M8-g-test.md` và mail GVHD `docs/drafts/2026-11-16-mail-gvhd-gtest.md`.
- **Chi phí phiên:** 1.179 câu mới = **1,2940 USD theo token** (≈ 35–44k đ trên số dư ≈ 300k đ của tháng). Tổng toàn mốc M8 = **15,8464 USD theo token** / 21.094 câu mới.
- **Việc đầu tiên phiên sau:** Người dùng xem báo cáo `docs/milestones/M8-g-test.md`, chốt **V36** (báo kèm dòng độ nhạy `c3_rolling_baseline` cho H5 ở M9-B hay không) ⇒ chính thức chuyển `CURRENT-MILESTONE.md` sang **M9 (RCA Agent: `grouping.py`, `propagation.py` mức 1, `summarizer.py`)**.

## Ghi chú bàn giao — kiểm kê 2026-11-16 (M8 đang làm)

**Trạng thái thực tế sau phiên 2026-11-14 (`da2bb91`..`4f736aa`, QĐ-037):**
- **Đã xong:** `h0_test_bm25_v1` (8,87 USD, `da2bb91`), `h0_test_c1_k0_v1` (3.299 gọi mới, 4,71 USD, `0c7689e`), `m8_anchor_features_test_v1` (90,9 s, 0 USD, `cb191d5`), bản nháp §5.7.1–5.7.3 ở `docs/drafts/ch5-ket-qua-test.md` (**H0 đạt cả 4 vế trên `test`**), và các dàn ý luận văn (`759fb2f`, `7198e2d`, `4f736aa`).
- **Đang dở:** `h0_test_norag_v1` bị ngắt lúc 16:18 ngày 2026-11-14; không còn tiến trình Python nào đang chạy. Thư mục `eval/results/h0_test_norag_v1/` đang rỗng (giữ nguyên, không ghi đè). Trong `data/llm_cache/gemini.jsonl` (39.072 dòng) đã lưu **2.917 / 3.287** câu mới của `norag` (0,97 USD theo token), chỉ còn **370 lần gọi API** (≈ 0,12 USD).
- **Chưa xong phần API** (phiên song song như M9-A vẫn phải dùng backend `mock` cho tới khi xong `norag_v2`, C5 một điểm và `repeat` ×4).
- **Quyết định người dùng chốt 2026-11-16 (QĐ-037):** V30 → (c) (M6 **QUA**); V35 → (a) (không chặn); V29 người dùng tự giải quyết; xác nhận 2 thiết kế Rescue M7/M8 ($A$ = cảnh báo CTAV không lan truyền dây chuyền, file `eval/results/m7_rescue_features_<split>_v1/rescue_features.parquet`); đồng ý 3 lựa chọn rút ngắn đường găng M8–M12 (chạy song song các làn, H5 tính ở M9-B + M10 parity, cắt `propagation` mức 2 / `ExperimentComparison` bảng tĩnh / M11 chấm tối thiểu 15/30 incident).
- **Ngân sách:** đã tiêu tại M8 **14,55 USD theo token**; phần gọi API còn lại ước **≈ 1,2–1,5 USD theo token** (tổng ≈ 15,8–16,0 USD theo token; người dùng đã duyệt chạy tiếp dù quy đổi billing có thể vượt ngưỡng dừng 20 USD).
- **Thứ tự chạy tiếp phiên sau (theo `P1b` trong `docs/prompts/M8-M12-prompts.md`):**
  1. Đổi `run_id` trong `eval/configs/h0_test_norag.yaml` sang `h0_test_norag_v2` → `py -m eval run --config eval/configs/h0_test_norag.yaml` (chỉ hỏi nốt 370 câu, giữ nguyên `_v1` rỗng).
  2. `py -m eval ctav --config eval/configs/ctav_final_test.yaml` + `py scripts/m8_finding11.py` (0 USD) + ba bản `h0_test_{bm25,c1_k0,norag}_b120.yaml` (0 USD, 100% cache sau `norag_v2`).
  3. C5 một điểm (`m8_rescue_features_test.yaml`, `m8_rescue_plan_test.yaml`, `m8_rescue_test_c1.yaml`, `m8_anchor_features_rescue_test.yaml`, `m8_rescue_test.yaml`).
  4. `repeat` ×4 (`h0_test_{bm25,c1_k0}_rep{1,2}.yaml`) → ghi dòng `"M8: xong phần API"` vào đây.
  5. `py -m eval compare` + `py scripts/m8_tables.py` + `py scripts/m8_context_precision_sample.py` → hoàn tất `docs/drafts/ch5-ket-qua-test.md`, viết `docs/milestones/M8-g-test.md` và `docs/drafts/<ngày>-mail-gvhd-gtest.md`.

## Ghi chú bàn giao — phiên 2026-11-14 (đóng M7, mở M8)

**Trạng thái:** người dùng báo đã gửi GVHD (V29), chốt V33 (a), V34 (b), V27 toàn bộ, V26 đóng (QĐ-034). Mục
đăng ký H0–H5 commit riêng `be2b985` trước mọi lệnh chạm `test`. M7 đóng, M8 mở.
**Việc đang làm:** M8 việc 1–3 (xem danh sách trên).
**Cập nhật 15:45:** BM25 xong (8,87 USD theo token). `h0_test_c1_k0_v1` đang chạy (tiến trình sống sót qua lần phiên bị ngắt 15:40 —
không chạy lại). Chuỗi nền 1: chờ C1 → `h0_test_norag` → `m8_anchor_features_test` → `ctav_final_test` → `m8_finding11_test_v1` →
`h0_test_compare_v1`, `h0_test_compare_c1ref_v1` → `m8_test_tables_v1`. Chuỗi 2 (chạy sau chuỗi 1): C5 một điểm → `repeat` ×4 →
`m8_test_tables_v2` → mẫu context precision → ba bản `_b120`. **Chưa xong phần API** (phiên khác vẫn dùng backend `mock`).
**Ngân sách:** người dùng báo đã tốn ≈ 300.000 đ sau BM25 (≈ 28.000–33.800 đ cho mỗi USD theo token, tùy thời điểm đọc); dự phóng cả
M8 440–570 nghìn đ, có thể vượt ngưỡng dừng 20 USD (≈ 520 nghìn đ). **Người dùng đồng ý chạy tiếp `repeat` và C5 dù vượt ngưỡng**
(2026-11-14, ghi lại ở QĐ-037 cùng kết quả).

## Ghi chú bàn giao — phiên 2026-11-11 (tiếp, M7)

**Trạng thái:** M7 việc 1–2 xong (QĐ-033, báo cáo `docs/milestones/M7-rescue-dang-ky.md`); bản nháp đăng ký
H0–H5 cuối experiment-log, commit riêng. 1,03 USD theo token. Test, mypy sạch; ruff chỉ còn E402 cũ ở `scripts/`.
**Việc đầu tiên phiên sau:** người dùng báo GVHD (V29), chốt V33, V34 ⇒ sửa bản nháp thành "ĐÃ ĐĂNG KÝ",
commit riêng, đóng M7, mở M8. Không chạm `test` trước đó.

## Ghi chú bàn giao — phiên 2026-11-11

**Trạng thái:** người dùng chốt V31 (a), V32 (a) (QĐ-032) ⇒ đóng M6, mở M7. V30 chờ xác nhận (không chặn).
**Việc đầu tiên phiên sau:** M7 việc 1–2 (Rescue, không cần chờ GVHD). Đăng ký giả thuyết (việc 3) chờ V29.

## Ghi chú bàn giao — phiên 2026-11-01 (tiếp, M6)

**Trạng thái:** M6 xong mọi việc (QĐ-031, báo cáo `docs/milestones/M6-ctav.md`), chờ người dùng xem. Chạy tự
động nên V30 do agent tự quyết. 0 USD. Test: 179 pass; mypy sạch; ruff chỉ còn E402 cũ ở `scripts/`.
**Việc đầu tiên phiên sau:** người dùng xác nhận V30, chốt V31, V32, báo GVHD (V29) ⇒ mở M7.

## Ghi chú bàn giao — phiên 2026-11-01

**Trạng thái:** M5 đóng (QĐ-028, QĐ-029, `h1_val_analysis_v2`): H1 giữ một phần, V28 (b). M6 đã mở,
M6 việc 1 dừng ở QĐ-030: baseline `dev` phủ ≈ 32% span trên `val`, chờ V30. Đính chính M4 (JSON bị cắt
1/5.677) đã ghi ở QĐ-028.
**Việc đầu tiên phiên sau:** hỏi V30, kết quả báo GVHD (V29) và số billing cho V26. Không làm M6 việc 2
trước khi có V30.

## Ghi chú bàn giao — phiên 2026-10-29

**Trạng thái:** V24 chốt (b), GVHD đồng ý ⇒ M4 QUA; M5 mở. Code H1 (`eval/harness/h1.py`,
`scripts/h1.py`, `tests/test_h1.py`, `eval/configs/h1_val.yaml`), mẫu `eval/samples/h1_val_v1.json.gz`
và 8 run `eval/results/h1_val_*` **chưa commit**. Người dùng bảo dừng giữa lúc chạy `neighbor_trace`.
Sơ bộ: `ref_flat` − `ref` trên normal +0,020 [+0,001; +0,042], McNemar p = 0,06 (điểm hiển thị gần như
không đổi hành vi judge). Cần sửa ghi chép M4: lỗi duy nhất ở `h0_val_c1_k0_v1` là **JSON bị cắt
(1/5.677)**, không phải lỗi mạng; V21 (a) vẫn đủ.
**Việc đầu tiên phiên sau:** hỏi người dùng có chạy tiếp không; nếu có: `neighbor_trace` →
`repeat` 1, 2 (`--subset 200`) → `py scripts/h1.py analyze` → báo cáo M5, QĐ-028, commit.

## Ghi chú bàn giao — phiên 2026-10-28

**Trạng thái:** M4 xong mọi việc, chờ **V24** để đóng. H0 chạy xong (9 run + 2 compare + `h0_val_evidence_diff_v1`); nháp chương `docs/drafts/chuong-bai-toan.md`.
**Commit:** `1b04c88` (ghi chú bàn giao 10-20). Kết quả H0, sửa retry, script `h0_evidence_diff.py`, nháp chương: xem `git log` (chưa push).
**Sự cố:** `h0_val_bm25_v2` sập do `TimeoutError` khi đọc response không được retry ⇒ sửa `_post_json_with_retry` (bắt `OSError` + `HTTPException`), test mới; BM25 chạy lại `_v3`. Thư mục `_v1`, `_v2` rỗng, để nguyên.
Test: 150 pass. Chi phí phiên: ≈ 4,4 USD theo token (4.808 lần gọi), billing người dùng báo 5 USD / ≈ 8k request — chưa đối chiếu (QĐ-026); M4 ≈ 8,6 USD theo token. Cache Gemini 10.710 entry (không commit — giữ file).
**Việc đầu tiên phiên sau:** người dùng chốt V24 (báo cáo M4 §3); nếu (b) ⇒ QĐ-027, sửa `08` §2/§4/§5 + mô tả M5–M6 trong `04`, cập nhật mục 5–6 nháp chương, đóng M4.

## Ghi chú bàn giao — phiên 2026-10-20

**Trạng thái:** M4 đã mở; nháp báo cáo `docs/milestones/M4-h0.md`. V16 (b) và V17 (a) đã cài, test, đo (QĐ-022, kèm bảng phương án dự
phòng). V19, V20 đã chốt (QĐ-023); V18 đã chốt (a): `k_graph = 1` (QĐ-024, `m4_kgraph_val_k*_v1`); ablation α/β/γ xong (QĐ-025); code H0 xong (QĐ-026), run H0 đang chờ V23. Docker `--profile dev` cần chạy cho `tests/test_storage.py`.
**Commit:** `20fe298` (M4 tới V18, QĐ-022..024) · `4695008` (ghi hash) · `59012f4` (ablation, QĐ-025) · `a351ca5` (chuẩn bị H0, QĐ-026). Chưa push.
Test: 148 pass (gồm `test_compare`, `test_fusion_ablation`, `test_storage`, `test_window_index`, `test_kgraph_select`).
Chi phí API phiên 2026-10-20 ≈ 4,2 USD: ≈ 1,2 USD trước H0 (probe 5 lần, smoke 3.8 ≈ 0,315, 3.6 ≈ 0,33, V20: 2.5 ≈ 0,23, 3.8 ≈ 0,33) + ≈ 3,0 USD cho `h0_val_bm25_v1` (4.722 lần gọi, dừng vì spend cap); quét V18 và ablation dùng judge mock / không gọi LLM (0 USD).
Cache Gemini `data/llm_cache/gemini.jsonl`: 5.903 entry (không commit — giữ file này, H0 chạy tiếp từ đây).
**Việc đầu tiên phiên sau:** kiểm tra API hết 429 (spend cap đúng project của `GEMINI_API_KEY`), rồi chạy H0 theo "Lệnh tái lập M4" bên dưới.
Config mới: `m4_c1_vec_smoke.yaml` (V17, judge mock), `m4_judge_g36_smoke.yaml`,
`m4_judge_g38_smoke.yaml`, `m4_v20_g25_smoke.yaml`, `m4_v20_g38_smoke.yaml`, `m4_kgraph_val_k{0..3}.yaml` (V18, judge mock). Đo retrieval: `py scripts/retrieval_bench.py run --config ... --name ... --set k_graph=1`.
Chọn k: `scripts/kgraph_select.py` + `eval/harness/kgraph.py`.
Ablation α/β/γ (QĐ-025, 0 USD): `scripts/fusion_ablation.py` + `eval/harness/fusion_ablation.py`, config `m4_fusion_ablation_val.yaml` (lưới bước 0,25 — tôi chọn, chưa hỏi), kết quả `eval/results/m4_fusion_ablation_val_v1/`. C1 tách `build_pool`/`top_events`/`reweighted` (refactor thuần, có test).
H0 (QĐ-026): retrieval `none` (`services/retrieval/no_retrieval.py`), `py -m eval compare` (`eval/harness/compare.py`), 9 config `eval/configs/h0_val_*.yaml`. `h0_val_bm25_v1/` (spend cap) và `_v2/` (timeout, 2026-10-28) là thư mục rỗng do run dừng — để nguyên (không ghi đè), run tiếp là `_v3`.

## Ghi chú bàn giao — dừng phiên 2026-10-19

**Trạng thái:** M0–M3 đã đóng; M4 chưa mở. Phiên kế tiếp bắt đầu bằng việc người dùng chốt
**V16** (C1-quota hay giữ đúng paper) và **V17** (tăng tốc C1) — xem bảng trên và
`docs/milestones/M3-graph-c1-gpaper.md` §3. Không viết code M4 trước khi có hai quyết định này.

**Commit của phiên 2026-10-19** (theo thứ tự): `7dbb07f` M1 việc 2–5 (QĐ-016) · `48b2284`,
`b3d1761`, `a688a8a` M2 (QĐ-017, QĐ-018) · `cc3a595` judge song song (QĐ-019) · `aa859f0`
khảo sát M3 (QĐ-020) · `5595e61` M3 (QĐ-021) · commit bàn giao này.

**Báo cáo cột mốc cần đọc:** `docs/milestones/M1-detector-bm25-judge.md`,
`M2-harness-gport.md`, `M3-graph-c1-gpaper.md`.

**Bốn phát hiện quan trọng cho luận văn** (đã ghi trong experiment-log):
1. QĐ-016/017 — Nezha chỉ có log/trace quanh lần tiêm lỗi (100% fault, ~25% normal có); kho
   bằng chứng của paper còn lọc theo nhãn ⇒ chỉ số chính GĐ2 tính trên cửa sổ có telemetry.
2. QĐ-020 — 80% bằng chứng topology của paper lệch thời gian > 8 phút; 100% normal có bằng chứng.
3. QĐ-021 — C1 đúng paper trên dữ liệu đầy đủ chọn 0 bằng chứng lân cận (V16).
4. QĐ-016/019/021 — Gemini chép `anomaly_score` làm confidence khi thiếu bằng chứng (83% ở
   paper); `gemini-2.5-flash` trên prompt GĐ2 chỉ 1/196.

**Ghi nhớ kỹ thuật:**
- Judge GĐ2 = `gemini-2.5-flash` (`JUDGE_MODEL`); flash-lite chỉ cho G-paper (`PAPER_MODEL`).
  Run dừng nếu `modelVersion` lệch (một số id 3.x bị API chuyển ngầm).
- Harness: `py -m eval run --config X`; judge song song 8 worker, 200 lần gọi/phút (Tier 1).
  Lỗi judge ⇒ `runtime.json.judge_errors`; chạy lại với run_id mới chỉ hỏi lại câu lỗi.
- Cache Gemini GĐ2: `data/llm_cache/gemini.jsonl` (397 entry, không commit — giữ file này).
  Dump GĐ1: `data/gd1_parity/` (tạo lại bằng `scripts/dump_gd1_prompts.py`).
- Chi phí API của phiên: ≈ 0,30 USD (smoke M1 5 lần, thử model 5 lần, smoke flash-lite 196 lần
  ≈ 0,056, smoke flash 197 lần ≈ 0,23).
- Docker `clickhouse`, `postgres` đang chạy; volume mới cần `py scripts/apply_clickhouse_migrations.py`.
- Khi sửa file bằng script: heredoc `py - <<'EOF'` làm hỏng chuỗi chứa ký tự xuống dòng thoát (backslash-n) — viết script ra file riêng rồi chạy.
- V17 gợi ý: nút thắt là BM25 thuần Python trên pool trung vị ~147 nghìn event/truy vấn.

---

## Lệnh tái lập M4 (tới nay)

```bash
py -m eval run --config eval/configs/m4_c1_vec_smoke.yaml          # V17, run_id mới
py -m eval run --config eval/configs/m4_v20_g25_smoke.yaml         # V20, cần GEMINI_API_KEY
py -m eval run --config eval/configs/m4_kgraph_val_k0.yaml         # V18: k0..k3, ~8 phút/run
py scripts/kgraph_select.py --runs 0=m4_kgraph_val_k0_v1,1=m4_kgraph_val_k1_v1,2=m4_kgraph_val_k2_v1,3=m4_kgraph_val_k3_v1 --out <file-mới>.json
py scripts/fusion_ablation.py --config eval/configs/m4_fusion_ablation_val.yaml  # QĐ-025, đổi run_id; ~9 phút

# H0 (QĐ-026) — cần GEMINI_API_KEY, chạy đúng thứ tự (các run sau dùng lại cache của run trước)
py -m eval run --config eval/configs/h0_val_bm25.yaml          # _v3 (v1: spend cap, v2: timeout — cả hai thư mục rỗng)
py -m eval run --config eval/configs/h0_val_c1_k0.yaml
py -m eval run --config eval/configs/h0_val_c1_k1.yaml
py -m eval run --config eval/configs/h0_val_norag.yaml         # require_evidence: false
py -m eval run --config eval/configs/h0_val_norag_reqev.yaml   # 100% cache
py -m eval run --config eval/configs/h0_val_bm25_b120.yaml     # + c1_k0/c1_k1/norag _b120, 100% cache
py -m eval compare --runs bm25=h0_val_bm25_v3,c1_k0=h0_val_c1_k0_v1,c1_k1=h0_val_c1_k1_v1,norag=h0_val_norag_v1 --detector-only h0_val_bm25_v3 --out h0_val_compare_v1
py -m eval compare --runs c1_k0=h0_val_c1_k0_v1,c1_k1=h0_val_c1_k1_v1 --out h0_val_compare_k1_vs_k0_v1
py scripts/h0_evidence_diff.py --a h0_val_bm25_v3 --b h0_val_c1_k0_v1 --out h0_val_evidence_diff_v1   # Phát hiện 7
```

## Lệnh tái lập M3

```bash
py scripts/build_service_graph.py
py scripts/dump_gd1_prompts.py --variant topology_aware_fusion_top6
py scripts/check_gd1_parity.py --variant hybrid_bm25_top6
py scripts/check_gd1_parity.py --variant topology_aware_fusion_top6
py -m eval run --config eval/configs/m3_c1_window_smoke.yaml       # run_id mới
```

## Lệnh tái lập M0

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
py scripts/verify_labels.py             # -> docs/label-audit.md (~80 s)
py scripts/make_splits.py --check       # xác nhận split không đổi
docker compose --profile dev up -d      # clickhouse + postgres
py -m pytest tests/ -q                  # 115 test (sau QĐ-021)
py scripts/replay_smoke.py --windows 50 --run-id <run_id-mới>   # fit + replay + ghi ClickHouse
```

## Lệnh tái lập M2

```bash
py scripts/map_gd1_windows.py
py scripts/dump_gd1_prompts.py --split phase4 --max-total-calls 40
py -m eval run --config eval/configs/gd1_phase4_parity.yaml      # run_id mới nếu đã có
py scripts/gport_layers.py --run gd1_phase4_parity_v1
py -m eval run --config eval/configs/val_detector_count.yaml     # ~5 phút
```

## Lệnh tái lập M1

```bash
py scripts/apply_clickhouse_migrations.py                # cột CTAV (idempotent)
py scripts/dump_gd1_prompts.py                           # 489 prompt GĐ1 paper_500, ~85 s
py scripts/check_gd1_parity.py                           # port GĐ2 vs GĐ1: 489/489
py scripts/evidence_coverage.py                          # bằng chứng theo nhãn: GĐ1 vs GĐ2
py scripts/judge_smoke.py --run-id <mới> --candidates 3  # BM25 -> judge mock + Gemini
```
