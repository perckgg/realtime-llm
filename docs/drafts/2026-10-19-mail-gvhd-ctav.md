# Mẫu mail gửi GVHD — định hướng Giai đoạn 2 (CTAV), bản cập nhật

> Soạn 2026-10-19, thay bản `2026-10-18-mail-gvhd-ctav.md`. **Chưa gửi.** Đổi xưng hô
> "Thầy/Cô" cho phù hợp trước khi gửi. Có thể đính kèm `docs/Final_Thesis_Phase2/08-research-direction.md`
> và `docs/milestones/M3-graph-c1-gpaper.md` (xuất PDF).
>
> Khác bản 2026-10-18: thêm mục 4 (kết quả tái lập bài báo và bốn phát hiện mới), đổi judge
> sang `gemini-2.5-flash`, thêm câu hỏi về biến thể C1 có dành chỗ cho bằng chứng lân cận.
> Số liệu: QĐ-016, QĐ-017, QĐ-020, QĐ-021 trong `docs/experiment-log.md`.

---

**Tiêu đề:** [CO5107] Báo cáo định hướng Giai đoạn 2: giải pháp CTAV, kết quả tái lập bài báo và xin ý kiến

Kính gửi Thầy/Cô Võ Thị Ngọc Châu,

Em là Nguyễn Văn Hoàng Khang. Theo góp ý của Thầy/Cô là Giai đoạn 2 phải đưa ra một giải pháp và chứng minh được giải pháp đó, không chỉ dừng ở thực nghiệm như Giai đoạn 1, em đã điều chỉnh lại hướng làm và đã chạy xong phần tái lập bài báo. Em xin tóm tắt như sau:

**1. Vấn đề**

Bài báo ICAETM 2026 của em đánh giá trên 500 cửa sổ dữ liệu Nezha. Khi đưa topology của call-graph vào bước truy xuất bằng chứng, LLM tìm được nhiều lỗi hơn (recall 0.58 → 0.74; network_delay 0.375 → 0.70), nhưng báo động giả trên 400 cửa sổ bình thường tăng từ 7 lên 137 và F1 giảm từ 0.70 xuống 0.48.

**2. Giải pháp: CTAV (Calibrated Topology-Aware Alert Validation)**

- **C1:** Fusion Score có topology (phương pháp của bài báo): α·BM25 + β·độ gần thời gian + γ·độ gần trên đồ thị.
- **C2:** Ngưỡng bất đối xứng theo nguồn gốc bằng chứng (cục bộ hay lấy qua đồ thị).
- **C3:** Neo bằng chứng: chỉ xác nhận khi có bằng chứng tại chính service bị cảnh báo hoặc trên đường gọi có lỗi/chậm tới service đó.
- **C4:** Định tuyến hai tầng: BM25 trước, chỉ mở rộng topology khi chưa đủ căn cứ.

Kết quả thẩm định là đầu vào cho tác tử RCA (gom sự cố, truy ngược service gốc, báo cáo JSON có bằng chứng), đánh giá bằng Hit@1/Hit@3.

**3. Cách chứng minh**

Giả thuyết H0–H5 và tiêu chí bác bỏ được viết trước; chỉ tinh chỉnh trên tập val, tập test chạy đúng một lần; bootstrap CI và McNemar test.

**4. Kết quả đến nay và bốn phát hiện mới**

Em đã viết lại pipeline và tái lập **chính xác** bảng kết quả chính của bài báo từ cache câu trả lời Gemini, không gọi API thêm (BM25: F1 0.703, 7 báo động giả; topology: F1 0.476, 137 báo động giả; cả 489 prompt của mỗi biến thể trùng từng byte). Trong quá trình tái lập, em phát hiện bốn điểm làm thay đổi cách hiểu kết quả của bài báo:

