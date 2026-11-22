# Mẫu mail gửi GVHD — kết quả cổng chặn G-test trên tập `test` (M8)

> Soạn 2026-11-16 theo quy định tại `04-implementation-roadmap.md` §10 ("Sau M3, M8, M10: gửi GVHD bản tóm tắt 1 trang
> lấy từ báo cáo mốc"). **Chưa gửi.**
> Có thể đính kèm `docs/milestones/M8-g-test.md` và `docs/drafts/ch5-ket-qua-test.md` (xuất PDF).
> Số liệu đối chiếu từ `docs/experiment-log.md` QĐ-034..038 và `eval/results/m8_test_tables_v1/`.

---

**Tiêu đề:** [CO5107] Báo cáo kết quả thực nghiệm một lần trên tập `test` (cổng G-test, mốc M8) và kế hoạch sang phần tác tử RCA

Kính gửi Cô Võ Thị Ngọc Châu,

Em là Nguyễn Văn Hoàng Khang. Tiếp theo báo cáo sau khi chốt cấu hình trên tập `val` và đăng ký trước các giả thuyết H0–H5 (ngày 14/11), em đã hoàn tất toàn bộ lượt chạy một lần duy nhất trên tập `test` độc lập (46.849 cửa sổ, trong đó 11.985 cửa sổ có log/trace với 346 cửa sổ sự cố; 13.699 cảnh báo từ detector, 0 lỗi API). Em xin tóm tắt kết quả chính thức của phần thẩm định cảnh báo (CTAV) để báo cáo Cô ạ.

**1. Kết quả kiểm định trên tập `test` (chỉ số chính: cửa sổ có log/trace)**

| Phương pháp | TP | FP | Precision | Recall [CI 95%] | F1 [CI 95%] | FPR [CI 95%] |
|---|---:|---:|---:|---|---|---|
| Chỉ detector (IForest) | 224 | 3.435 | 0,061 | 0,647 [0,601; 0,699] | 0,112 [0,100; 0,126] | 0,2951 [0,2870; 0,3036] |
| LLM không dùng RAG | 37 | 371 | 0,091 | 0,107 [0,077; 0,139] | 0,098 [0,071; 0,126] | 0,0319 [0,0288; 0,0351] |
| BM25 + Judge | 34 | 369 | 0,084 | 0,098 [0,070; 0,130] | 0,091 [0,064; 0,119] | 0,0317 [0,0285; 0,0350] |
| Topology chưa hiệu chỉnh (C1) | 96 | 1.235 | 0,072 | 0,277 [0,230; 0,321] | 0,114 [0,093; 0,135] | 0,1061 [0,1007; 0,1118] |
| **CTAV đóng băng** (C1 + C3 ngưỡng tĩnh `dev`) | **14** | **64** | **0,179** | **0,040 [0,022; 0,061]** | **0,066 [0,036; 0,100]** | **0,0055 [0,0042; 0,0069]** |
| *Biến thể H3 đã đăng ký:* **CTAV dùng C3 ngưỡng trượt 60 phút** | **47** | **391** | **0,107** | **0,136 [0,101; 0,172]** | **0,120 [0,090; 0,151]** | **0,0336 [0,0304; 0,0369]** |

Đối chiếu nguyên văn với các tiêu chí đã đăng ký trước khi chạm `test`:
- **H0 (vấn đề của bài báo gốc) — Được chấp nhận (đạt cả 4/4 vế):** So với BM25, truy xuất topology chưa hiệu chỉnh (C1) bắt thêm 62 sự cố (`ΔRecall = +0,179`, `p < 0,001`) nhưng sinh thêm 866 báo động giả (`ΔFPR = +0,0744`, tăng gấp 3,3 lần, `p < 0,001`), khiến F1 không tăng có ý nghĩa thống kê.
- **H2 (giả thuyết chính, cấu hình CTAV đóng băng) — Không được chấp nhận:** CTAV đạt rất mạnh vế giảm báo động giả (`ΔFPR = −0,0262` so với BM25, cắt 94,8% FP của C1 và tăng gấp đôi precision lên `0,179`), nhưng làm rơi quá nhiều TP (từ 96 xuống 14 TP), nên không đạt vế F1 (`ΔF1 = −0,025 [−0,067; +0,014]`) và vế giữ recall.
- **H3 (đóng góp thành phần) & H4 (ngân sách nhỏ 120 lần gọi) — Đều đạt:** Bỏ C3 làm precision tụt `−0,107`; thêm lại C2 (gating) và C4 (định tuyến 2 tầng) đều không cải thiện kết quả mà C4 còn tốn thêm chi phí; cổng Rescue (C5) chỉ thêm `+0 TP, +1 FP`; ở ngân sách nhỏ 120 lần gọi, CTAV đạt F1 `0,034` (6 TP, 0 FP) so với `0,017` của không-RAG. Độ lặp lại qua 3 lần gọi độc lập của judge đạt 99,0–99,5%.

**2. Nguyên nhân kỹ thuật rõ ràng của kết quả H2 (điểm đóng góp phân tích cho luận văn)**

Phân tích tách nhóm đã chuẩn bị trước (Phát hiện 11) chỉ ra chính xác lý do CTAV đóng băng mất recall trên `test`: do dữ liệu được chia theo từng đợt tiêm lỗi để chống rò rỉ, trên `test` có tới **32/42 service (chiếm 61,0% số cửa sổ sự cố)** chưa từng xuất hiện đủ dữ liệu bình thường trong tập `dev` nhỏ ban đầu để ước lượng ngưỡng độ trễ p90 tĩnh. Trên nhóm 32 service này, luật C3 tĩnh hạ trắng cả **67/67 sự cố** mà C1 đã bắt được về 0.

Khi thay **duy nhất** nguồn ngưỡng của C3 sang **ngưỡng trượt 60 phút ngay trước cảnh báo** (biến thể `C3-trượt` đã đăng ký sẵn trong H3, nâng độ phủ span từ 16,1% lên 91,2%), hệ thống đạt **47 TP, 391 FP, F1 = 0,120** (`ΔF1 = +0,054 [+0,017; +0,091]` so với CTAV tĩnh): giữ được nhiều hơn BM25 38% số sự cố (47 so với 34 TP), cắt được 68,3% báo động giả của C1 (đưa FPR `0,0336` về ngang BM25 `0,0317`), và đạt F1 cao nhất trên `test`.

**3. Hướng trình bày trong luận văn và bước tiếp theo (M9–M10)**

1. **Giữ nghiêm ngặt tính trung thực thực nghiệm:** Trong luận văn, em giữ nguyên kết luận **"H2 không được chấp nhận trên cấu hình đóng băng"** đúng như cam kết tiền đăng ký (không sửa hậu nghiệm cấu hình chính sau khi xem `test`), sau đó dùng phép đối chứng đã đăng ký `C3-trượt` để chứng minh nguyên lý neo bằng chứng tại service gốc là hiệu quả nhưng bắt buộc phải đi kèm ngưỡng nền thích nghi (rolling baseline) thay vì ngưỡng tĩnh khi triển khai qua các tập dịch vụ biến động.
2. **Chuyển sang M9 (Tác tử RCA — H5) và M10 (Platform Demo):** Em bắt đầu triển khai gom cụm cảnh báo (grouping), truy vết lan truyền ngược 1-hop và sinh báo cáo sự cố có cấu trúc. Ở bước kiểm định H5 trên `test`, em dự kiến báo chỉ số chính trên đúng đầu ra CTAV đã đăng ký (78 cảnh báo) và báo kèm một dòng độ nhạy trên đầu ra `C3-trượt` (438 cảnh báo) để đánh giá đầy đủ trên cả các service thiếu ngưỡng `dev`.

Em gửi kèm báo cáo chi tiết cột mốc M8 và bản nháp Chương 5 (§5.7–§5.8) để Cô tiện xem khi cần ạ. Em rất mong nhận được ý kiến góp ý của Cô về cách đóng khung kết quả H2 và phần đánh giá H5 như trên.

Em cảm ơn Cô nhiều ạ.

Trân trọng,  
Nguyễn Văn Hoàng Khang
