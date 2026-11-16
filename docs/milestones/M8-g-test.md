# M8 — Cổng chặn G-test (chạy `test` một lần)

| | |
|---|---|
| Ngày hoàn tất thực nghiệm | 2026-11-16 (mở 2026-11-14 sau commit đăng ký `be2b985`) |
| Hạn mục tiêu | 2026-12-20 (sớm 34 ngày) |
| Kết luận | **QUA** (chờ người dùng xem báo cáo theo `04` §2; phần API hoàn tất 100%, 0 lỗi judge) |
| Commit | `be2b985` (đăng ký H0–H5) → `da2bb91`, `0c7689e`, `cb191d5` (nửa đầu M8) → commit M8 hoàn tất |
| Quyết định liên quan | QĐ-034, QĐ-035, QĐ-036, QĐ-037, **QĐ-038** |

## 1. Kết quả hiện tại

| Việc / DoD | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|
| 1. Tạo config `test` #1–#8 sao từ `val`, không chỉnh tham số | Có | `eval/configs/h0_test_*.yaml`, `ctav_final_test.yaml`, `m8_*_test*.yaml` (`30f3f92`, `e6a71cb`, `48ee7f5`) |
| 2. Đếm candidate `test` và phân tích độ lệch detector (0 LLM) | Có | 46.849 cửa sổ, 13.699 candidate (29,2%); `eval/results/m8_test_detector_count_v1/`, `m8_detector_shift_test_v1/` (QĐ-035, QĐ-036) |
| 3–4. Chạy BM25, C1, LLM-không-RAG (toàn bộ candidate, V27) + 3 bản `_b120` | Có | `h0_test_bm25_v1` (13.699 API, 8,87 USD), `h0_test_c1_k0_v1` (3.299 API, 4,71 USD), `h0_test_norag_v2` (370 API nối tiếp 2.917 câu cache `_v1`, tổng 1,10 USD), `h0_test_*_b120_v1` (0 API, khớp 100% đường ngân sách); **0 lỗi judge** |
| 5. Đặc trưng neo C3 + replay CTAV + ablation + Phát hiện 11 | Có | `m8_anchor_features_test_v1`, `ctav_final_test_v1`, `m8_finding11_test_v1`, `m8_finding11_val_v1` (0 LLM) |
| 6. C5 một điểm (`η = (0; 0,4; 0,6), τ = 0,8`, V34 (b)) | Có | 61 cửa sổ được cứu → `m8_rescue_test_c1_v1` (61 API, 0,09 USD, 0 lỗi) → `m8_rescue_test_v1` (+0 TP, +1 FP) |
| 7. Phương sai judge `repeat` 1, 2 trên 200 cửa sổ (`seed = 42`) | Có | `h0_test_{bm25,c1_k0}_rep{1,2}_v1` (748 API mới, 1,08 USD, 0 lỗi): đồng thuận 3/3 đạt 99,0% (BM25) và 99,5% (C1) |
| 8. **DoD chính:** bảng H0–H4 có bootstrap CI + McNemar; kết luận H2 viết trung thực | **Có** | `eval/results/m8_test_tables_v1/` (`tables.md`, `verdicts.json`), `docs/drafts/ch5-ket-qua-test.md` (§5.7–§5.8) |
| 9. Mẫu 50 cửa sổ chấm tay context precision (V35 (a)) | Có (xuất mù) | `eval/manual/context_precision_test_v1.csv` (50 cửa sổ, 525 dòng bằng chứng) + `.key.csv` + `README-context-precision.md`; người dùng chấm sau, không chặn M9 (QĐ-037) |
| 10. Báo cáo mốc + tóm tắt 1 trang gửi GVHD (`04` §10) | Có | File này + `docs/drafts/2026-11-16-mail-gvhd-gtest.md` |

### Số liệu chính trên `test` (cửa sổ có telemetry: 11.985 cửa sổ, 346 fault)

**Bảng 1. So sánh các phương pháp trên `test` cạnh `val` (7.636 cửa sổ, 209 fault).**

