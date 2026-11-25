# Quy tắc viết luận văn (style guide)

> Áp dụng cho **mọi** văn bản đi vào luận văn: sườn (`suon-bao-cao-gd2.md`), outline (`outline-bao-cao-gd2.md`),
> nháp chương (`docs/drafts/ch*.md`) và file LaTeX. Đây là nguồn duy nhất của quy tắc văn phong. File khác chỉ trỏ
> về đây, không chép lại. Ghi chú nội bộ (bảng trạng thái, ký hiệu ♻️ ⏳ ✍️, mã QĐ, mốc M*) không phải văn luận văn
> và không chịu §1.1, nhưng khi chuyển thành văn thì phải viết lại theo file này.
>
> Soạn 2026-11-16 từ hướng dẫn của người dùng; gộp §3 cũ của `outline-bao-cao-gd2.md`. Cập nhật cùng ngày: thuật ngữ
> "đa phương thức", bảng vai trò thành phần (§1.4), phần đầu/cuối (§3.1), khung LaTeX (§6), mục tiêu đã chốt (§7).
> Lịch viết: `ke-hoach-viet-bao-cao.md`.
>
> Cập nhật 2026-11-18 theo template GVHD (`outline-bao-cao-gd2.md` mục 9): cấu trúc 9 chương (§3), "Kết chương" đánh
> số (§2.2), Chương 9 Công bố khoa học (§3.1), tài liệu tham khảo IEEE (§3.1), khai báo AI hỗ trợ (§5.3).

---

## 1. Định vị công trình

### 1.1 Một đề tài thống nhất

- Luận văn trình bày **một** hệ AIOps khép kín, theo đúng thứ tự xử lý: phát hiện bất thường chuỗi thời gian
  (Isolation Forest, kèm luật Rescue) → thẩm định cảnh báo hiệu chỉnh theo bằng chứng đa phương thức (CTAV) → tác tử phân
  tích nguyên nhân gốc (RCA) → platform trực quan hoá.
- **Cấm** trong văn luận văn: "giai đoạn 1/2/3", "GĐ1", "GĐ2", "Phase", "kế thừa từ", "mở rộng từ báo cáo trước",
  "phiên bản trước của hệ thống".
- Phần hướng phát triển (§8.2) gọi là "hướng phát triển", không gọi là "giai đoạn tiếp theo".
- Kiểm tra tính đúng của pipeline (G-port, G-paper) viết như một bước kiểm chứng kỹ thuật: pipeline tái lập đúng
  baseline đã công bố. Không viết là "pipeline mới khớp pipeline cũ".

### 1.2 Vị trí của bài báo ICAETM 2026

- Bài báo là **khảo sát thực nghiệm bước đầu** của tác giả, chỉ cho khâu truy xuất ngữ cảnh, trên tập mẫu nhỏ
  (`paper\_500`). Trích dẫn như mọi công trình khác: `\cite{...}` kèm một câu nói nó cho thấy gì và giới hạn ở đâu.
- Bài báo là tiền đề thực nghiệm, **không** là trục tham chiếu. Không mở mục, chương hay bảng bằng "so với bài báo".
- Số của bài báo chỉ xuất hiện ở hai chỗ: §1.1 (hiện tượng xuất phát) và mục kiểm tra tính đúng của pipeline
  (Chương 5). Ở mọi chỗ khác, baseline là BM25 chạy trong chính luận văn.
- Chương 9 (Công bố khoa học) trình bày bài báo **như một công bố** của tác giả: thông tin bài, trạng thái thật, quan hệ
  với luận văn. Chương này không lặp số và không biến bài báo thành trục so sánh.

### 1.3 Hai nguyên tắc trung thực (sợi chỉ đỏ)

1. **Đổi hướng có ghi lại.** Trên `val`, hiện tượng "truy xuất đồ thị tăng cả recall lẫn báo động giả" lặp lại, nhưng
   cơ chế "nhiễu từ service lân cận" thì không. Nguyên nhân thực chất là thiên lệch xác nhận trên bằng chứng cục bộ sát
   thời điểm cảnh báo. Viết thẳng ở Chương 1, 4, 5, không giấu và không viết như thể đã biết từ đầu.
2. **Kết quả âm cũng là kết quả.** C2 (gating theo nguồn bằng chứng) và C4 (định tuyến hai tầng) bị loại sau
   ablation. C5 (Rescue Score) không đóng góp đáng kể. CTAV giảm mạnh báo động giả nhưng không giữ được recall của C1.
   Mỗi điều viết như một thiết kế đã kiểm chứng và loại có cơ sở, có số đi kèm.

