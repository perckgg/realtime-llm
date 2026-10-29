# Chương — Bài toán (nháp M4 việc 5)

> Nháp ngày 2026-10-28. Nguồn: paper ICAETM 2026 (`docs/submission_docs/paper/draft.md`,
> `docs/Final_Thesis_Phase2/08-research-direction.md` §2), Phát hiện 1–6 trong
> `docs/experiment-log.md` (QĐ-016, QĐ-019, QĐ-020, QĐ-021, QĐ-022, QĐ-025). Mỗi số liệu ghi
> kèm QĐ gốc để đối chiếu. Mục 6 = kết quả H0 (QĐ-026) và vấn đề phát biểu lại (QĐ-027, GVHD đồng ý). Số chương/bảng là tạm,
> đánh lại khi ghép vào luận văn.

---

## 1. Bối cảnh: thẩm định cảnh báo bằng LLM có truy xuất bằng chứng

Trong hệ thống microservice, bộ phát hiện bất thường trên metric chạy nhanh và rẻ, nhưng sinh
ra nhiều cảnh báo không kèm bằng chứng vận hành. Trên tập `val` của luận văn, Isolation Forest
với ngưỡng 0,85 sinh 5.677 cảnh báo ứng viên trên 28.898 cửa sổ, trong đó chỉ 109 ứng viên
thuộc cửa sổ có sự cố (recall detector 0,52, FPR 0,194; QĐ-018). Nếu chuyển thẳng các ứng viên
này cho kỹ sư vận hành (SRE), phần lớn là báo động giả.

Kiến trúc lai được nghiên cứu ở Giai đoạn 1 (GĐ1) và trong paper ICAETM 2026 xử lý vấn đề này
bằng ba tầng:

1. **Detector** trên metric sinh ứng viên cảnh báo.
2. **Truy xuất (retrieval)** chọn top-k sự kiện log/trace liên quan đến ứng viên.
3. **LLM judge** đọc ứng viên cùng bằng chứng, trả về nhãn có cấu trúc (`true_alert`,
   `false_positive`, `uncertain`), độ tin cậy và danh sách bằng chứng đã dùng.

Một chính sách quyết định (ngưỡng tin cậy, luật bắt buộc có bằng chứng, ngân sách số lần gọi
LLM) chuyển nhãn của judge thành hành động: chuyển cảnh báo cho SRE, bỏ qua, hoặc đưa vào hàng
đợi xem tay.

Câu hỏi trung tâm của paper là: bằng chứng nên được chọn chỉ theo độ liên quan từ vựng và thời
gian, hay nên tính thêm **độ gần trên đồ thị phụ thuộc service**?

## 2. Phát biểu bài toán

**Ứng viên cảnh báo.** Mỗi ứng viên là bộ `a = (s₀, t₀, x, z)`: service `s₀`, thời điểm `t₀`,
vector metric `x` của cửa sổ và điểm bất thường `z ∈ [0, 1]` của detector.

**Kho bằng chứng.** `E` là tập sự kiện log và span trace; mỗi sự kiện `e` có service `s_e`,
thời điểm `t_e` và nội dung văn bản. `G = (V, A)` là đồ thị gọi giữa các service dựng từ trace
(56 service, 68 cạnh trên Nezha; QĐ-021); `d_G(s, s')` là khoảng cách trên đồ thị vô hướng.

**Truy xuất.** Hàm `R(a) ⊂ E`, `|R(a)| ≤ k` (k = 6) chọn bằng chứng cho ứng viên. Hai họ
phương pháp được so sánh:

- **BM25** (baseline): xếp hạng theo BM25 giữa truy vấn sinh từ ứng viên và nội dung sự kiện,
  giới hạn trong ±8 phút quanh `t₀`.
- **Topology (C1, phương pháp của paper)**: xếp hạng theo Fusion Score

  `Score(e) = α · BM25_norm(e) + β · exp(−|t_e − t₀| / τ) + γ · GraphSim(s_e, s₀)`,

  với `GraphSim = 1 / (1 + d_G)` nếu `s_e` tới được `s₀`, ngược lại 0; `α + β + γ = 1`,
  τ = 300 s. Cấu hình A4 của paper: α = 0,35, β = 0,25, γ = 0,40, mở rộng 2-hop, top-6.

