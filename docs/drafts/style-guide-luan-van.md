# Quy tắc viết luận văn (style guide)

> Áp dụng cho **mọi** văn bản đi vào luận văn: sườn (`suon-bao-cao-gd2.md`), outline (`outline-bao-cao-gd2.md`),
> nháp chương (`docs/drafts/ch*.md`) và file LaTeX. Đây là nguồn duy nhất của quy tắc văn phong. File khác chỉ trỏ
> về đây, không chép lại. Ghi chú nội bộ (bảng trạng thái, ký hiệu ♻️ ⏳ ✍️, mã QĐ, mốc M*) không phải văn luận văn
> và không chịu §1.1, nhưng khi chuyển thành văn thì phải viết lại theo file này.
>
> Soạn 2026-11-16 từ hướng dẫn của người dùng; gộp §3 cũ của `outline-bao-cao-gd2.md`.

---

## 1. Định vị công trình

### 1.1 Một đề tài thống nhất

- Luận văn trình bày **một** hệ AIOps khép kín, theo đúng thứ tự xử lý: phát hiện bất thường chuỗi thời gian
  (Isolation Forest, kèm luật Rescue) → thẩm định cảnh báo hiệu chỉnh theo bằng chứng đa nguồn (CTAV) → tác tử phân
  tích nguyên nhân gốc (RCA) → platform trực quan hoá.
- **Cấm** trong văn luận văn: "giai đoạn 1/2/3", "GĐ1", "GĐ2", "Phase", "kế thừa từ", "mở rộng từ báo cáo trước",
  "phiên bản trước của hệ thống".
- Phần hướng phát triển (Chương 7) gọi là "hướng phát triển", không gọi là "giai đoạn tiếp theo".
- Kiểm tra tính đúng của pipeline (G-port, G-paper) viết như một bước kiểm chứng kỹ thuật: pipeline tái lập đúng
  baseline đã công bố. Không viết là "pipeline mới khớp pipeline cũ".

### 1.2 Vị trí của bài báo ICAETM 2026

- Bài báo là **khảo sát thực nghiệm bước đầu** của tác giả, chỉ cho khâu truy xuất ngữ cảnh, trên tập mẫu nhỏ
  (`paper\_500`). Trích dẫn như mọi công trình khác: `\cite{...}` kèm một câu nói nó cho thấy gì và giới hạn ở đâu.
- Bài báo là tiền đề thực nghiệm, **không** là trục tham chiếu. Không mở mục, chương hay bảng bằng "so với bài báo".
- Số của bài báo chỉ xuất hiện ở hai chỗ: §1.1 (hiện tượng xuất phát) và mục kiểm tra tính đúng của pipeline
  (Chương 5). Ở mọi chỗ khác, baseline là BM25 chạy trong chính luận văn.

### 1.3 Hai nguyên tắc trung thực (sợi chỉ đỏ)

1. **Đổi hướng có ghi lại.** Trên `val`, hiện tượng "truy xuất đồ thị tăng cả recall lẫn báo động giả" lặp lại, nhưng
   cơ chế "nhiễu từ service lân cận" thì không. Nguyên nhân thực chất là thiên lệch xác nhận trên bằng chứng cục bộ sát
   thời điểm cảnh báo. Viết thẳng ở Chương 1, 4, 5, không giấu và không viết như thể đã biết từ đầu.
2. **Kết quả âm cũng là kết quả.** C2 (gating theo nguồn bằng chứng) và C4 (định tuyến hai tầng) bị loại sau
   ablation. C5 (Rescue Score) không đóng góp đáng kể. CTAV giảm mạnh báo động giả nhưng không giữ được recall của C1.
   Mỗi điều viết như một thiết kế đã kiểm chứng và loại có cơ sở, có số đi kèm.

---

## 2. Giọng văn và cấu trúc

### 2.1 Văn phong

- Kỹ thuật, trực diện: vấn đề → cơ chế → bằng chứng.
- **Từ cấm** (quảng bá hoặc sáo rỗng): đột phá, vượt trội, quan trọng bậc nhất, then chốt (khi không có số),
  hoàn hảo, giải quyết triệt để, đáng kinh ngạc, hiện đại nhất / state-of-the-art, "đáng chú ý là", "Crucial finding".
  "Lần đầu tiên" chỉ dùng khi đã kiểm tài liệu và có trích dẫn chứng minh.
- "Có ý nghĩa" chỉ dùng theo nghĩa thống kê, kèm kiểm định và mức ý nghĩa.
- Nhịp câu: xen câu ngắn dứt khoát (khoảng 8–14 từ) với câu phân tích dài hơn (khoảng 18–25 từ). Không để ba câu liền
  nhau cùng độ dài hoặc cùng khuôn ("X giúp Y. Z giúp W."). Đây là hướng dẫn, không phải chỉ tiêu đếm từ.