### 1.4 Vai trò của từng thành phần (dùng đúng nhãn này ở mọi chương)

| Ký hiệu | Chức năng (ghi kèm ở lần đầu mỗi chương) | Vai trò | Quyết định |
|---|---|---|---|
| C1 | truy xuất lai BM25–topology (Fusion Score) | **đang dùng** | QĐ-031 |
| C2 | ngưỡng bất đối xứng theo nguồn bằng chứng | **đã loại** (ΔFPR CI chạm 0 trên `val`) | QĐ-031 |
| C3 | neo bằng chứng (ngưỡng nền p90 của `dev`) | **đang dùng**, đóng góp chính | QĐ-031, QĐ-037 |
| C4 | định tuyến hai tầng thích nghi | **đã loại** (tốn hơn, F1 không tăng) | QĐ-031 |
| C5 | Rescue Score | **chỉ là ablation** (một điểm) | QĐ-033, QĐ-034 |

Cấu hình CTAV chốt = C1 + θ = 0,80 + C3. Không gọi C2, C4 là "ablation"; ablation là cách đã dùng để loại chúng.

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
- Chương 2–7 kết bằng mục **"Kết chương"** có đánh số (theo template GVHD), 5–8 câu, không thêm ý mới. Chương 1 kết ở
  1.5 Cấu trúc báo cáo; Chương 8, 9 không có Kết chương. Kết chương của Ch2 phải **khẳng định nền tảng đã đủ** cho đề
  tài; của Ch3 phải nêu khoảng trống và định vị đề tài.
- Đoạn dẫn chương **không đánh số** (không có "3.0"). Đánh số tối đa cấp 3 (1.2.3).
- Mỗi mục cấp 2 mở bằng một câu chủ đề nói mục này để làm gì.
- Một đoạn một ý trọn vẹn, khoảng 4–7 câu.

### 2.3 Thuật ngữ

- Giữ tiếng Anh: `microservice`, `metric`, `log`, `trace`, `candidate`, `judge`, `topology`, `pipeline`, `cache`,
  `split`, `baseline`, `ablation`, `TRUE\_ALERT`, `NORMAL`.
- Tên tiếng Việt cố định: "cửa sổ", "cảnh báo", "bằng chứng", "cửa sổ có telemetry", "đa phương thức"
  (metric + log + trace; không xen "đa nguồn", "multi-modal"), "tác tử RCA", "service gốc".
- Lần đầu xuất hiện thì giải thích, sau đó không đổi cách gọi.
- Lần đầu nhắc ký hiệu thành phần **trong mỗi chương** phải kèm chức năng:
  C1 (truy xuất lai BM25–topology), C2 (gating theo nguồn bằng chứng), C3 (neo bằng chứng),
  C4 (định tuyến hai tầng), C5 (Rescue Score).

---

## 3. Khuôn mẫu theo chương