**Judge và chính sách.** `J(a, R(a)) → (ŷ, c, Ev)` với nhãn `ŷ`, độ tin cậy `c` và tập bằng
chứng được trích `Ev ⊆ R(a)`. Cảnh báo được chuyển cho SRE khi `ŷ = true_alert`, `c ≥ θ`
(θ = 0,80) và `Ev ≠ ∅` (luật `require_evidence`); các trường hợp còn lại thành bỏ qua hoặc xem
tay. Mỗi run có ngân sách `B` lần gọi LLM; hết ngân sách thì ứng viên còn lại đi vào xem tay.

**Mục tiêu.** Với cùng judge, cùng prompt, cùng ngân sách `B`, chọn `R` (và chính sách) để
tăng recall của các cửa sổ có sự cố mà **không** tăng tỷ lệ báo động giả (FPR) trên cửa sổ bình
thường, đồng thời kiểm soát chi phí (số lần gọi, token) và độ trễ. Chỉ số: precision, recall,
F1, FPR, kèm khoảng tin cậy bootstrap và kiểm định McNemar có cặp.

## 3. Vấn đề do paper chỉ ra

Paper đánh giá trên tập `paper_500` đóng băng (100 cửa sổ sự cố, 400 cửa sổ bình thường,
56 service), judge `gemini-2.5-flash-lite`, nhiệt độ 0.

Bảng 3.1. Kết quả chính của paper (View A, top-6).

| | BM25 | Topology (A4) |
|---|---|---|
| Recall (toàn ngân sách) | 0,58 | **0,74** |
| Recall `network_delay` | 0,375 | **0,70** |
| Báo động giả trên 400 cửa sổ bình thường | **7** | 137 |
| FPR | **0,0175** | 0,3425 |
| F1 (toàn ngân sách) | **0,7030** | 0,4759 (McNemar p = 2,61 × 10⁻¹⁹) |
| Chi phí API | 1× | ≈ 2,7× |
| F1 ở ngân sách 120 lần gọi | 0,508 | 0,514 (LLM không RAG: 0,566) |

Paper diễn giải kết quả hai mặt này như sau: topology giúp LLM thấy bằng chứng mà BM25 bỏ sót
(recall tăng, rõ nhất với `network_delay`), nhưng cũng đưa vào telemetry bình thường của service
lân cận khiến LLM xác nhận cả sự cố không tồn tại — **thiên lệch xác nhận do ngữ cảnh**. Gần trên
đồ thị không có nghĩa là liên quan nhân quả, nên truy xuất và chính sách quyết định không thể
tối ưu tách rời.

Paper cũng tự nêu các điểm còn bỏ ngỏ: chưa tách được nguyên nhân của thiên lệch (khối lượng,
thứ tự hay nội dung bằng chứng), mỗi cấu hình chỉ chạy một lần, trọng số được chọn khi đã nhìn
`paper_500`, và hệ thống chỉ thẩm định cảnh báo chứ chưa định vị nguyên nhân gốc.

## 4. Đánh giá lại giao thức của paper

Trước khi xây giải pháp trên vấn đề của paper, luận văn tái lập chính xác kết quả paper (cổng
G-paper: 489/489 top-6, prompt và cache trùng; F1 0,7030 / FP 7 cho BM25 và F1 0,4759 / FP 137
cho topology; QĐ-021), rồi kiểm tra từng giả định của giao thức đánh giá. Sáu phát hiện dưới đây
cho thấy một phần đáng kể của kết quả trong Bảng 3.1 đến từ giao thức và dữ liệu, không chỉ từ
cơ chế topology.

### 4.1 Về dữ liệu và giao thức đánh giá

**Phát hiện 1 — có bằng chứng hay không gần như lộ nhãn (QĐ-016).** Hai nguyên nhân chồng lên
nhau. (i) Dataset Nezha chỉ có file log/trace trong một số phút quanh các lần tiêm lỗi (cả bốn
ngày: 303 phút), trong khi metric liên tục cả ngày. (ii) Bước tiền xử lý của GĐ1 còn lọc tiếp,
chỉ giữ log/trace của service bị tiêm lỗi trong [−300 s, +600 s] quanh mỗi lần tiêm.

