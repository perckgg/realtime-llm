# M11 — Đánh giá bằng người + phân tích lỗi

| | |
|---|---|
| Ngày mở mốc | **2026-11-17** (QĐ-049) |
| Ngày cập nhật bản nháp | 2026-11-22 (**M11-A, V35 (vá luật, `m8_context_precision_v2`) và V50 (AI chấm nháp, tác giả duyệt, `m11_diagnostic_quality_v1`) xong**) |
| Hạn mục tiêu | 2027-01-17 |
| Kết luận | **ĐẠT phần kỹ thuật — chờ commit và đóng mốc.** V50 đã chấm 30/30 sự cố (AI `deepseek-flash` chấm nháp trên bảng mù, tác giả rà soát và sửa 9 dòng trước khi mở khoá), tổng hợp ở `eval/results/m11_diagnostic_quality_v1`; V35 vá luật đọc lỗi trong `content`, chấm lại ở `eval/results/m8_context_precision_v2`; số đã điền vào nháp Chương 7 và LaTeX §5.8.6, §7.3, §7.4.4, §7.5. |
| Commit | *(M11-A đã tách commit riêng theo QĐ-050; hash đóng mốc bổ sung ở M11-B)* |
| Quyết định liên quan | QĐ-037, QĐ-049, **QĐ-050** (M11-A) |

---

## 1. Kết quả hiện tại

| Việc / DoD (`04` §M11 & `P5`) | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|
| 1. `scripts/m11_sample_incidents.py`: lấy mẫu ngẫu nhiên 30 incident `test` (`rca_final_test_v1`, `seed = 42`) sao cho 15 dòng đầu tự nó là mẫu ngẫu nhiên hợp lệ; xuất bảng chấm mù 3 tiêu chí + hướng dẫn ≤ 1 trang + tách khóa | **Đạt** (2026-11-19) | `scripts/m11_sample_incidents.py`, `eval/manual/diagnostic_quality.csv` (30 dòng, không chứa nhãn gốc hay `invalid_evidence_ids`), `eval/manual/diagnostic_quality.key.csv`, `eval/manual/README-diagnostic-quality.md` (32 dòng); 15 dòng đầu gồm `6 labelled / 7 no_fault / 2 ambiguous`, đủ 30 gồm `15 / 13 / 2`; `tests/test_m11.py` kiểm khớp tiền tố & tính mù |
| 2. Chấm mù `diagnostic_quality.csv` (`n ≥ 15` dòng đầu) | **Đạt** (2026-11-22, 30/30 dòng) | AI chấm nháp `diagnostic_quality.ai_scores.csv` + `ai_review.md`; tác giả duyệt đề xuất sửa 10 dòng (`diagnostic_quality.proposed.csv`, sửa thật 9 dòng: 1, 4, 11, 13, 17, 19, 22, 25, 30; dòng 18 giữ điểm, đổi lý do) **trước khi mở `.key.csv`**; điểm đã duyệt chép vào `diagnostic_quality.csv`, cột `note` ghi `[AI nháp, tác giả duyệt]`. Không có người chấm thứ hai ⇒ không tính Cohen's κ |
| 3. Phân tích ca sai trên `test` (chỉ mô tả, không đổi tham số): toàn bộ 64 FP & 332 FN của CTAV + toàn bộ ca RCA sai (tập đăng ký và dòng độ nhạy), gắn độ lệch detector M8 | **Đạt** (2026-11-19) | `scripts/m11_error_analysis.py`, `eval/results/m11_error_analysis_test_v1/{error_analysis.json,tables.md}`; `0` USD API; kiểm bất biến số học với M8/M9 trong `tests/test_m11.py` |
| 4. Script tổng hợp điểm chất lượng báo cáo (CI bootstrap, đối chiếu khoá) | **Đạt** (2026-11-22) | `eval/results/m11_diagnostic_quality_v1/{summary.json,tables.md}`: root cause `0,900 ± 0,845` [0,600; 1,200] (`12/9/9`), bằng chứng `1,133 ± 0,937` [0,800; 1,500] (`11/4/15`), gợi ý xử lý `1,167 ± 0,379` [1,033; 1,300] (`0/25/5`); trên 15 sự cố có nhãn, khớp thang khách quan `8/15`, trung bình chấm `1,000` vs khách quan `1,333`; trong 9 báo cáo chấm root cause = 2 chỉ 3 là `EXACT` |
| 5. Tổng duyệt demo lần 1 theo `08` §6, rà lại 3 lỗi từ M10-D | **Đạt** (2026-11-19, tổng hợp đợt rà `2026-11-18`) | Commit sửa UX & giải thích cho hội đồng (`2af9480`, `538f8cc`), `scripts/m11_graph_evidence_share.py`, danh sách lỗi tổng duyệt lần 1 bên dưới |
| **DoD:** `docs/drafts/ch7-phan-tich-ca-sai.md` (§7.3 mối đe doạ, §7.4 phân tích ca sai, §7.5 kết chương, hạn chế §8.2.1) | **Đạt** (2026-11-22) | `docs/drafts/ch7-phan-tich-ca-sai.md` §7.4.4, §7.5 đã điền số; bản LaTeX `Sections/Ch7_ThaoLuan.tex` |