| Chương | Khuôn |
|---|---|
| 1 Giới thiệu | Hình phễu: bối cảnh rộng → bài toán hẹp. Trực giác, động lực, kiến trúc tổng quan. **Không công thức, không CI, không số thập phân.** Được dùng số đếm (ví dụ số FP) hoặc tỷ lệ làm tròn; kết quả chính của luận văn viết định tính hoặc làm tròn. |
| 2 Kiến thức và công nghệ nền tảng | Mỗi khái niệm 4 bước: (1) định nghĩa → (2) công thức hoặc sơ đồ → (3) một ví dụ nhỏ trên dữ liệu Nezha → (4) một câu chỉ rõ luận văn dùng nó ở đâu (trỏ sang Chương 4). Không kết quả thực nghiệm. Công nghệ (§2.8): là gì, vai trò, vì sao chọn; cách lắp ráp để ở §4.5. |
| 3 Công trình liên quan | Hai nhánh: nghiên cứu (3.1) và hệ thống, công cụ (3.2). Khoảng một đoạn mỗi công trình, 3 bước: (1) họ làm gì → (2) giới hạn liên quan đến đề tài → (3) luận văn khác ở đâu. Tính năng sản phẩm ở 3.2 chỉ lấy từ tài liệu chính thức, ghi ngày truy cập. Kết chương: bảng so sánh, khoảng trống, định vị. |
| 4 Đề xuất | 4.1 Mô tả đề xuất (tổng quan, vấn đề nghiên cứu, thách thức) trước, rồi từng thành phần. Mỗi thành phần 5 bước: (1) vấn đề giải quyết → (2) thiết kế (công thức/luật) → (3) tham số và cách chọn → (4) vai trò hiện tại (đang dùng / đã bỏ / chỉ là ablation) → (5) dẫn chiếu mục Chương 5 chứa bằng chứng. C2, C4 viết gọn hơn nhưng không lược. Số `val` chỉ để giải thích một lựa chọn, mỗi chỗ một câu. **Không số `test`.** |
| 5 Thực nghiệm | Mỗi mục kiểm định giả thuyết theo 6 bước ở §3.2. |
| 6 Platform | Theo mắt người vận hành, không theo mã nguồn. Mỗi màn hình: ảnh chụp, một đoạn "màn hình trả lời câu hỏi gì", một đoạn nối với thành phần ở Chương 4. Kịch bản demo là bảng từng bước. |
| 7 Thảo luận | Không lặp bảng của Chương 5; mỗi luận điểm trích 1–2 con số rồi giải thích nguyên nhân. Mối đe doạ tính hợp lệ và phân tích ca sai ở đây; hạn chế của hệ để ở §8.2. |
| 8 Tổng kết | Không ý mới, không hình. 8.1 Kết quả đạt được: mỗi câu hỏi nghiên cứu một đoạn 3–4 câu (câu trả lời, số chính, giới hạn). 8.2: **mọi hạn chế**, viết cụ thể (cái gì, ảnh hưởng kết luận nào), mỗi hạn chế nối sang một hướng phát triển; hướng nằm trong mốc còn lại thì dẫn sang Kế hoạch. |
| 9 Công bố khoa học | Xem §1.2 và §3.1. |

### 3.1 Phần đầu và phần cuối

| Phần | Quy tắc |
|---|---|
| Tóm tắt, Abstract | Mỗi bản ≤ 1 trang, viết **sau cùng**. Bốn ý: bài toán, phương pháp, kết quả chính trên `test` (kèm CI), giới hạn. Abstract là bản dịch tương đương, không thêm bớt ý. |
| Lời cam đoan | Có đoạn khai báo AI hỗ trợ (§5.3). |
| Thứ tự phần đầu | Bìa · Lời cam đoan · Lời cảm ơn · Tóm tắt · Abstract · Mục lục · Danh mục từ viết tắt · Danh mục hình · Danh mục bảng (thứ tự của template GVHD). |
| Danh mục từ viết tắt | Mọi viết tắt dùng ≥ 2 lần (CTAV, RCA, FPR, CI, ARR...). Lần đầu trong văn vẫn viết đầy đủ. |
| Chương 9 Công bố khoa học | **Chương có số**, ngay sau Chương 8 (người dùng chốt 2026-11-18). 9.1 thông tin bài với **trạng thái thật** (đã nộp / được chấp nhận / đã đăng); 9.2 quan hệ với luận văn. Không lặp số. |
| Kế hoạch thực hiện | Không đánh số chương, đặt trước Tài liệu tham khảo. Viết theo **mốc** (M9–M12), không "Giai đoạn 1–4". Chỉ gồm việc chưa xong lúc nộp. Việc ngoài phạm vi hiện tại (judge thứ hai, dataset thứ hai) ghi là "hướng mở rộng", tách khỏi mốc bắt buộc. |
| Tài liệu tham khảo | Chuẩn **IEEE** (kiểu số `[n]`, theo template GVHD); chỉ mục thật sự được trích trong văn. |

### 3.2 Sáu bước cho một mục kiểm định (Chương 5)

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
- Caption bảng **trên** bảng; caption hình **dưới** hình. Caption hình viết **không quá 1 câu** (không tính ghi chú `(Nguồn: ...)` của sơ đồ tự vẽ) và **phải nêu sơ bộ hình đó thể hiện/làm gì**, kèm định danh tự đủ nghĩa (`split`, tập cửa sổ, `run\_id` nếu là kết quả chạy); không liệt kê dài nhiều mệnh đề trong caption (diễn giải chi tiết đặt ở đoạn văn ngay dưới hình). Trong LaTeX (`main.tex` đặt `aboveskip=-9pt`), luôn chèn `\par\vspace{0.4cm}` trước `\caption` của hình để tránh chữ đè lên mép dưới ảnh.
- Sơ đồ (kiến trúc, luồng): một bộ màu và kiểu khối thống nhất cả luận văn.
- Biểu đồ số liệu: sinh bằng script đọc thẳng `eval/results/`, không nhập số tay (`scripts/thesis_figures.py`).
- Mọi hình xuất **PNG 300 dpi** để chèn vào Word; không xuất PDF.
- Chữ trên **biểu đồ số liệu** bằng **tiếng Anh**, dấu chấm thập phân (ngoại lệ của §4, chỉ áp dụng bên trong hình).
  Caption và văn bản quanh hình vẫn tiếng Việt, dấu phẩy thập phân. Mỗi phương pháp giữ một màu ở mọi hình (BM25, C1,
  CTAV); danh sách và caption: `docs/drafts/figures/danh-sach-bieu-do.md`.