Bảng 4.1. Có bằng chứng hay không, theo nhãn, trên 489 lần gọi LLM của paper.

| | Sự cố (98) | Bình thường (391) |
|---|---|---|
| Paper: top-6 không rỗng | 89 (90,8%) | 21 (5,4%) |
| Kho Nezha đầy đủ: top-6 không rỗng | 98 (100%) | 76 (19,4%) |
| Có file log/trace trong ±8 phút | 98 (100%) | 106 (27,1%) |

Trong paper, 370/391 cửa sổ bình thường không có bằng chứng; 360 trong số đó được LLM gắn
`true_alert` và chỉ bị luật `require_evidence` chặn lại. FP = 7 của BM25 vì vậy chủ yếu phản ánh
việc cửa sổ bình thường **không có** bằng chứng, không phải việc BM25 chọn bằng chứng tốt. Hiện
tượng không chỉ do bước lọc của GĐ1: trên toàn split của luận văn, khoảng 75% cửa sổ bình thường
không có log/trace nào (Bảng 4.2), nên một judge có `require_evidence` sẽ "đúng" một cách tầm
thường trên chúng.

Bảng 4.2. Cửa sổ có file log/trace trong ±8 phút, theo split của luận văn.

| Split | Sự cố | Bình thường |
|---|---|---|
| dev | 149/149 (100%) | 4.881/19.167 (25,5%) |
| val | 209/209 (100%) | 7.427/28.689 (25,9%) |
| test | 346/346 (100%) | 11.639/46.503 (25,0%) |

**Phát hiện 3 — biến thể "topology" của paper chủ yếu là BM25 không giới hạn thời gian
(QĐ-020).** Cài đặt topology của paper gộp (i) top-60 BM25 tìm trên **toàn kho, không lọc thời
gian** và (ii) mở rộng đồ thị 2-hop trong ±8 phút, rồi xếp hạng bằng Fusion Score.

Bảng 4.3. Nguồn và thời điểm của 2.934 bằng chứng topology trong paper.

| | Số bằng chứng | Tỷ lệ |
|---|---|---|
| Chỉ từ BM25 toàn kho | 2.612 | 89,0% |
| Chỉ từ mở rộng đồ thị | 229 | 7,8% |
| Cả hai | 93 | 3,2% |
| Nằm ngoài ±8 phút quanh cửa sổ | 2.354 | 80,2% |
| … trong đó cách hơn 1 giờ | 2.200 | 75,0% |
| Cửa sổ bình thường có bằng chứng | 391/391 (100%) | BM25: 21/391 |

Kết hợp với Phát hiện 1 (kho của GĐ1 chỉ gồm log/trace quanh các lần tiêm lỗi), mọi cửa sổ bình
thường dưới biến thể topology đều nhận bằng chứng, phần lớn là log/trace của **sự cố ở thời điểm
khác**. Đây là một giải thích cạnh tranh cho FP = 137: bằng chứng lệch thời gian, không phải bằng
chứng của service lân cận trên đồ thị.

### 4.2 Về LLM judge

**Phát hiện 2 — độ tin cậy của judge chủ yếu là điểm detector chép lại (QĐ-016, QĐ-019).**
Trong 489 câu trả lời BM25 của paper, 365 (74,6%) có `confidence` bằng đúng `anomaly_score`
trong prompt. Hiện tượng gắn với việc prompt thiếu bằng chứng: 316/379 (83,4%) khi prompt không
có bằng chứng, 49/110 (44,5%) khi có. Ngưỡng θ = 0,80 vì thế phần lớn là ngưỡng trên điểm
detector. Trên giao thức của luận văn (mọi prompt có `top_features`, judge `gemini-2.5-flash`),
tỷ lệ này giảm còn 1/196 ở smoke (QĐ-021).