### Tóm tắt số liệu phân tích ca sai trên `test` (`eval/results/m11_error_analysis_test_v1/`)

**Bảng 1. Phân loại 64 báo động giả (`FP`) và 332 sự cố bị bỏ sót (`FN`) của CTAV (`ctav_final_test_v1`, `11.985` cửa sổ telemetry, `346` fault).**

| Lớp lỗi | Nhóm | Số lượng | Tỉ lệ | Ghi chú chính |
|---|---|---:|---:|---|
| **CTAV FP (64)** | Trùng thời gian lỗi đang tiêm ở downstream (*collateral*) | 31 | 48,4% | `frontend` 17, `ts-travel-service` 14; trung vị `duration / dev_p90 = 3,02×` (tối đa `68,78×`), chủ yếu `network_delay` (`20`) |
| **CTAV FP (64)** | Ngoài mọi lần tiêm lỗi (lưu lượng bình thường) | 33 | 51,6% | `frontend` 22, `ts-travel-service` 11; trung vị `duration / dev_p90 = 1,95×` (tối đa `7,60×`); toàn bộ `64 / 64` có `C1 = TRUE_ALERT (0,9)` và neo qua `span > dev_p90` |
| **CTAV FN (332)** | Detector bỏ sót (`score < 0,85`) | 122 | 36,7% | `network_delay` 62, `return` 27, `exception` 23, `cpu_contention` 10 |
| **CTAV FN (332)** | `Judge` `C1` trả `FALSE_POSITIVE` | 128 | 38,6% | Đều có đủ 6 sự kiện ngữ cảnh; `64` có ngưỡng `dev` / `64` không |
| **CTAV FN (332)** | `C3` hạ — service thiếu ngưỡng `dev` (Phát hiện 11) | 67 | 20,2% | `checkoutservice` 17, `currencyservice` 10, `adservice` 9, `ts-food-service` 9, `productcatalogservice` 8, `ts-preserve-service` 7, `ts-basic-service` 5, `emailservice` 2 |
| **CTAV FN (332)** | `C3` hạ — thao tác thiếu ngưỡng `dev` trong service có `dev` | 3 | 0,9% | `ts-travel-service` (`57549fece1b3bbcd`, `a51fd9368feedc27`, `0b89a4f5493363ee`), gồm `2` span `WARN` > `1.000 ms` không được neo |
| **CTAV FN (332)** | `C3` hạ — span cục bộ thấp hơn `dev` `p90` | 12 | 3,6% | `frontend` 8, `ts-travel-service` 3, `ts-travel2-service` 1; không có log `ERROR`/`WARN` |

**Bảng 2. Phân loại ca sai của tác tử RCA trên `test` (`rca_final_test_v1` và dòng độ nhạy ngoài đăng ký).**