- Ảnh chụp, ví dụ prompt, ca cụ thể: lấy từ hệ thống chạy thật.
- Bảng dài hơn nửa trang hoặc chỉ để tra cứu (theo service, cấu hình đầy đủ) đưa vào phụ lục.

### 5.3 Khai báo AI hỗ trợ

Template GVHD: mọi phần lấy từ nguồn khác hoặc có AI hỗ trợ phải trích dẫn, từ Chương 1 đến hết báo cáo. Người dùng
chốt 2026-11-18: AI chỉ hỗ trợ **lập dàn ý** và **vẽ sơ đồ**.

- **Không tính là AI hỗ trợ:** judge `gemini-2.5-flash`. Đây là đối tượng nghiên cứu, trình bày ở Ch4, Ch5.
- **Lời cam đoan:** một đoạn nêu tên công cụ, dùng cho dàn ý và sơ đồ, nội dung do tác giả viết, mọi sơ đồ do tác giả
  kiểm lại.
- **Sơ đồ** (loại SĐ trong outline mục 5) vẽ có AI hỗ trợ: dòng nguồn dưới caption, ví dụ "Nguồn: tác giả vẽ, có hỗ trợ
  của công cụ AI [n]". Biểu đồ số liệu sinh từ script và ảnh chụp không cần dòng này.
- **Tài liệu tham khảo:** mỗi công cụ một mục IEEE (tên, nhà cung cấp, phiên bản hoặc model, ngày truy cập).
- Nếu sau này dùng AI cho việc khác (soạn hoặc sửa văn, dịch Abstract), phải mở rộng khai báo trước khi nộp.

### 5.2 Quy chuẩn LaTeX

- Tên biến nhiều chữ cái trong môi trường toán bọc `\mathrm{}`: `\mathrm{GraphSim}`, `\mathrm{BM25}`,
  `\mathrm{Recall}`; dùng `\exp`, `\max`, `\min`, `\log`.
- Định danh code hoặc chuỗi có gạch dưới bọc `\texttt{}` và thoát `\_`: `\texttt{network\_delay}`,
  `\texttt{paper\_500}`, `\texttt{TRUE\_ALERT}`, `\texttt{ctav\_final}`.
- Dấu phẩy thập phân **trong môi trường toán** phải viết `0{,}201` (hoặc nạp gói `icomma`); nếu không, LaTeX chèn
  khoảng trắng sau dấu phẩy. Ngoài môi trường toán viết bình thường `0,201`.
- Tham chiếu chéo luôn qua `\label`/`\ref` (`\ref{tab:h0-test}`, `\ref{sec:ctav-c3}`), không gõ số mục bằng tay.
- Không để lại ký hiệu do công cụ sinh văn bản chèn vào (ví dụ `[cite: 4]`, `【…】`). Mọi trích dẫn đi qua `\cite{}`.
- Tiền tố nhãn: `ch:`, `sec:`, `fig:`, `tab:`, `eq:`, `app:`; tên theo nội dung, không theo số (`tab:h2-test`, không `tab:5-18`).

---

## 6. Khung LaTeX

Cấu trúc đề xuất (đổi theo template của khoa nếu khác):

```text
thesis/
  main.tex            % nạp gói, macro, \include từng chương
  macros.tex          % macro dưới đây
  chapters/ch1.tex … ch9.tex, ke-hoach.tex   % ch9 = Công bố khoa học
  appendices/a.tex … f.tex
  figures/            % sơ đồ (pdf/svg) và biểu đồ sinh từ script
  tables/             % bảng sinh từ script (.tex), \input vào chương
  refs.bib
```

Macro tối thiểu (`macros.tex`):

```latex
\usepackage{icomma}                       % dấu phẩy thập phân trong môi trường toán
\newcommand{\CTAV}{CTAV}
\newcommand{\code}[1]{\texttt{#1}}         % \code{network\_delay}
\newcommand{\splitname}[1]{\texttt{#1}}    % \splitname{val}, \splitname{test}
\newcommand{\CHO}[2]{\textcolor{red}{[CHỜ #1: #2]}} % \CHO{M9}{Hit@1 trên test}
```

