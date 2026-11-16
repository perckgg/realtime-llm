# Hướng dẫn chấm Context Precision thủ công (`test`, V35)

Phép đo mô tả theo `02-data-and-experiment-protocol.md` §4.2 và quyết định V35 (a) (QĐ-037): **không gắn tiêu chí giả thuyết** và **không chặn đóng M8 / mở M9**.

## 1. File trong thư mục này

- `context_precision_test_v1.csv` — **file để chấm** (50 cửa sổ có telemetry × 525 dòng sự kiện phân biệt, mã hóa UTF-8-BOM mở trực tiếp được bằng Excel). Mỗi sự kiện được khử trùng lặp giữa BM25 và C1, xáo ngẫu nhiên thứ tự cửa sổ và thứ tự sự kiện (`seed = 42`), ẩn phương pháp truy xuất, thứ hạng và nhãn lỗi thật.
- `context_precision_test_v1.key.csv` — **khóa đối chiếu** (`window_id`, `event_id`, nhãn fault thật, thứ hạng của từng phương pháp). **Tuyệt đối không mở trước khi chấm xong.**

## 2. Cách chấm

Chỉ điền vào cột **`relevance`** (cột `note` tùy chọn) cho mỗi dòng trong `context_precision_test_v1.csv` bằng một trong ba giá trị:

| Giá trị điền vào `relevance` | Ý nghĩa | Khi nào chọn |
|---|---|---|
| `1` (hoặc `lien_quan`) | **Liên quan** | Log/span cung cấp bằng chứng trực tiếp giúp xác định bất thường tại `(alert_service, window_start)` là lỗi thật hay nhiễu: ví dụ log `ERROR`/`WARN`/exception/5xx liên quan đường gọi, hoặc span có `duration_ms` tăng vọt bất thường / lỗi trên chính `alert_service` hoặc service gọi/được gọi trực tiếp quanh thời điểm cảnh báo. |
| `0` (hoặc `khong_lien_quan`) | **Không liên quan** | Sự kiện bình thường không mang tín hiệu chẩn đoán cho bất thường của cửa sổ (ví dụ span `INFO` vài ms lặp lại đều đặn cách xa cửa sổ 4–8 phút, heartbeat/healthcheck thông thường, hoặc sự kiện của nhánh không liên quan tới triệu chứng ở `top_features`). |
| `?` (hoặc `khong_chac`) | **Không chắc** | Thiếu ngữ cảnh để kết luận rõ giữa `1` và `0` (sẽ báo riêng tỉ lệ `?` và tính độ nhạy khi gộp vào `0` hoặc loại khỏi mẫu số). |

## 3. Lưu ý khi đọc các cột

- `window_no` (1..50): các dòng cùng `window_no` thuộc cùng một cảnh báo tại `(alert_service, alert_pod, window_start)` với điểm `anomaly_score` và 3 metric lệch mạnh nhất ở `top_features`. Nên đọc lướt toàn bộ sự kiện của một `window_no` rồi chấm từng dòng.
- `seconds_from_window_start`: độ lệch thời gian (giây) của sự kiện so với đầu cửa sổ cảnh báo (`[0, 60]` là nằm ngay trong cửa sổ 1 phút; âm là trước cửa sổ).
- Không sửa/xóa dòng hay đổi tên cột; lưu lại đúng định dạng CSV UTF-8. Nếu có người chấm thứ hai, giao độc lập 10 cửa sổ đầu (`window_no` 1..10, tức 20% mẫu) trên bản sao của file mù để tính hệ số đồng thuận Cohen's κ.
