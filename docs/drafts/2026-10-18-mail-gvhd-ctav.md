# Mẫu mail gửi GVHD — định hướng Giai đoạn 2 (CTAV)

> **Đã thay thế** bởi `2026-10-19-mail-gvhd-ctav.md` (thêm kết quả tái lập bài báo, Phát hiện 1–4, judge `gemini-2.5-flash`). Giữ lại để đối chiếu, không gửi bản này.

> Soạn 2026-10-18. Chưa gửi. Đổi xưng hô "Thầy/Cô" cho phù hợp trước khi gửi.
> Có thể đính kèm `docs/Final_Thesis_Phase2/08-research-direction.md` (xuất PDF).

---

**Tiêu đề:** [CO5107] Báo cáo định hướng Giai đoạn 2: giải pháp CTAV và kế hoạch chứng minh

Kính gửi Thầy/Cô Võ Thị Ngọc Châu,

Em là Nguyễn Văn Hoàng Khang. Theo góp ý của Thầy/Cô là Giai đoạn 2 phải đưa ra một giải pháp và chứng minh được giải pháp đó, không chỉ dừng ở thực nghiệm như Giai đoạn 1, em đã điều chỉnh lại hướng làm. Em xin tóm tắt như sau:

**1. Vấn đề**

Bài báo ICAETM 2026 của em (bản đã sửa theo phản biện) đánh giá trên 500 cửa sổ dữ liệu Nezha. Kết quả cho thấy khi đưa topology của call-graph vào bước truy xuất bằng chứng, LLM tìm được nhiều lỗi hơn:
- Recall tăng từ 0.58 lên 0.74.
- Riêng lỗi network_delay, recall tăng từ 0.375 lên 0.70.

Nhưng LLM cũng đọc telemetry bình thường của các service lân cận thành lỗi lan truyền:
- Báo động giả trên 400 cửa sổ bình thường tăng từ 7 lên 137.
- F1 giảm từ 0.70 xuống 0.48 (McNemar p ≈ 10⁻¹⁹).
- Chi phí API tăng 2,7 lần.

Nói ngắn gọn: service nằm gần trên đồ thị không có nghĩa là nguyên nhân gây lỗi.

**2. Giải pháp: CTAV (Calibrated Topology-Aware Alert Validation)**

CTAV giữ lại phần recall tăng thêm nhờ topology, đồng thời chặn báo động giả bằng cách hiệu chỉnh quyết định theo nguồn gốc của bằng chứng. Phương pháp gồm 4 thành phần:
- **C1:** Fusion Score có topology, tức phương pháp của bài báo: α·BM25 + β·độ gần thời gian + γ·độ gần trên đồ thị.
- **C2:** Ngưỡng tin cậy bất đối xứng. Kết luận dựa trên bằng chứng lấy qua đồ thị phải đạt ngưỡng cao hơn kết luận dựa trên bằng chứng cục bộ.
- **C3:** Neo bằng chứng. Chỉ xác nhận cảnh báo khi có bằng chứng tại chính service bị cảnh báo, hoặc trên đường gọi có lỗi/chậm dẫn tới service đó.
- **C4:** Định tuyến hai tầng. Chạy BM25 trước, chỉ mở rộng theo topology khi chưa đủ căn cứ kết luận, để giảm chi phí.

Kết quả thẩm định của CTAV sẽ là đầu vào cho tác tử RCA: gom các cảnh báo thành sự cố, truy ngược để tìm service gốc, rồi sinh báo cáo JSON có bằng chứng. Nezha có nhãn root-cause ở mức pod nên đánh giá được bằng Hit@1 và Hit@3.

**3. Cách chứng minh**

- **Viết giả thuyết trước khi chạy:** em ghi sẵn các giả thuyết H0–H5 cùng tiêu chí bác bỏ, trước khi chạy trên tập test.
  - H0: tái lập được vấn đề của bài báo trên split mới.
  - H1: báo động giả tăng theo tỷ lệ bằng chứng lấy từ service xa.
  - H2: CTAV có F1 cao hơn BM25 một cách có ý nghĩa thống kê.
  - H3: bỏ đi bất kỳ thành phần nào thì kết quả đều xấu đi.
  - H4: trong ngân sách gọi LLM giới hạn, CTAV không thua LLM không dùng RAG.
  - H5: tác tử RCA đạt Hit@1 ≥ 0.60 và Hit@3 ≥ 0.80.
- **Tách dữ liệu nghiêm ngặt:** chỉ tinh chỉnh tham số trên tập val. Tập test chỉ chạy một lần.
- **Kiểm định thống kê:** dùng bootstrap CI và McNemar test.

**4. Đầu ra Giai đoạn 2**

- Luận văn theo mạch: vấn đề (từ bài báo) → giải pháp CTAV và tác tử RCA → chứng minh H0–H5.
- Platform chạy được để demo trước hội đồng: replay dữ liệu, chạy CTAV và tác tử RCA, hiển thị trên dashboard 4 màn hình. Platform chạy offline được từ cache.
- Bảng kết quả trên tập test có kiểm định thống kê, các ablation, đánh giá chất lượng chẩn đoán bằng người trên 30 sự cố, kèm số liệu chi phí và độ trễ.
- Mã nguồn công khai, người khác chạy lại được.

**5. Thay đổi so với kế hoạch trước**

- Em bỏ hướng "so sánh 5 biến thể RAG" vì hướng đó vẫn chỉ là thực nghiệm.
- Phần LLM em dùng cố định một model API là gemini-2.5-flash-lite, không chạy LLM local. Có ba lý do:
  - Judge cần là biến cố định để so sánh có kiểm soát.
  - Định tuyến local trước, API sau làm model chấm từng cảnh báo thay đổi theo lỗi/timeout, nên kết quả khó tái lập. Ở Giai đoạn 1, 4/6 lần gọi đã phải chuyển sang API và độ trễ cao hơn khoảng 13 lần.
  - Máy em không đủ tài nguyên để chạy LLM local.

Kế hoạch được chia thành 13 cột mốc, có ba cổng kiểm tra tính đúng: tái lập Giai đoạn 1, tái lập bài báo, và chạy tập test. Dự kiến chốt kết quả trên tập test vào khoảng cuối tháng 12/2026.

**Em xin ý kiến Thầy/Cô về:**
1. Hướng CTAV như trên đã phù hợp với yêu cầu "đề xuất và chứng minh giải pháp" chưa ạ?
2. Việc dùng LLM API thay cho LLM local có chấp nhận được không ạ?
3. Em hiểu mốc bảo vệ là khoảng tuần 08/02/2027. Em hiểu như vậy có đúng không ạ?

Em có tài liệu chi tiết về giải pháp và lộ trình, nếu Thầy/Cô cần em sẽ gửi kèm.

Em cảm ơn Thầy/Cô.

Trân trọng,
Nguyễn Văn Hoàng Khang