| Phương pháp | `test`: TP | FP | Precision | Recall [CI95] | F1 [CI95] | FPR [CI95] | `val`: R / F1 / FPR |
|---|---:|---:|---:|---|---|---|---|
| Detector-only | 224 | 3.435 | 0,061 | 0,647 [0,601; 0,699] | 0,112 [0,100; 0,126] | 0,2951 [0,2870; 0,3036] | 0,522 / 0,111 / 0,2208 |
| LLM-không-RAG | 37 | 371 | 0,091 | 0,107 [0,077; 0,139] | 0,098 [0,071; 0,126] | 0,0319 [0,0288; 0,0351] | 0,086 / 0,092 / 0,0224 |
| BM25 | 34 | 369 | 0,084 | 0,098 [0,070; 0,130] | 0,091 [0,064; 0,119] | 0,0317 [0,0285; 0,0350] | 0,163 / 0,103 / 0,0561 |
| C1 (`k_graph = 0`) | 96 | 1.235 | 0,072 | 0,277 [0,230; 0,321] | 0,114 [0,093; 0,135] | 0,1061 [0,1007; 0,1118] | 0,263 / 0,126 / 0,0816 |
| **CTAV** (`dev` p90, đóng băng) | **14** | **64** | **0,179** | **0,040 [0,022; 0,061]** | **0,066 [0,036; 0,100]** | **0,0055 [0,0042; 0,0069]** | 0,139 / 0,201 / 0,0069 |
| *Đối chứng H3:* `c3_rolling_baseline` | **47** | **391** | **0,107** | **0,136 [0,101; 0,172]** | **0,120 [0,090; 0,151]** | **0,0336 [0,0304; 0,0369]** | 0,163 / 0,137 / 0,0343 |

**Bảng 2. Kết luận kiểm định H0–H4 theo đúng bản đăng ký `be2b985`.**

| Giả thuyết | Kết luận trên `test` | Số đo quyết định |
|---|---|---|
| **H0** (C1 − BM25) | **Chấp nhận** (4/4 vế) | ΔRecall `+0,179 [+0,138; +0,226]`, ΔFPR `+0,0744 [+0,0694; +0,0798]`, McNemar fault & normal `p < 0,001` (+62 TP, +866 FP) |
| **H2** (chính: CTAV − BM25, − C1) | **Không được chấp nhận** | Đạt sâu vế (ii) FPR (`ΔFPR = −0,0262 [−0,0297; −0,0229]`, giảm 5,8× FP, Precision `0,179` vs `0,084`); **không đạt** vế (i) (`ΔF1 = −0,025 [−0,067; +0,014]`) và vế (iii) (`ΔRecall = −0,237 < −0,05`) |
| **H3** (thành phần quanh CTAV) | **Đạt cả 3 tiêu chí** | Bỏ C3: `ΔPrecision = −0,107 [−0,197; −0,030]` (C3 đóng góp); +C2: `ΔFPR = +0,0000` (xác nhận bỏ); +C4: `13,56 vs 8,16 USD`, `ΔF1 = −0,001 [−0,001; +0,000]` (xác nhận bỏ); C5 một điểm: `+0 TP, +1 FP` (+61 lần gọi) |
| **H4** (ngân sách 120 lần gọi) | **Chấp nhận** | F1(CTAV) `0,034 [0,011; 0,064]` (6 TP, 0 FP) ≥ F1(không-RAG) `0,017 [0,000; 0,038]` (3 TP, 3 FP) |

**Giải thích cơ chế cốt lõi (Phát hiện 11 trên `test`, `m8_finding11_test_v1`).**
Trên `test`, do split chia theo lần tiêm lỗi (QĐ-036), **32 / 42 service** (88,1% cửa sổ telemetry, **61,0% số fault = 211 / 346**, so với 50,2% trên `val`) không có ngưỡng p90 trong `data/span_baseline.parquet` (dựng từ `dev`). C3 đóng băng hạ **trọn 67 / 67 TP của C1 về 0** trên 32 service này, làm mất ngay `0,194` recall toàn tập. Khi thay **duy nhất** nguồn ngưỡng của C3 sang ngưỡng trượt 60 phút đã đăng ký sẵn ở H3 (`c3_rolling_baseline`, phủ 91,2% span C1 thay vì 16,1%), hệ thống đạt **47 TP, 391 FP, F1 = 0,120 (`ΔF1 vs CTAV = +0,054 [+0,017; +0,091]`), FPR = 0,0336**: giữ nhiều hơn BM25 13 TP (+38%), cắt 68,3% FP của C1 (1.235 → 391, đưa FPR về sát mức 0,0317 của BM25) và đạt F1 điểm cao nhất trong mọi phương pháp trên `test`. Điều này chứng minh nguyên lý neo bằng chứng C3 là đúng, còn sự thất bại của H2 thuộc về tính mong manh của ngưỡng tĩnh `dev` dưới độ lệch thành phần service.

