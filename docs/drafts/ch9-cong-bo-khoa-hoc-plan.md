# Kế hoạch Chương 9 — Công bố khoa học

> Nguồn: bản bài báo `ICAETM2026_Track4_386_TopologyGuidedAlertValidation_Revised (2).pdf` (6 trang), outline
> `outline-bao-cao-gd2.md` (Chương 9), style guide §1.2 và §3.1. Soạn 2026-11-22.

## 1. Ràng buộc

- Chương có số (Chương 9), nằm ngay sau Chương 8. Dài khoảng 1 trang, không có Kết chương, không có hình.
- Bài báo là **khảo sát thực nghiệm bước đầu** cho riêng khâu truy xuất, chạy trên `paper_500`. Nó không phải trục so sánh
  của luận văn.
- **Không lặp số** của bài báo. Số của bài báo chỉ xuất hiện ở §1.1.2 và ở mục G-paper (§5.5.2).
- 9.1 phải ghi **trạng thái thật** của bài: đã nộp / được chấp nhận / đã đăng. Trích dẫn theo chuẩn IEEE.
- File LaTeX: `Sections/Ch9_CongBoKhoaHoc.tex`, nhãn `\label{ch:cong-bo}`, `\input` sau Ch8 trong `main.tex`.

## 2. Thông tin cần người dùng xác nhận trước khi viết

| Mục | Đọc được từ bản PDF | Cần xác nhận |
|---|---|---|
| Tên bài | *Topology-Guided Evidence Retrieval for Cost-Aware LLM Alert Validation in Microservices* | Tên chính thức sau vòng sửa |
| Tác giả | Khang Van Hoang Nguyen (tác giả liên hệ), Chau Thi Ngoc Vo, cùng khoa KH&KT Máy tính, HCMUT | Thứ tự tác giả và vai trò (GVHD?) |
| Hội nghị | ICAETM 2026, Track 4, mã bài 386 | Tên đầy đủ, nơi và thời gian tổ chức |
| Kỷ yếu / nhà xuất bản | Không có trong bản PDF | Nhà xuất bản (`main.tex` đang ghi "Atlantis Press / Springer Nature", chưa có nguồn xác nhận) |
| Trạng thái | Tên file có "Revised (2)", nghĩa là đã qua ít nhất một vòng sửa | **Đã nộp bản sửa / được chấp nhận / đã đăng**, kèm ngày |
| DOI, số trang | Chưa có | Nếu đã đăng |
| Mã nguồn | Link `anonymous.4open.science` (bản ẩn danh để phản biện) | Có công khai repo thật sau khi được chấp nhận không |

## 3. Sai lệch cần sửa ngay ở chỗ khác

1. **`\bibitem{icaetm2026}` trong `main.tex`** đang ghi tên bài là "Topology-*Aware* Evidence Retrieval…", trong khi bản PDF
   ghi "Topology-*Guided*…". Bibitem cũng thiếu đồng tác giả Võ Thị Ngọc Châu và ghi nhà xuất bản khi chưa có nguồn xác
   nhận. Sửa sau khi có thông tin ở mục 2.
2. **Ch3 dòng 68** viết rằng báo động giả tăng "do bộ thẩm định dễ diễn giải nhầm log nền từ láng giềng". Câu này mâu thuẫn
   với Phát hiện 7 và H1 của luận văn: nguyên nhân là trace **cục bộ** sát thời điểm cảnh báo, không phải bằng chứng từ
   láng giềng. Chính bài báo cũng chỉ viết thận trọng: "consistent with confirmation bias", "does not isolate…". Nên sửa
   câu ở Ch3 cho đúng điều bài báo thật sự khẳng định.

## 4. Dàn ý

### 9.1 Bài báo đã công bố (~½ trang)

