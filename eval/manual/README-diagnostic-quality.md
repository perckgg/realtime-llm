# Hướng dẫn chấm chất lượng báo cáo chẩn đoán (`test`, M11)

Đánh giá theo `docs/Final_Thesis_Phase2/02-data-and-experiment-protocol.md` §4.4 (thang `0–2`, mẫu ngẫu nhiên 30 incident từ `rca_final_test_v1`, `seed = 42`).

## 1. File trong thư mục

- `diagnostic_quality.csv` — **bảng chấm mù** (30 dòng, UTF-8-BOM mở trực tiếp bằng Excel). Đã tách toàn bộ nhãn gốc và `invalid_evidence_ids`. **15 dòng đầu (`sample_no = 1..15`) tự nó là một mẫu ngẫu nhiên hợp lệ** — bạn cần chấm tối thiểu 15 dòng đầu (chấm đủ 30 sẽ thu hẹp khoảng tin cậy).
- `diagnostic_quality.key.csv` — **khóa đối chiếu** (`status`, `true_root_cause`, `graph_relation`, `objective_rc_score`). **Tuyệt đối không mở trước khi chấm xong.**

## 2. Thang chấm (`0`, `1`, `2`)

Chỉ điền số nguyên `0`, `1` hoặc `2` vào 3 cột `root_cause_score`, `evidence_score`, `action_score` (cột `note` tùy chọn). Không xóa/sắp xếp lại dòng.

| Tiêu chí | `0` | `1` | `2` |
|---|---|---|---|
| **Đúng root cause** (`root_cause_score`) | **Sai:** service kết luận không liên quan hoặc telemetry/bằng chứng hoàn toàn bình thường (không có lỗi thật). *VD:* báo cáo kết luận `frontend` lỗi CPU nhưng `alerts_summary` và span chỉ cho thấy lưu lượng bình thường. | **Gần đúng (service liền kề):** báo cáo chỉ vào caller phát cảnh báo (`frontend` / `ts-travel-service`), nhưng span/log trích dẫn lại cho thấy độ trễ/lỗi phát sinh trực tiếp ở một downstream call (`CheckoutService/PlaceOrder`, `ts-basic-service`). | **Đúng:** bằng chứng metric/trace/log cục bộ ủng hộ rõ sự cố nằm ngay tại `predicted_root_cause` và phù hợp với `predicted_fault_type`. |
| **Bằng chứng hợp lệ** (`evidence_score`) | **Bịa hoặc không liên quan:** danh sách bằng chứng rỗng, ID vô nghĩa hoặc toàn span `INFO` vài ms / heartbeat không giải thích được bất thường. | **Liên quan một phần:** trích đúng ngữ cảnh quanh sự cố nhưng pha trộn span bình thường hoặc thiếu tín hiệu giải thích nguyên nhân / loại lỗi. | **Đúng và đủ:** các mục trong `cited_evidence` khớp thời điểm, chỉ ra span chậm vượt nền hoặc log lỗi chứng minh trực tiếp cho nhận định. |
| **Gợi ý xử lý dùng được** (`action_score`) | **Vô nghĩa / rủi ro:** gợi ý sai ngữ cảnh, mơ hồ không thực hiện được, hoặc chứa câu lệnh thực thi nguy hiểm. | **Chung chung:** đúng hướng nhưng mang tính mẫu chung cho mọi ca (VD: *"kiểm tra CPU và log của service X"*, *"xem lại thay đổi gần đây"*). | **Cụ thể, khả thi:** gắn với triệu chứng, thao tác/endpoint hoặc callee cụ thể xuất hiện trong bằng chứng (VD: *"kiểm tra nghẽn gọi `CurrencyService/Convert` hoặc pool kết nối của `ts-travel-service`"*). |

*(Lưu ý khi chấm mù: đánh giá dựa trên `alerts_summary`, `judge_reasonings`, `cited_evidence` và đồ thị dịch vụ trong hệ; sau khi bạn nộp bảng chấm, script tổng hợp mới đối chiếu thêm với nhãn gốc ở `.key.csv`.)*

## 3. Người chấm thứ hai & lệnh tổng hợp

- **Người chấm thứ hai (tùy chọn):** gửi bản sao **trống điểm** của 20% đầu mẫu đã chấm (`sample_no = 1..6` nếu chấm 30, hoặc `1..3` nếu chấm 15) để chấm độc lập và tính độ đồng thuận Cohen's $\kappa$.
- **Tổng hợp sau khi chấm:** giữ nguyên file `eval/manual/diagnostic_quality.csv` (lưu UTF-8) rồi chạy:

```bash
py scripts/m11_score_diagnostic_quality.py \
  --graded eval/manual/diagnostic_quality.csv \
  --key eval/manual/diagnostic_quality.key.csv \
  --out eval/results/m11_diagnostic_quality_v1
```