**Phát hiện 5 — một cột metric chết làm lệch judge (QĐ-022, QĐ-023).** Cột
`PodSuccessRate(%)` của Nezha bằng 0 ở 95.660/95.660 dòng metric, nhưng prompt (của cả paper)
đưa nguyên giá trị vào, nên mọi prompt đều nói "tỷ lệ thành công 0%". Judge Gemini 3.x đọc theo
nghĩa đen là sự cố nên gần như không bác bỏ cảnh báo nào; `gemini-2.5-flash` coi đây là nhiễu
nhưng vẫn có 33/196 nhãn `true_alert` mà phần giải thích nhắc đến "success"/"0%". Bỏ cột này khỏi prompt (chỉ thay đổi prompt,
truy xuất giữ nguyên) đổi hẳn hành vi:

Bảng 4.4. Smoke 196 ứng viên dev, BM25, trước và sau khi bỏ cột chết (không phải kết quả khoa
học — 21 cửa sổ sự cố, CI rộng).

| | 2.5-flash trước | 2.5-flash sau | 3.8-flash trước | 3.8-flash sau |
|---|---|---|---|---|
| TP / FP / FN | 8 / 25 / 13 | 7 / 1 / 14 | 6 / 40 / 15 | 3 / 0 / 18 |
| F1 | 0,296 | 0,483 | 0,179 | 0,250 |
| FPR | 0,040 | 0,002 | 0,064 | 0,000 |
| Nhãn thô trùng bản trước | | 165/196 | | 15/196 |

Một lỗi dữ liệu làm thay đổi kết quả judge mạnh hơn cả việc đổi model.

**Quy tắc ngân sách của GĐ1 (QĐ-018).** Khi tái lập Phase 4 của GĐ1, 10/13 báo động giả đến từ
quy tắc "hết ngân sách thì chuyển cảnh báo", chỉ 3 đến từ judge. Luận văn mặc định đưa ứng viên
hết ngân sách vào hàng đợi xem tay.

### 4.3 Về cơ chế topology trên dữ liệu đầy đủ

**Phát hiện 4 — Fusion Score với trọng số paper không đưa được bằng chứng lân cận (QĐ-021).**
Khi C1 chạy trên kho Nezha đầy đủ và giới hạn trong ±8 phút (giao thức của luận văn), 810 sự
kiện được chọn cho 196 ứng viên dev đều thuộc chính `s₀`; **0/196** prompt có bằng chứng của
service lân cận. Nguyên nhân mang tính cấu trúc: `GraphSim(s₀) = 1` trong khi
`GraphSim(d = 1) = 0,5`, và truy vấn chứa tên service/pod của `s₀` nên BM25 cũng ưu tiên `s₀`.
Điểm tối đa của một sự kiện lân cận d = 1 là 0,35 + 0,25 + 0,40 × 0,5 = 0,80, thấp hơn trung vị
điểm của sự kiện hạng 6 (0,841). Trong paper, bằng chứng lân cận chỉ xuất hiện vì kho của GĐ1 đã
lọc rất thưa.

**Phát hiện 6 — trọng số Fusion gần như không điều khiển được bằng chứng lân cận (QĐ-025).**
Ablation chỉ trên truy xuất (không gọi LLM) với lưới α, β, γ bước 0,25 trên `val`:

Bảng 4.5. Bằng chứng lân cận theo trọng số, `val`, 1.177 ứng viên bình thường có bằng chứng.

| α / β / γ | Có lân cận, không quota | Có lân cận, quota 1/6 | Root đang lỗi cùng lúc trong top-6, quota (/166) |
|---|---|---|---|
| 0,35 / 0,25 / 0,40 (paper) | 3 | 1.177 | 7 (4,2%) |
| 0 / 0 / 1 (graph-only) | 3 | 1.177 | 9 (5,4%) |
| 1 / 0 / 0 (lexical-only) | 115 | 1.177 | 11 (6,6%) |
| 0 / 1 / 0 (temporal-only) | 1.171 (mất bằng chứng của service gốc: root hit 9/109) | 1.177 | 4 (2,4%) |
| 0,25 / 0,75 / 0 (cao nhất) | 94 | 1.177 | 14 (8,4%) |

