# M11 — Đánh giá bằng người + phân tích lỗi

| | |
|---|---|
| Ngày mở mốc | **2026-11-17** (QĐ-049) |
| Ngày cập nhật bản nháp | 2026-11-19 (**M11-A xong; chờ người dùng chấm tay để đóng mốc**) |
| Hạn mục tiêu | 2027-01-17 |
| Kết luận | **ĐANG LÀM** — **chờ người dùng chấm mù `eval/manual/diagnostic_quality.csv` (`n ≥ 15`)** mới tổng hợp bước 4 và đóng mốc. Đã xong 100% việc kỹ thuật 0 USD (lấy mẫu mù `seed = 42`, script chấm điểm + Cohen's $\kappa$, phân tích toàn bộ ca sai `test` CTAV & RCA, tổng duyệt demo lần 1 và nháp Chương 7 §7.3–§7.5 + nguyên liệu §8.2.1). |
| Commit | *(M11-A đã tách commit riêng theo QĐ-050; hash đóng mốc bổ sung ở M11-B)* |
| Quyết định liên quan | QĐ-037, QĐ-049, **QĐ-050** (M11-A) |

---

## 1. Kết quả hiện tại

| Việc / DoD (`04` §M11 & `P5`) | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|
| 1. `scripts/m11_sample_incidents.py`: lấy mẫu ngẫu nhiên 30 incident `test` (`rca_final_test_v1`, `seed = 42`) sao cho 15 dòng đầu tự nó là mẫu ngẫu nhiên hợp lệ; xuất bảng chấm mù 3 tiêu chí + hướng dẫn ≤ 1 trang + tách khóa | **Đạt** (2026-11-19) | `scripts/m11_sample_incidents.py`, `eval/manual/diagnostic_quality.csv` (30 dòng, không chứa nhãn gốc hay `invalid_evidence_ids`), `eval/manual/diagnostic_quality.key.csv`, `eval/manual/README-diagnostic-quality.md` (32 dòng); 15 dòng đầu gồm `6 labelled / 7 no_fault / 2 ambiguous`, đủ 30 gồm `15 / 13 / 2`; `tests/test_m11.py` kiểm khớp tiền tố & tính mù |
| 2. Người dùng chấm mù `diagnostic_quality.csv` (`n ≥ 15` dòng đầu; thêm người chấm thứ hai trên 20% nếu có) | **Chờ người dùng** | Đã xuất sẵn bảng chấm mù và hướng dẫn |
| 3. Phân tích ca sai trên `test` (chỉ mô tả, không đổi tham số): toàn bộ 64 FP & 332 FN của CTAV + toàn bộ ca RCA sai (tập đăng ký và dòng độ nhạy), gắn độ lệch detector M8 | **Đạt** (2026-11-19) | `scripts/m11_error_analysis.py`, `eval/results/m11_error_analysis_test_v1/{error_analysis.json,tables.md}`; `0` USD API; kiểm bất biến số học với M8/M9 trong `tests/test_m11.py` |
| 4. Script tổng hợp điểm chất lượng báo cáo (CI bootstrap + độ đồng thuận Cohen's $\kappa$, chỉ báo `n` thực chấm) | **Có script; chờ CSV đã chấm** | `scripts/m11_score_diagnostic_quality.py` (đã test logic tổng hợp & κ bằng `tests/test_m11.py`) |
| 5. Tổng duyệt demo lần 1 theo `08` §6, rà lại 3 lỗi từ M10-D | **Đạt** (2026-11-19, tổng hợp đợt rà `2026-11-18`) | Commit sửa UX & giải thích cho hội đồng (`2af9480`, `538f8cc`), `scripts/m11_graph_evidence_share.py`, danh sách lỗi tổng duyệt lần 1 bên dưới |
| **DoD:** `docs/drafts/ch7-phan-tich-ca-sai.md` (§7.3 mối đe doạ, §7.4 phân tích ca sai, §7.5 kết chương, hạn chế §8.2.1) | **Đạt phần phân tích; chờ điền §7.4.4** | `docs/drafts/ch7-phan-tich-ca-sai.md` (đã gắn `[CHỜ M11]` cho phần chấm tay) |

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
| **V50** | Chấm mù chất lượng báo cáo chẩn đoán trong `eval/manual/diagnostic_quality.csv` (tuyệt đối không mở `.key.csv` trước) | **(a)** Chấm tối thiểu `15` dòng đầu (`sample_no = 1..15`, đã là mẫu ngẫu nhiên hợp lệ theo `04` §9 ưu tiên 3); **(b)** Chấm đủ `30` dòng (`sample_no = 1..30`) để thu hẹp CI 95%; kèm người chấm thứ hai trên 20% đầu (`sample_no = 1..3` hoặc `1..6`) nếu thu xếp được | **(a)** nếu bận, **(b)** nếu có thời gian (khoảng 3–5 giờ); đọc hướng dẫn ở `eval/manual/README-diagnostic-quality.md` | **Có — chặn đóng M11** |
| **V51** | Cách lấy mẫu `30` trong `38` sự cố của `rca_final_test_v1` *(agent tự quyết, chờ người dùng xác nhận)* | **(a)** Lấy mẫu ngẫu nhiên đơn giản không hoàn lại (`seed = 42`) trên toàn bộ 38 sự cố (15 dòng đầu: `6 labelled / 7 no_fault / 2 ambiguous`; cả 30: `15 / 13 / 2`); **(b)** Phân tầng tỉ lệ theo `status` (khi đó 15 dòng đầu không còn tự động giữ phân tầng nếu cắt ngang không chia lô) | **(a)** — giữ đúng tỉ lệ tự nhiên trên `test` và đảm bảo cắt ở `n = 15` hay `n = 30` đều không thiên lệch | Không |
| **V52** | Chụp lại Hình 6.2–6.4 sau cập nhật giao diện `538f8cc` và nhắc **V35** (`context_precision_test_v1.csv`, hiện `0 / 525` dòng) | **(a)** Chụp lại hình khi tổng duyệt demo lần 2 ở M12 và hoàn tất V35 trước khi đóng M12; **(b)** Làm ngay ở M11-B | **(a)** cho M12 (hoặc làm luôn khi chạy Docker chụp ảnh nếu tiện) | Không chặn M11; cần trước M12 |

---

## 4. Plan cho nửa cuối mốc (M11-B) và M12

1. **M11-B (ngay sau khi người dùng gửi lại `eval/manual/diagnostic_quality.csv` đã chấm, 0 USD):**
   - Chạy `py scripts/m11_score_diagnostic_quality.py --graded eval/manual/diagnostic_quality.csv --key eval/manual/diagnostic_quality.key.csv --out eval/results/m11_diagnostic_quality_v1` (kèm `--second-rater` nếu có).
   - Điền số thực đo (`n`, trung bình ± SD, CI 95% bootstrap, đối chiếu `.key.csv`, Cohen's $\kappa$ nếu có) vào `docs/drafts/ch7-phan-tich-ca-sai.md` (§7.4.4, §7.5), `docs/milestones/M11-danh-gia-nguoi.md` (§1), cập nhật `docs/experiment-log.md` (`QĐ-051`), đóng M11 trong `docs/CURRENT-MILESTONE.md`, `04` §1, `docs/milestones/README.md` và chuyển sang **M12 (P6 — đóng gói)**.
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