### 2.2 Khung chương, mục, đoạn

- Mỗi chương mở bằng một đoạn dẫn 4–6 câu: chương trả lời câu hỏi gì, gồm những mục nào.
- Mỗi chương (trừ Chương 8) kết bằng mục **"Tóm tắt chương"** 5–8 câu, không thêm ý mới.
- Mỗi mục cấp 2 mở bằng một câu chủ đề nói mục này để làm gì.
- Một đoạn một ý trọn vẹn, khoảng 4–7 câu.

### 2.3 Thuật ngữ

- Giữ tiếng Anh: `microservice`, `metric`, `log`, `trace`, `candidate`, `judge`, `topology`, `pipeline`, `cache`,
  `split`, `baseline`, `ablation`, `TRUE\_ALERT`, `NORMAL`.
- Tên tiếng Việt cố định: "cửa sổ", "cảnh báo", "bằng chứng", "cửa sổ có telemetry".
- Lần đầu xuất hiện thì giải thích, sau đó không đổi cách gọi.
- Lần đầu nhắc ký hiệu thành phần **trong mỗi chương** phải kèm chức năng:
  C1 (truy xuất lai BM25–topology), C2 (gating theo nguồn bằng chứng), C3 (neo bằng chứng),
  C4 (định tuyến hai tầng), C5 (Rescue Score).

---

## 3. Khuôn mẫu theo chương

| Chương | Khuôn |
|---|---|
| 1 Giới thiệu | Hình phễu: bối cảnh rộng → bài toán hẹp. Trực giác, động lực, kiến trúc tổng quan. **Không công thức, không CI, không số thập phân.** Được dùng số đếm (ví dụ số FP) hoặc tỷ lệ làm tròn; kết quả chính của luận văn viết định tính hoặc làm tròn. |
| 2 Cơ sở lý thuyết | Mỗi khái niệm 4 bước: (1) định nghĩa → (2) công thức hoặc sơ đồ → (3) một ví dụ nhỏ trên dữ liệu Nezha → (4) một câu chỉ rõ luận văn dùng nó ở đâu (trỏ sang Chương 4). Không kết quả thực nghiệm. |
| 3 Công trình liên quan | Khoảng một đoạn mỗi công trình, 3 bước: (1) họ làm gì → (2) giới hạn liên quan đến đề tài → (3) luận văn khác ở đâu. Chốt chương bằng bảng so sánh và khoảng trống nghiên cứu. |
| 4 Phương pháp | Mỗi thành phần 5 bước: (1) vấn đề giải quyết → (2) thiết kế (công thức/luật) → (3) tham số và cách chọn → (4) vai trò hiện tại (đang dùng / đã bỏ / chỉ là ablation) → (5) dẫn chiếu mục Chương 5 chứa bằng chứng. C2, C4 viết gọn hơn nhưng không lược. Số `val` chỉ để giải thích một lựa chọn, mỗi chỗ một câu. **Không số `test`.** |
| 5 Thực nghiệm | Mỗi mục kiểm định giả thuyết theo 6 bước ở §3.1. |
| 6 Platform | Theo mắt người vận hành, không theo mã nguồn. Mỗi màn hình: ảnh chụp, một đoạn "màn hình trả lời câu hỏi gì", một đoạn nối với thành phần ở Chương 4. Kịch bản demo là bảng từng bước. |
| 7 Thảo luận | Không lặp bảng của Chương 5; mỗi luận điểm trích 1–2 con số then chốt rồi giải thích nguyên nhân. Hạn chế viết cụ thể (cái gì, ảnh hưởng kết luận nào). Mỗi hướng phát triển gắn với một hạn chế. |
| 8 Kết luận | Không ý mới, không hình. Mỗi câu hỏi nghiên cứu một đoạn 3–4 câu: câu trả lời, số chính, giới hạn. |

### 3.1 Sáu bước cho một mục kiểm định (Chương 5)

1. **Câu hỏi và tiêu chí chấp nhận**: chép nguyên văn tiêu chí đã đăng ký (cuối `docs/experiment-log.md`, commit `be2b985`).
2. **Bảng số đo** và **bảng đối chiếu từng vế** của tiêu chí (đạt / không đạt).
3. **Một câu kết luận in đậm**, chỉ dùng một trong ba cụm: **"được chấp nhận"**, **"không được chấp nhận"**,
   **"đạt một phần"**. "Đạt một phần" chỉ dùng cho giả thuyết đã đăng ký có nhiều vế (H1, H2, H5) và phải nói rõ vế
   nào đạt, vế nào không.
4. **Diễn giải bằng số đếm** (`TP`, `FP`, số cửa sổ), không chỉ nêu hiệu $\Delta$.
5. **Đối chiếu với `val`**: hiện tượng có lặp lại không, biên độ ra sao.
6. **Điều kiện đọc kết quả và giới hạn** (nếu có).