| Run | Tổng sự cố | Có nhãn | Trúng Hit@1 | Trượt Hit@1 | Phân loại chi tiết ca trượt & tóm tắt |
|---|---:|---:|---:|---:|---|
| `rca_final_test_v1` (đăng ký) | 38 (`18` `no_fault`, `3` `ambiguous`) | 17 | 8 | **9** | **7** `callee` `1-hop` không có cảnh báo (`frontend` → `checkoutservice` ×2 / `currencyservice` ×2; `ts-travel-service` → `ts-basic-service` ×2 / `ts-route-service` ×1); **2** `≥2-hop` hoặc không cạnh (`inc-f3161a3992b92cda`, `inc-049cc7be85eeacb2`). Ngoài ra **29 / 50** lần tiêm không có cảnh báo CTAV. Tóm tắt: `35 / 38` gán `cpu_contention` (đúng loại lỗi `5 / 17 = 29,4%`), `1` ca có ID tự bịa bị lọc (`inc-a0589ae59b492c07`). |
| `rca_sens_test_c3rolling_v1` (độ nhạy ngoài đăng ký) | 114 (`52` `no_fault`, `14` `ambiguous`) | 48 | 10 | **38** | **33** thiếu cảnh báo ở service gốc (`21` `≥2-hop`/không cạnh, `6` `callee` `1-hop`, `6` `caller` `1-hop`); **5** lỗi xếp hạng đa service (đều trúng `Hit@3`: `3` lỗi ở `caller` `1-hop` bị dồn phiếu về `callee` như `inc-bd062ac615eaf3d7`, `2` hòa phiếu thua tie-break như `inc-15b089daf856a2e2`). Tóm tắt: `96 / 114` gán `cpu_contention` (đúng `8 / 48 = 16,7%`), `4` ca có ID tự bịa bị lọc. |

### V35 — Chỉ số gần đúng về chất lượng ngữ cảnh trên `test` (xong 2026-11-22, QĐ-051; vá luật cùng ngày)

50 cửa sổ có telemetry × 2 phương pháp (mỗi phương pháp `top_k = 6`, 525 sự kiện phân biệt, trùng 75 sự kiện). Nhãn do quy tắc ngưỡng cố định (`scripts/m8_context_precision_rule_label.py`), **không phải người chấm từng dòng**: `1` nếu `WARN`/`ERROR` (cột `severity`), log có level `ERROR`/`FATAL`/`CRITICAL` trong `content`, span `BasicErrorController.error`, hoặc `duration_ms ≥ 200`, và nằm trong ±180 s; `?` nếu 100–200 ms trong ±120 s; còn lại `0`.

**Vá 2026-11-22:** cột `severity` của Nezha hầu như luôn `INFO`, nên bản đầu bỏ sót `W49.E5` (log JSON `ERROR ... Failed!`), `W29.E2` và `W47.E3` (span `BasicErrorController.error` ~1 ms). Luật mới đọc thêm `content`; 8 test mới trong `tests/test_m8_context_precision.py` (27/27 qua). Kết quả cũ `m8_context_precision_v1` giữ nguyên để đối chiếu (thư mục kết quả bất biến), kết quả mới ở `m8_context_precision_v2`.

| Phương pháp | Retrieval | Liên quan | `?` | Micro precision | CI 95 % | Cửa sổ có ≥ 1 liên quan |
|---|---:|---:|---:|---:|---|---:|
| BM25 | 300 | 4 | 2 | **0,0133** | [0,0000; 0,0300] | 3 / 50 |
| C1 | 300 | 26 | 15 | **0,0867** | [0,0433; 0,1367] | 11 / 50 |

Δ micro (C1 − BM25) = **+0,0733** [+0,0333; +0,1200]. Độ nhạy: `?` tính là liên quan +0,1167; loại `?` +0,0778; ngưỡng 100 ms +0,1200; ngưỡng 500 ms +0,0400.

Giới hạn (đã ghi ở §5.8.6 và §7.3): nhãn do quy tắc, không do người; quy tắc thưởng cho "span chậm gần cửa sổ" — đúng thứ thành phần thời gian của C1 tối ưu (76 % sự kiện C1 trong ±180 s so với 58 % của BM25) — nên **không dùng để khẳng định C1 tốt hơn BM25**; ngưỡng tuyệt đối 200 ms bỏ qua mức nền từng thao tác (18/24 span bị gắn "liên quan" theo thời lượng không vượt 2 lần trung vị thao tác của chính nó trong mẫu); precision tuyệt đối vẫn ≤ 9 %.