Mọi điểm lưới có γ ≥ 0,25 đều giữ top-6 gần như toàn bằng chứng cục bộ; chỉ temporal-only đảo
ngược hẳn, và khi đó mất bằng chứng của chính service gốc. Muốn đưa bằng chứng lân cận vào prompt
phải dành chỗ (quota `k_graph`), không thể chỉ chỉnh trọng số. Ngay cả khi có quota, bằng chứng
lan truyền thật (top-6 chứa service gốc đang lỗi cùng lúc) hiếm: tối đa 8,4%.

## 5. Phát biểu lại vấn đề nghiên cứu

Sáu phát hiện trên không bác bỏ quan sát của paper, nhưng cho thấy Bảng 3.1 trộn lẫn ba hiệu
ứng: (i) có/không có bằng chứng gần như trùng với nhãn (Phát hiện 1); (ii) biến thể topology chủ
yếu mang vào bằng chứng lệch thời gian chứ không phải bằng chứng lân cận (Phát hiện 3); (iii)
hành vi judge phụ thuộc vào artefact của prompt (Phát hiện 2, 5). Trên dữ liệu đầy đủ, chính
công thức của paper lại gần như không chọn bằng chứng lân cận (Phát hiện 4, 6).

Luận văn vì vậy đặt lại câu hỏi trên một giao thức đã loại các hiệu ứng trên:

| Hiệu ứng | Giao thức của luận văn |
|---|---|
| Bằng chứng lộ nhãn (PH1) | Kho Nezha đầy đủ, không lọc theo nhãn; chỉ số chính tính trên **cửa sổ có telemetry** (có file log/trace trong ±8 phút — tính từ danh sách file, không từ nhãn); toàn split là số phụ (QĐ-017) |
| Bằng chứng lệch thời gian (PH3) | Mọi biến thể truy xuất giới hạn ±8 phút (`bm25_pool: window`, QĐ-021) |
| Confidence chép điểm detector (PH2) | Prompt luôn có `top_features`; chính sách CTAV dựa trên nguồn gốc và neo bằng chứng, không chỉ confidence (QĐ-017) |
| Cột metric chết (PH5) | `drop_metrics: ["PodSuccessRate(%)"]` cho mọi run có judge thật (QĐ-023) |
| Topology không có bằng chứng lân cận (PH4, PH6) | So sánh cả **C1-paper** (`k_graph = 0`, đúng công thức) và **C1-quota** (`k_graph = 1`: một trong sáu chỗ dành cho lân cận, QĐ-022, QĐ-024) |
| Trọng số chọn khi đã nhìn dữ liệu đánh giá | Split dev/val/test nhóm theo lần tiêm lỗi; tinh chỉnh chỉ trên `val`, `test` chạy một lần sau đăng ký giả thuyết (QĐ-004, QĐ-005) |
| Judge | `gemini-2.5-flash`, nhiệt độ 0, một prompt cho mọi biến thể; run dừng nếu API trả về model khác (QĐ-020, QĐ-021) |

Câu hỏi nghiên cứu được phát biểu lại:

> Trên giao thức đã loại các hiệu ứng lộ nhãn và lệch thời gian, việc đưa bằng chứng của service
> lân cận vào prompt có còn tăng recall và đồng thời tăng báo động giả so với BM25 không (H0)?
> Nếu có, làm thế nào giữ được mức tăng recall mà không tăng báo động giả, trong cùng ngân sách
> LLM (H1–H4)?

H0 là cổng chặn của hướng nghiên cứu: nếu không tái lập được hiện tượng trên giao thức này, kết
luận đúng là vấn đề của paper phần lớn là hệ quả của giao thức đánh giá, và câu chuyện của luận
văn phải viết lại theo hướng đó (`08` §5.1).

## 6. Kết quả H0 trên `val`

> Số liệu từ QĐ-026 (2026-10-28). Cách diễn giải ở 6.3 phụ thuộc quyết định V24 (báo cáo M4 §3);
> sửa lại sau khi chốt.