**Chi phí thực tế M8:** **21.094 lần gọi API mới = 15,85 USD theo token** (phiên 2026-11-14: 19.915 câu = 14,55 USD; phiên 2026-11-16: 1.179 câu = 1,29 USD), nằm dưới ngân sách 18 USD theo token của M8.

## 2. Cần review gì

| # | Kiểm gì | Ở đâu (file:dòng / lệnh) | Vì sao rủi ro |
|---|---|---|---|
| 1 | Mục đăng ký giả thuyết `be2b985` còn nguyên vẹn từng chữ không | `git diff be2b985 -- docs/experiment-log.md` (chỉ được có phần thêm từ QĐ-035..038 phía dưới, 0 dòng xóa/sửa trong khối đăng ký) | Cam kết khoa học cốt lõi của G-test |
| 2 | Cách trình bày kết luận "H2 không được chấp nhận" kèm đối chứng `c3_rolling_baseline` | `docs/drafts/ch5-ket-qua-test.md` §5.7.5 & §5.8.2; `docs/drafts/2026-11-16-mail-gvhd-gtest.md` | Cần tuyệt đối khách quan: không sửa ngược cấu hình chính sang `C3-trượt`, nhưng trình bày rõ cơ chế để hội đồng thấy đóng góp khoa học |
| 3 | Tính khớp của `h0_test_norag_v2` sau khi `_v1` bị ngắt | `eval/results/h0_test_norag_v2/runtime.json` (`cache_hits = 13329`, `api_calls = 370`, `judge_errors = 0`); thư mục `_v1` vẫn rỗng | Đảm bảo quy tắc không ghi đè `eval/results/` và tận dụng đúng cache |
| 4 | File chấm tay context precision | `eval/manual/context_precision_test_v1.csv` và `README-context-precision.md` | Không được mở `.key.csv` trước khi chấm xong 525 dòng để giữ tính mù |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| **V36** | Đầu vào cảnh báo cho đánh giá H5 (RCA Agent) trên `test` ở M9-B: cấu hình CTAV đóng băng (`ctav_final_test_v1`) chỉ phát 78 cảnh báo (14 TP, 64 FP) trên 10 service có ngưỡng `dev` (0 cảnh báo ở 11 service có fault thiếu ngưỡng `dev`), trong khi `c3_rolling_baseline` phát 438 cảnh báo (47 TP, 391 FP) phủ hầu hết các lần tiêm lỗi | **(a)** Giữ chỉ số chính thức của H5 trên đúng 78 cảnh báo của `ctav_final_test_v1` theo bản đăng ký `be2b985`, **và** báo kèm một dòng độ nhạy phụ trên 438 cảnh báo của `c3_rolling_baseline` (0 LLM thêm cho bước grouping/propagation 1-hop; chỉ tốn vài chục câu tóm tắt nếu chạy summarizer); **(b)** Chỉ chạy trên 78 cảnh báo của `ctav_final_test_v1` | **(a)** — tôn trọng tuyệt đối bản đăng ký `be2b985` cho kết luận H5, đồng thời tránh việc đánh giá RCA bị khuyết 11/20 service có fault trên `test` | Không chặn M9-A (trên `val`); chốt trước M9-B (`test`) |
| V35 (đã chốt (a) ở QĐ-037) | Chấm tay 525 dòng trong `eval/manual/context_precision_test_v1.csv` | Bạn điền cột `grade` (`relevant` / `irrelevant` / `unsure`), gửi lại để ghép `.key.csv` điền Bảng 5.25 (T15) | Chấm lúc thuận tiện trước M12 | Không chặn M9–M11 |