Áp dụng: H0, H2, H3, H4 trên `test`; H5 trên incident của `test`. H1 chỉ chạy trên mẫu cố định của `val`, nên bước 5
thay bằng một câu nêu phạm vi (mẫu, split) và nói rõ H1 không được kiểm lại trên `test`. Kiểm tra tính đúng của
pipeline (G-port, G-paper) không phải kiểm định giả thuyết; viết theo bước 2, 4, 6.

---

## 4. Kỷ luật số liệu

- Dấu phẩy thập phân: `0,201`; khoảng: `+0,179 [+0,138; +0,226]`; `p < 0,001`.
- Mỗi con số ghi rõ split (`dev`, `val`, `test`) và tập cửa sổ (mặc định: cửa sổ có telemetry). Không trộn số `val`
  và `test` trong một câu mà không nói rõ. `dev`/`val` là số để chọn cấu hình ("trên `val`"); chỉ `test` là kết quả
  kiểm định.
- Hiệu giữa hai phương pháp luôn kèm CI 95% bootstrap. **Không** viết "tốt hơn", "cao hơn rõ", "cải thiện" khi CI
  chứa 0. Viết: "chênh lệch +0,0xx, CI chứa 0, chưa đủ bằng chứng để khẳng định khác biệt".
- Số mock (judge mock) không dùng làm kết luận; nếu nhắc thì ghi rõ "judge mock".
- Chỗ chưa có số ghi `[CHỜ M8]`, `[CHỜ M9]`, `[CHỜ M10]`, `[CHỜ M11]` đúng mốc. Không để trống, không ước lượng.
  Câu kết luận phụ thuộc số chưa có thì viết khung câu và đánh dấu cả câu, ví dụ
  `[CHỜ M9: H5 được chấp nhận / đạt một phần / không được chấp nhận]`.

---

## 5. Hình, bảng và LaTeX

### 5.1 Hình và bảng

- Mỗi hình, bảng được nhắc trong văn **trước** khi xuất hiện, kèm ít nhất một câu nói người đọc cần nhìn vào đâu.
- Caption bảng **trên** bảng; caption hình **dưới** hình. Caption tự đủ nghĩa: split, tập cửa sổ, `run\_id` nếu là kết quả chạy.
- Sơ đồ (kiến trúc, luồng): một bộ màu và kiểu khối thống nhất cả luận văn.
- Biểu đồ số liệu: sinh bằng script đọc thẳng `eval/results/`, không nhập số tay.
- Ảnh chụp, ví dụ prompt, ca cụ thể: lấy từ hệ thống chạy thật.
- Bảng dài hơn nửa trang hoặc chỉ để tra cứu (theo service, cấu hình đầy đủ) đưa vào phụ lục.

### 5.2 Quy chuẩn LaTeX

- Tên biến nhiều chữ cái trong môi trường toán bọc `\mathrm{}`: `\mathrm{GraphSim}`, `\mathrm{BM25}`,
  `\mathrm{Recall}`; dùng `\exp`, `\max`, `\min`, `\log`.
- Định danh code hoặc chuỗi có gạch dưới bọc `\texttt{}` và thoát `\_`: `\texttt{network\_delay}`,
  `\texttt{paper\_500}`, `\texttt{TRUE\_ALERT}`, `\texttt{ctav\_final}`.
- Dấu phẩy thập phân **trong môi trường toán** phải viết `0{,}201` (hoặc nạp gói `icomma`); nếu không, LaTeX chèn
  khoảng trắng sau dấu phẩy. Ngoài môi trường toán viết bình thường `0,201`.
- Tham chiếu chéo luôn qua `\label`/`\ref` (`\ref{tab:h0-test}`, `\ref{sec:ctav-c3}`), không gõ số mục bằng tay.
- Không để lại ký hiệu do công cụ sinh văn bản chèn vào (ví dụ `[cite: 4]`, `【…】`). Mọi trích dẫn đi qua `\cite{}`.

---

## 6. Checklist trước khi coi một mục là xong

- [ ] Không có từ ở §1.1 (giai đoạn, GĐ, kế thừa…) và §2.1 (từ cấm).
- [ ] Bài báo ICAETM chỉ xuất hiện như trích dẫn, không làm trục so sánh.
- [ ] Mọi con số có split và tập cửa sổ; mọi hiệu có CI; không "tốt hơn" khi CI chứa 0.
- [ ] C2/C4/C5 và giới hạn recall của CTAV được nêu ở đúng chỗ, không né.
- [ ] Hình/bảng được nhắc trước, caption đúng vị trí và tự đủ nghĩa.
- [ ] Chỗ chưa có số đã gắn `[CHỜ M*]`; không còn `[cite: …]`.