**Thiết lập.** Tập `val` (28.898 cửa sổ, 209 cửa sổ sự cố); số chính trên 7.636 cửa sổ có
telemetry. Detector Isolation Forest ngưỡng 0,85 (5.677 ứng viên, 1.749 có telemetry). Judge
`gemini-2.5-flash`, nhiệt độ 0, θ = 0,80, `require_evidence`, bỏ cột metric chết; Fusion Score
dùng trọng số paper. Mỗi phương pháp chấm toàn bộ ứng viên. CI 95% bằng bootstrap; hiệu số dùng
bootstrap có cặp; McNemar chính xác tách riêng cửa sổ sự cố và bình thường
(`py -m eval compare`, `eval/results/h0_val_compare_v1/`).

### 6.1 Kết quả

Bảng 6.1. H0 trên `val`, tập có telemetry.

| Phương pháp | TP | FP | Precision | Recall [CI95] | F1 [CI95] | FPR [CI95] |
|---|---|---|---|---|---|---|
| Detector-only | 109 | 1.640 | 0,062 | 0,522 [0,454; 0,589] | 0,111 [0,094; 0,131] | 0,221 [0,211; 0,230] |
| BM25 | 34 | 417 | 0,075 | 0,163 [0,115; 0,214] | 0,103 [0,072; 0,133] | 0,056 [0,051; 0,061] |
| C1-paper (k_graph = 0) | 55 | 606 | 0,083 | 0,263 [0,205; 0,326] | 0,126 [0,095; 0,156] | 0,082 [0,075; 0,087] |
| C1-quota (k_graph = 1) | 53 | 585 | 0,083 | 0,254 [0,197; 0,315] | 0,125 [0,094; 0,156] | 0,079 [0,073; 0,085] |
| LLM không RAG | 18 | 166 | 0,098 | 0,086 [0,052; 0,128] | 0,092 [0,056; 0,134] | 0,022 [0,019; 0,026] |

LLM không RAG ở bảng trên tắt `require_evidence`; khi bật thì không cảnh báo nào được chuyển
(recall 0 theo cấu trúc).

Bảng 6.2. Hiệu số so với BM25 (CI 95% bootstrap có cặp) và McNemar.

| So sánh | ΔRecall | ΔFPR | ΔF1 | McNemar p (sự cố / bình thường) |
|---|---|---|---|---|
| C1-paper − BM25 | +0,100 [+0,052; +0,155] | +0,025 [+0,020; +0,031] | +0,023 [−0,004; +0,052] | 5,1 × 10⁻⁴ / 5,0 × 10⁻²⁴ |
| C1-quota − BM25 | +0,091 [+0,040; +0,145] | +0,023 [+0,018; +0,028] | +0,022 [−0,004; +0,051] | 1,3 × 10⁻³ / 2,2 × 10⁻²⁰ |
| C1-quota − C1-paper | −0,010 [−0,044; +0,028] | −0,003 [−0,006; +0,001] | −0,001 [−0,017; +0,016] | 0,79 / 0,16 |
| Không RAG − BM25 | −0,077 [−0,124; −0,034] | −0,034 [−0,040; −0,028] | −0,011 [−0,050; +0,022] | 2,5 × 10⁻³ / 4,0 × 10⁻³¹ |

Trên toàn split, các biến thể có RAG giữ nguyên TP/FP (ứng viên không có telemetry đều có truy
xuất rỗng và bị `require_evidence` chặn); FPR của BM25 0,0145, C1-paper 0,0211. Với ngân sách 120
lần gọi theo thứ tự thời gian, chỉ ≈ 7% ứng viên có telemetry được chấm (BM25: TP 2 / FP 44;
C1: TP 3 / FP 52), nên một điểm ngân sách này không đủ để so sánh; ảnh hưởng của ngân sách được
đo bằng đường cong ở H4.

### 6.2 Bằng chứng nào tạo ra khác biệt

Bảng 6.3. Bằng chứng trong prompt, ứng viên có telemetry (`scripts/h0_evidence_diff.py`).

| | BM25 bình thường | C1-paper bình thường | BM25 sự cố | C1-paper sự cố |
|---|---|---|---|---|
| Prompt có bằng chứng | 1.174 / 1.640 | 1.177 / 1.640 | 109 / 109 | 109 / 109 |
| Số sự kiện trung bình | 4,30 | 4,31 | 6,00 | 6,00 |
| Tỷ lệ bằng chứng lân cận | 0 | 0,0025 | 0 | 0 |
| Tỷ lệ span trace | 0,794 | 0,984 | 0,858 | 0,962 |
| Trung vị \|t_e − t₀\| | 167 s | 66 s | 139 s | 73 s |
| Judge trả `true_alert` | 495 | 684 | 34 | 55 |