## 4. Plan cho mốc tiếp theo (M9 — RCA Agent)

Theo các quyết định rút ngắn đường găng đã chốt ở QĐ-037 (đã bỏ `propagation` mức 2 LLM full path; M8 đã **xong phần API** nên M9 dùng được Gemini thật trong phạm vi ngân sách 1 USD):

1. **M9-A trên `val` (`ctav_final_val_v1`, 80 cảnh báo):**
   - Hoàn thiện `services/rca_agent/grouping.py`; quét `T_group ∈ {180, 300, 600}` s trên `val` để chọn `T_group` đạt Alert Reduction Ratio (ARR) ≥ 30% trên cascade / `network_delay`; ghi `incidents` vào PostgreSQL.
   - Hoàn thiện `services/rca_agent/propagation.py` mức 1 (backward 1-hop thuần thuật toán trên đồ thị dịch vụ + thời gian cảnh báo); đo `Hit@1`, `Hit@3` so với baseline "service có anomaly score cao nhất trong incident".
   - Hoàn thiện `services/rca_agent/summarizer.py` theo schema `03` §2 + validator (`diagnostic_rejected`, `require_evidence`, chặn câu lệnh thực thi nguy hiểm); đo `JSON valid rate ≥ 0,95` trên `val` (ước vài chục lần gọi Gemini, < 0,2 USD).
2. **M9-B trên `test` (kiểm định chính thức H5 theo QĐ-037):**
   - Chạy cấu hình M9 đã chốt từ `val` một lần lên cảnh báo CTAV của `test` (`ctav_final_test_v1`, kèm dòng độ nhạy `c3_rolling_baseline` nếu bạn duyệt V36 (a)); tính CI bootstrap cho `ΔHit@1`, kiểm tra tiêu chí H5 (`Hit@1 ≥ 0,60`, `Hit@3 ≥ 0,80`, `ARR ≥ 30%`).
   - Viết báo cáo `docs/milestones/M9-rca-agent.md` và nháp chương kết quả RCA.

- **DoD M9:** ARR ≥ 30% trên `network_delay`; có `Hit@1`/`Hit@3` mức 1; `JSON valid rate ≥ 0,95` trên `val`; có bảng kiểm định H5 (theo lộ trình gộp M9-B của QĐ-037).
- **Rủi ro đã biết:** 78 cảnh báo của `ctav_final_test_v1` trên `test` sẽ gom thành ít incident (chỉ ở các service có ngưỡng `dev`), khiến mẫu đánh giá `Hit@1` nhỏ và khoảng tin cậy rộng — phương án V36 (a) là đối sách trực tiếp cho rủi ro này.

## Phụ lục

- **Sai lệch nhỏ so với plan ban đầu:**
  1. `h0_test_norag_v1` bị ngắt giữa chừng ở câu 2.917/3.287 ngày 2026-11-14; theo quy tắc không ghi đè, giữ nguyên thư mục `_v1` rỗng và chạy `h0_test_norag_v2` (hỏi nốt 370 câu, QĐ-038).
  2. `m8_tables.py` được chạy gộp luôn `--rescue m8_rescue_test_v1` ngay ở `m8_test_tables_v1` (nên `m8_test_tables_v1` đã chứa đầy đủ cả dòng H3 — C5, không cần sinh thêm `v2`).
- **Nguyên liệu cho luận văn (đã sẵn sàng lắp vào Word):**
  - Toàn văn nháp hoàn chỉnh §5.7.1–§5.7.8 và §5.8.1–§5.8.6 (Bảng T1–T15): `docs/drafts/ch5-ket-qua-test.md`.
  - Bảng chuẩn hóa tự động từ JSON: `eval/results/m8_test_tables_v1/tables.md`, `eval/results/m8_finding11_test_v1/tables.md`, `eval/results/m8_finding11_val_v1/tables.md`, `eval/results/m8_detector_shift_test_v1/tables.md`.
  - Bản nháp mail 1 trang báo cáo GVHD: `docs/drafts/2026-11-16-mail-gvhd-gtest.md`.
- **Lệnh tái lập đầy đủ:** xem cuối QĐ-035, QĐ-036, QĐ-037 và QĐ-038 trong `docs/experiment-log.md`.
