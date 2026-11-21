# Phân tích ca sai trên `test` (`m11_error_analysis_test_v1`)

## 1. 64 báo động giả (FP) của CTAV trên `test`

| Nhóm phân loại | Số FP | Tỉ lệ (%) | Chi tiết chính |
|---|---:|---:|---|
| Theo service: `frontend` / `ts-travel-service` | 39 / 25 | 60,9 / 39,1 | Đều có ngưỡng nền `dev` (`2022-08-22`: 39; `2023-01-30`: 25) |
| Verdict C1 gốc & confidence | 64 / 64 | 100,0 | `TRUE_ALERT`, `confidence = 0,9`; neo 100% qua `span > dev_p90` (`local`: 63, `mixed`: 1) |
| Trùng thời gian lỗi đang tiêm ở downstream (collateral) | 31 | 48.4 | Trung vị `duration/p90` = 3.02× (tối đa 68.78×) |
| Ngoài mọi lần tiêm lỗi (lưu lượng bình thường) | 33 | 51.6 | Trung vị `duration/p90` = 1.95× (tối đa 7.6×) |

## 2. 332 sự cố bị bỏ sót (FN) của CTAV trên `test`

| Tầng gây bỏ sót | Số FN | Tỉ lệ / 332 (%) | Ghi chú |
|---|---:|---:|---|
| Detector không đưa lên candidate (`score < 0,85`) | 122 | 36.7 | Chủ yếu `network_delay` (62), `return` (27), `exception` (23) |
| Judge C1 trả `FALSE_POSITIVE` | 128 | 38.6 | Đủ 6 sự kiện ngữ cảnh; 64 có ngưỡng `dev` / 64 không |
| C3 hạ — thiếu ngưỡng nền `dev` của service | 67 | 20.2 | Phát hiện 11 trên 11 service có fault |
| C3 hạ — thiếu ngưỡng thao tác trong service có `dev` | 3 | 0.9 | Gồm 2 span `WARN` > 1.000 ms trên `ts-travel-service` |
| C3 hạ — span có ngưỡng nhưng dưới `dev` p90 | 12 | 3.6 | Không có log `ERROR`/`WARN` cục bộ |

## 3. Ca sai của tác tử RCA trên `test`

| Run | Tổng sự cố | Có nhãn | Trúng Hit@1 | Trượt Hit@1 | Phân loại trượt |
|---|---:|---:|---:|---:|---|
| Đăng ký (`rca_final_test_v1`) | 38 | 17 | 8 | 9 | 7 callee 1-hop không cảnh báo; 2 ≥2-hop/không cạnh; +29/50 tiêm lỗi 0 cảnh báo |
| Độ nhạy ngoài đăng ký (`rca_sens_test_c3rolling_v1`) | 114 | 48 | 10 | 38 | 33 thiếu cảnh báo ở service gốc; 5 sai xếp hạng đa service (đều trúng Hit@3) |