- Một đoạn thông tin: tác giả, tên bài, hội nghị, track, kỷ yếu, trạng thái thật kèm ngày, và trích dẫn `\cite{icaetm2026}`.
- Một đoạn nội dung bài, viết định tính, **không có số**:
  - Pipeline gồm detector nhẹ, tầng truy xuất bằng chứng log và trace, rồi judge LLM có lược đồ JSON cố định.
  - Đóng góp chính là Fusion Score, kết hợp BM25, độ gần thời gian và độ gần trên đồ thị gọi.
  - Đánh giá có cả cửa sổ bình thường, và theo dõi số lần gọi API cùng chi phí.
  - Phát hiện chính: topology tăng recall, nhất là với lỗi lan truyền `network_delay`, nhưng cũng tăng mạnh báo động giả
    trên cửa sổ bình thường.
  - Bài kết luận rằng truy xuất và chính sách quyết định phải được thiết kế cùng nhau.

### 9.2 Quan hệ với luận văn (~½ trang)

**Đoạn 1 — Luận văn dùng bài báo ở đâu.** Mỗi chỗ một vế câu:

- §1.1.2: hiện tượng xuất phát (đánh đổi recall và báo động giả).
- Chương 3: một công trình liên quan trong bảng so sánh.
- Chương 4: công thức và trọng số Fusion Score của C1 lấy từ bài, khóa cache tương thích.
- §5.5.2 (G-paper): kiểm chứng pipeline tái lập đúng baseline đã công bố, toàn bộ từ cache.

**Đoạn 2 — Luận văn đi xa hơn ở đâu.** Có thể đặt thành bảng nhỏ ba cột: điểm mở của bài báo → luận văn xử lý ở đâu → kết
cục. Bảng không có số.

| Điểm mở của bài báo | Luận văn | Kết cục |
|---|---|---|
| Future Scope (1): ngưỡng tin cậy bất đối xứng cho bằng chứng xa | C2 (gating theo nguồn bằng chứng) | Đã loại sau ablation H3 |
| Future Scope (2): Causal Span Grounding | C3 (neo bằng chứng, bản rút gọn: span phải vượt ngưỡng nền) | Đang dùng, đóng góp chính |
| Future Scope (3): định tuyến nhiều tầng thích nghi | C4 (định tuyến hai tầng) | Đã loại vì chi phí |
| Thiên lệch xác nhận mới là giả thuyết, chưa cô lập | Thí nghiệm can thiệp H1 | Nguyên nhân là trace cục bộ, không phải bằng chứng xa |
| Một lượt chạy; `paper_500` chưa hoàn toàn chưa nhìn; truy vấn BM25 lộ thẻ loại lỗi | Split dev/val/test theo đợt tiêm lỗi, đăng ký trước, chạy lặp, xoá thẻ kèm kiểm thử | Kiểm định một lần trên `test` |
| Chỉ thẩm định cảnh báo, không định vị nguyên nhân gốc | Tác tử RCA (H5) và platform | H5 không được chấp nhận; platform chạy được |

**Đoạn 3 — Một điểm đổi hướng có ghi lại** (style guide §1.3). Bài báo gợi ý dùng ngưỡng chặt hơn cho bằng chứng *xa*. Luận
văn kiểm giả thuyết đó và thấy nó không đúng: báo động giả đến từ bằng chứng *cục bộ*. Vì vậy trục thiết kế chuyển từ C2
sang C3. Viết thẳng điều này, kèm tham chiếu Mục 5.x (H1) và Mục 7.2.

## 5. Kiểm tra trước khi đóng chương

- [ ] Không có con số nào của bài báo trong Chương 9.
- [ ] Không mở mục hay câu bằng "so với bài báo"; bài báo được trích như mọi công trình khác.
- [ ] Trạng thái bài là trạng thái thật lúc nộp luận văn, kèm ngày.
- [ ] Bibitem đã khớp tên bài, đủ tác giả, nhà xuất bản đã xác nhận, đúng chuẩn IEEE.
- [ ] Không dùng "giai đoạn", "kế thừa từ", "phiên bản trước" (style guide §1.1).
- [ ] Lần đầu nhắc C2, C3, C4 trong chương có kèm chức năng.
- [ ] Rebuild PDF; không còn tham chiếu "??".

## 6. Thứ tự làm

1. Người dùng xác nhận các mục ở bảng 2.
2. Sửa bibitem và câu ở Ch3 dòng 68.
3. Viết `Ch9_CongBoKhoaHoc.tex` theo mục 4, rồi thêm `\input` vào `main.tex` sau Ch8.
4. Rebuild và chạy checklist ở mục 5.