1. **Có bằng chứng gần như đồng nghĩa với gần sự cố.** Bộ Nezha chỉ có log/trace trong khoảng 300 phút quanh các lần tiêm lỗi, còn metric thì liên tục. Kho bằng chứng của bài báo còn được lọc theo nhãn lỗi. Kết quả: 95% cửa sổ bình thường của bài báo không có bằng chứng nào, và luật "xác nhận phải có bằng chứng" tự động loại chúng. Con số 7 báo động giả của BM25 chủ yếu đến từ đây.
2. **Bằng chứng của biến thể topology phần lớn lệch thời gian.** Phần BM25 của biến thể này tìm trên toàn bộ dữ liệu, không giới hạn thời gian: 80% bằng chứng nằm ngoài ±8 phút quanh cảnh báo (75% cách hơn 1 giờ), và 100% cửa sổ bình thường đều nhận được bằng chứng — phần lớn là log của sự cố ở thời điểm khác. Vì vậy 137 báo động giả có thể chủ yếu do bằng chứng lệch thời gian, chứ không hẳn do topology.
3. **Trên dữ liệu đầy đủ, công thức của bài báo không chọn bằng chứng lân cận.** Khi giới hạn bằng chứng trong ±8 phút và dùng toàn bộ log/trace, với trọng số của bài báo, không bằng chứng nào từ service lân cận lọt vào top-6 (0/196 truy vấn thử): điểm tối đa của một event lân cận (0.80) luôn thấp hơn điểm của event cục bộ thứ 6 (trung vị 0.84).
4. **Gemini thường chép điểm bất thường làm độ tin cậy** khi prompt không có bằng chứng (83% trường hợp), nên ngưỡng tin cậy (C2) không thể chỉ dựa vào con số này.

Em đã điều chỉnh giao thức như sau:
- Chỉ số chính tính trên các cửa sổ có telemetry (có log/trace trong ±8 phút); toàn bộ split là số phụ.
- C1 có giới hạn thời gian; phiên bản đúng như bài báo vẫn giữ để so sánh.
- Đề xuất thêm một biến thể C1 **dành sẵn một số chỗ (ví dụ 3/6) cho bằng chứng từ service lân cận**, xếp hạng bằng chính Fusion Score, làm tầng topology của CTAV. Nếu không có điều chỉnh này thì tầng topology sẽ trùng với tầng BM25.
- Judge là một model API cố định, nay nâng lên `gemini-2.5-flash` (cùng thế hệ với model của bài báo nhưng lớn hơn), temperature 0, không chạy LLM local. Bài báo vẫn được tái lập bằng cache của `gemini-2.5-flash-lite`.

**5. Đầu ra Giai đoạn 2**

Luận văn (vấn đề → CTAV và tác tử RCA → chứng minh H0–H5), platform chạy được để demo (chạy offline từ cache), bảng kết quả trên tập test có kiểm định thống kê, và mã nguồn công khai để người khác chạy lại được.

**Em xin ý kiến Thầy/Cô về:**
1. Hướng CTAV như trên đã phù hợp với yêu cầu "đề xuất và chứng minh giải pháp" chưa ạ?
2. Bốn phát hiện ở mục 4 cho thấy một phần vấn đề của bài báo đến từ giao thức đánh giá. Em dự định trình bày điều này trung thực trong chương Bài toán, và nếu trên dữ liệu mới vấn đề không còn tái lập được thì em sẽ báo cáo đúng như vậy. Thầy/Cô thấy cách làm này có ổn không ạ?
3. Việc thêm biến thể C1 dành chỗ cho bằng chứng lân cận có chấp nhận được không, hay em nên giữ đúng công thức của bài báo ạ?
4. Việc dùng một LLM API cố định (`gemini-2.5-flash`) thay cho LLM local có chấp nhận được không ạ?
5. Em hiểu mốc bảo vệ là khoảng tuần 08/02/2027. Em hiểu như vậy có đúng không ạ?

Em có tài liệu chi tiết và các báo cáo theo từng cột mốc, nếu Thầy/Cô cần em sẽ gửi kèm.

Em cảm ơn Thầy/Cô.

Trân trọng,
Nguyễn Văn Hoàng Khang