Hai phương pháp có cùng lượng bằng chứng và gần như không có bằng chứng lân cận, nhưng chỉ chung
trung bình 1,67/6 sự kiện mỗi prompt. Fusion Score (thành phần β · TimeSim) kéo top-6 về các span
trace sát thời điểm cửa sổ, và judge xác nhận nhiều hơn ở cả cửa sổ sự cố lẫn bình thường. Các
báo động giả không tập trung quanh sự cố: không có báo động giả nào nằm trong ±10 phút của một
cửa sổ sự cố cùng service.

### 6.3 Nhận định

**Phát hiện 7 — H0 tái lập về hiện tượng, không tái lập về cơ chế.**

1. *Hiện tượng.* Trên giao thức đã loại các hiệu ứng lộ nhãn và lệch thời gian, topology chưa hiệu
   chỉnh vẫn tăng recall (+0,10) và tăng FPR (+0,025) so với BM25, có ý nghĩa thống kê ở cả cửa sổ
   sự cố lẫn bình thường; ΔF1 có CI chứa 0. Hướng giống paper, nhưng độ lớn nhỏ hơn nhiều (paper:
   FPR 0,0175 → 0,3425).
2. *Cơ chế.* Hiệu ứng không đến từ bằng chứng của service lân cận: C1-paper gần như không có bằng
   chứng lân cận mà đã tạo đủ hiệu ứng, và dành một chỗ cho bằng chứng lân cận (C1-quota) không đổi
   kết quả. Giải thích "thiên lệch xác nhận do ngữ cảnh lân cận" của paper vì vậy không đứng được
   trên giao thức này; giả thuyết cạnh tranh là độ gần thời gian và loại bằng chứng, cần kiểm định
   riêng (H1).
3. *Mức hiệu năng.* Khi bằng chứng không còn trùng với nhãn, mọi biến thể có judge chỉ đạt
   precision 0,075–0,098 và F1 không khác detector-only. Judge xác nhận 30–42% ứng viên bình thường
   có bằng chứng. Vấn đề cần giải quyết vì vậy rộng hơn topology: judge xác nhận quá dễ khi được
   đưa telemetry bình thường, bất kể nguồn của telemetry.

### 6.4 Vấn đề nghiên cứu sau H0

> Theo QĐ-027 (2026-10-29; GVHD đồng ý cùng ngày).

H0 cho thấy vấn đề mà paper chỉ ra là có thật trên giao thức không lộ nhãn, nhưng cơ chế khác với
giải thích của paper. Luận văn vì vậy phát biểu vấn đề là **thiên lệch xác nhận theo nội dung bằng
chứng**: khi được đưa telemetry bình thường của chính service bị cảnh báo, judge vẫn xác nhận sự cố,
và cách chọn bằng chứng (độ gần thời gian, loại bằng chứng) làm mức thiên lệch thay đổi.

> Có thể giữ được mức tăng recall của tầng truy xuất topology mà không tăng báo động giả, trong cùng
> ngân sách LLM, bằng cách hiệu chỉnh quyết định của judge theo hồ sơ của bằng chứng mà nó trích dẫn
> và buộc mỗi xác nhận phải dựa trên ít nhất một bằng chứng bất thường tại service bị cảnh báo không?

Câu hỏi này dẫn tới ba thay đổi so với kế hoạch ban đầu của CTAV, trình bày ở chương Giải pháp:
ngưỡng bất đối xứng (C2) tính theo hồ sơ bằng chứng thay vì theo khoảng cách trên đồ thị; luật neo
bằng chứng (C3) yêu cầu bằng chứng bất thường tại `s₀`; thí nghiệm cơ chế (H1) can thiệp vào độ gần
thời gian, loại và thứ tự của bằng chứng, với tỷ lệ bằng chứng lân cận chỉ còn là đối chứng âm.