- Mỗi số lấy từ thực nghiệm kèm chú thích nguồn ngay cạnh: `0,201 % src: ctav_final_test_v1`. Rà chéo số dựa vào các
  chú thích này.
- Bảng và biểu đồ số liệu sinh bằng script vào `tables/`, `figures/`; không gõ số tay vào bảng.
- Trước khi nộp: `grep -n "CHO{" chapters/` phải rỗng hoặc chỉ còn chỗ đã chuyển vào Kế hoạch có chủ đích.

---

## 7. Nội dung đã chốt

**Mục tiêu cụ thể (1.2.2), chốt 2026-11-16.** Năm mục, mỗi mục 1–2 câu: (1) giao thức đánh giá chống rò rỉ và xác lập
bài toán; (2) phân tích cơ chế báo động giả của judge LLM; (3) đề xuất CTAV (truy xuất lai BM25–topology, ngưỡng tin
cậy, neo bằng chứng); (4) kiểm định theo giả thuyết đăng ký trước (một lần trên `test`, bootstrap CI, McNemar,
ablation, ngân sách); (5) tác tử RCA và platform end-to-end tái lập được từ cache. Văn bản LaTeX đầy đủ do người dùng
giữ trong `ch1.tex`; sửa mục tiêu thì cập nhật đoạn này.

**Đối tượng và phạm vi (1.3), chốt 2026-11-16.** Ba đối tượng: dữ liệu đa phương thức và đồ thị phụ thuộc; CTAV
(nhận candidate từ detector, **không gồm detector**); tác tử RCA và platform thực nghiệm. Phạm vi phải nêu: Nezha là
bộ dữ liệu duy nhất, hai hệ (OnlineBoutique, TrainTicket), **năm loại lỗi** (không phải hai), cửa sổ có telemetry,
chạy replay + cache, chưa kiểm chứng trên dữ liệu khác; một LLM `gemini-2.5-flash` (QĐ-021), không fine-tuning, không
LLM cục bộ. Chi tiết như 56 service / 68 cạnh, vùng đệm 600 s để ở Ch2, Ch5.

**Ý nghĩa (1.4), chốt 2026-11-16.** Không được viết: "thời gian thực", "streaming", "kiến trúc hai tầng giải quyết
độ trễ" (C4 đã loại), "LLM phát hiện bất thường" (LLM là judge, không là detector), mở rộng sang IoT/trung tâm dữ liệu,
"học sâu truyền thống" (Isolation Forest không phải học sâu), "tài liệu tham khảo có giá trị". Ý nghĩa thực tiễn: chính
sách quyết định kiểm soát báo động giả khi thêm ngữ cảnh, chi phí theo ngân sách gọi LLM, RCA từ cảnh báo đã thẩm định,
platform tái lập được. Ý nghĩa khoa học: cơ chế thiên lệch xác nhận, giao thức đăng ký trước, kết quả âm có kiểm chứng.

**Câu hỏi nghiên cứu:** RQ1–RQ5 theo `suon-bao-cao-gd2.md` (RQ1↔H0, RQ2↔H1, RQ3↔H2+H4, RQ4↔H3, RQ5↔H5). Dùng đúng
5 RQ ở 1.2.3 và 8.1.1.

---

## 8. Checklist trước khi coi một mục là xong

- [ ] Không có từ ở §1.1 (giai đoạn, GĐ, kế thừa…) và §2.1 (từ cấm).
- [ ] Bài báo ICAETM chỉ xuất hiện như trích dẫn, không làm trục so sánh.
- [ ] Mọi con số có split và tập cửa sổ; mọi hiệu có CI; không "tốt hơn" khi CI chứa 0.
- [ ] C2/C4/C5 và giới hạn recall của CTAV được nêu ở đúng chỗ, không né.
- [ ] Hình/bảng được nhắc trước, caption đúng vị trí và tự đủ nghĩa.
- [ ] C1–C5 dùng đúng nhãn vai trò ở §1.4; lần đầu mỗi chương có kèm chức năng.
- [ ] Mỗi số thực nghiệm có `% src: <run_id>`.
- [ ] Chỗ chưa có số đã gắn `\CHO{M*}{...}`; không còn `[cite: …]`.
- [ ] Sơ đồ vẽ có AI hỗ trợ đã có dòng nguồn dưới caption (§5.3); chương 2–7 có Kết chương đánh số.