### Danh sách lỗi tổng duyệt demo lần 1 (`08` §6, tổng hợp sau đợt rà `2026-11-18`)

- **Đã xử lý ngày `2026-11-18` (trước M11-A):**
  - *(M10 lỗi #1)* Đã sửa việc chọn mặc định `pipeline_sens_test_v1` và đồng bộ `?run_id=` lên URL (`2af9480`, `src/lib/runContext.ts` + `App.tsx`, kiểm trình duyệt thật 5 bước kịch bản `08` §6, `0` lỗi console).
  - Bổ sung hai thẻ giải thích cho hội đồng trên giao diện tiếng Anh (`538f8cc`: *How C1 built this context* ở Alert Detail và *How the RCA agent localized the root cause* ở Incident Detail, kèm `scripts/m11_graph_evidence_share.py`).
- **Tồn đọng còn lại sau tổng duyệt lần 1 (xếp theo mức độ):**
  1. **Trung bình (`Tài liệu / Hình Ch6`):** Cần chụp lại bộ ảnh giao diện Chương 6 (`m10-timeline.png`, `m10-alert-c3-downgrade.png`, `m10-incident-cascade.png`) để phản ánh hai thẻ giải thích đồ thị mới thêm ở `538f8cc`.
  2. **Thấp (`UX`):** Trục X của biểu đồ Timeline mới gắn nhãn ngày `dd/MM` ở `bucket 0`, chưa nhắc lại tại các mốc chuyển ngày qua nửa đêm.
  3. **Thấp (`RCA UI`):** Thẻ lan truyền hiển thị khớp phiếu gốc `177 / 178` sự cố ở 3 run `pipeline_*`; riêng `inc-dd6ada446605fb93` hòa điểm `0,50` và phá hòa bằng `anomaly_score` trên toàn khoảng sự cố (đã gắn nhãn `"Tie"`).
  4. **Thẩm mỹ (`Build`):** Bundle JS của Vite vượt ngưỡng cảnh báo mặc định `500 kB` do chưa tách chunk theo route.

---

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Tính mù của bảng chấm `diagnostic_quality.csv` và tính hợp lệ tiền tố `1..15` | `eval/manual/diagnostic_quality.csv`, `scripts/m11_sample_incidents.py`, `tests/test_m11.py` | Không được lộ `status`, `true_root_cause`, `level1_hit1`, `invalid_evidence_ids` sang file chấm |
| 2 | Đối khớp số lượng ca sai trong `m11_error_analysis_test_v1` với số đã chốt ở M8 và M9 | `eval/results/m11_error_analysis_test_v1/error_analysis.json`, `scripts/m11_error_analysis.py` | Mọi tổng thành phần (`14 + 332 = 346`, `122 + 128 + 82 = 332`, `31 + 33 = 64`, `8 + 9 = 17`, `29` không cảnh báo) phải khớp tuyệt đối |
| 3 | Văn phong và kỷ luật số liệu của nháp Chương 7 (không từ cấm, không lộ mã QĐ/V/M trong thân bài) | `docs/drafts/ch7-phan-tich-ca-sai.md` | Cần sẵn sàng ghép thẳng vào luận văn mà không mang giọng ghi chú nội bộ |

---

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| **V50** | Chấm mù chất lượng báo cáo chẩn đoán trong `eval/manual/diagnostic_quality.csv` | **Đã giải quyết 2026-11-22:** AI chấm nháp 30/30 dòng, tác giả duyệt đề xuất sửa 10 dòng trước khi mở khoá (QĐ-051) | Luận văn ghi: *"AI chấm nháp trên bảng mù, tác giả rà soát và hiệu chỉnh trước khi mở khóa đối chiếu"*; không báo Cohen's κ; mở rộng khai báo AI trong Lời cam đoan | Không |
| **V51** | Cách lấy mẫu `30` trong `38` sự cố của `rca_final_test_v1` *(agent tự quyết, chờ người dùng xác nhận)* | **(a)** Lấy mẫu ngẫu nhiên đơn giản không hoàn lại (`seed = 42`) trên toàn bộ 38 sự cố (15 dòng đầu: `6 labelled / 7 no_fault / 2 ambiguous`; cả 30: `15 / 13 / 2`); **(b)** Phân tầng tỉ lệ theo `status` (khi đó 15 dòng đầu không còn tự động giữ phân tầng nếu cắt ngang không chia lô) | **(a)** — giữ đúng tỉ lệ tự nhiên trên `test` và đảm bảo cắt ở `n = 15` hay `n = 30` đều không thiên lệch | Không |
| **V52** | Chụp lại Hình 6.2–6.4 sau cập nhật giao diện `538f8cc` | **(a)** Chụp lại hình khi tổng duyệt demo lần 2 ở M12; **(b)** Làm ngay ở M11-B | **(a)** cho M12 (hoặc làm luôn khi chạy Docker chụp ảnh nếu tiện) | Không chặn M11; cần trước M12 |

---

## 4. Plan cho nửa cuối mốc (M11-B) và M12

1. **M11-B (còn lại, 0 USD):**
   - Commit các thay đổi V35, V50 và cập nhật Chương 5–7; ghi QĐ-051 (AI chấm nháp + tác giả duyệt; vá luật V35) vào `docs/experiment-log.md`.
   - Mở rộng khai báo AI trong Lời cam đoan (style guide §5.3): thêm việc dùng LLM `deepseek-flash` chấm nháp V50 và đề xuất quy tắc V35; thêm mục tài liệu tham khảo cho mô hình chấm.
   - Đóng M11 trong `docs/CURRENT-MILESTONE.md`, `04` §1, `docs/milestones/README.md` và chuyển sang **M12 (P6 — đóng gói)**.
2. **M12 (P6, sau khi đóng M11):** kiểm tra chéo toàn bộ số liệu luận văn với `eval/results/`, hoàn tất hình vẽ còn thiếu (kèm chụp lại H6.2–H6.4), ghép bản thảo hoàn chỉnh, dọn repo tái lập trên bản clone sạch, tổng duyệt demo lần 2 và chuẩn bị slide bảo vệ.

---

## Phụ lục

- **Nguyên liệu cho luận văn:**
  - `docs/drafts/ch7-phan-tich-ca-sai.md` — toàn văn §7.3 (Bảng 7.2), §7.4 (Bảng 7.3 + §7.4.1–§7.4.4), §7.5 Kết chương, và 6 mục hạn chế cho §8.2.1.
  - `eval/results/m11_error_analysis_test_v1/{error_analysis.json,tables.md}` — bộ đếm & ví dụ định danh đầy đủ để script M12 kiểm khớp số liệu.
- **Lệnh tái lập M11-A (0 USD API):**
  ```bash
  py scripts/m11_sample_incidents.py --rca-run rca_final_test_v1 --ctav-run ctav_final_test_v1 --c1-run h0_test_c1_k0_v1 --n 30 --seed 42 --out eval/manual/diagnostic_quality
  py scripts/m11_error_analysis.py --out eval/results/m11_error_analysis_test_v1
  py -m pytest tests/test_m11.py -v
  ```
- **Lệnh tái lập V35 (0 USD API):**
  ```bash
  py scripts/m8_context_precision_rule_label.py --graded eval/manual/context_precision_test_v1.csv       --out eval/manual/context_precision_test_v1.ai_scores.csv --force
  py scripts/m8_context_precision_score.py --out eval/results/m8_context_precision_v2
  .venv/Scripts/python.exe -m pytest tests/test_m8_context_precision.py -q
  ```
  Ghi chú: trên máy này Windows chặn Python của `.venv` ghi vào `eval/`; chạy hai script bằng `py` hệ thống (chỉ dùng thư viện chuẩn).
- **Lệnh tái lập V50 (0 USD API, sau khi điểm đã duyệt nằm trong `diagnostic_quality.csv`):**
  ```bash
  py scripts/m11_score_diagnostic_quality.py --graded eval/manual/diagnostic_quality.csv       --key eval/manual/diagnostic_quality.key.csv --out eval/results/m11_diagnostic_quality_v1
  ```
