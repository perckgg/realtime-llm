# Bản nháp — RCA Agent trên `val` (nguyên liệu cho Ch4 §phương pháp RCA và Ch5 §5.9)

> Trạng thái: M9-A, 2026-11-16. Mọi con số ở đây thuộc **`val`** (28.898 cửa sổ, 30 lần tiêm lỗi); dùng để chọn
> tham số, **không** dùng để kết luận H5. Bảng H5 trên `test` sẽ viết ở M9-B. Nguồn: `eval/results/rca_select_val_v1/`,
> `eval/results/rca_final_val_v1/`; quyết định QĐ-040, QĐ-041. CI95: bootstrap percentile, 1.000 mẫu, seed 42.

---

## A. Mô tả phương pháp (cho Ch4)

### A.1 Vị trí trong hệ thống

Tác tử RCA nhận các cảnh báo đã được CTAV xác nhận (`TRUE_ALERT`) và chạy ngoài đường găng, không đồng bộ với judge.
Nó làm ba việc nối tiếp: gom cảnh báo thành sự cố (*incident*), định vị service gốc của mỗi sự cố, và viết báo cáo
chẩn đoán có cấu trúc. Hai việc đầu là thuật toán thuần, không gọi LLM; chỉ việc thứ ba gọi LLM, một lần cho mỗi sự cố.

### A.2 Gom cảnh báo thành sự cố

Các cảnh báo được sắp theo thời gian và cắt thành cụm ở mọi chỗ hai cảnh báo liên tiếp cách nhau quá $T_{group}$
(liên kết đơn). Trong mỗi cụm, lấy đồ thị con của đồ thị phụ thuộc service (vô hướng) cảm sinh bởi các service có cảnh
báo; mỗi thành phần liên thông là một sự cố. Hai service chỉ vào chung một sự cố khi chúng kề nhau trên đồ thị và cảnh
báo của chúng gần nhau về thời gian.

### A.3 Định vị service gốc — lan truyền ngược một bước (mức 1)

Khi service $a$ gọi service $b$ và $b$ hỏng, $a$ chậm hoặc lỗi theo: triệu chứng lan **ngược chiều gọi**. Vì vậy từ
mỗi service có cảnh báo, thuật toán nhìn một bước **theo chiều gọi**. Gọi $A$ là tập service có cảnh báo trong sự cố,
$N^{+}(s)$ là tập callee trực tiếp của $s$ trên đồ thị gọi có hướng:

$$B(s) = \begin{cases} N^{+}(s) \cap A & \text{nếu } N^{+}(s) \cap A \neq \varnothing \\ \{s\} & \text{ngược lại} \end{cases}
\qquad
\mathrm{score}(v) = \frac{1}{|A|} \sum_{s \in A,\; v \in B(s)} \frac{1}{|B(s)|}$$

Service được xếp theo $\mathrm{score}$ giảm dần; hoà thì xét anomaly score cao nhất của service trong khoảng thời gian
sự cố (± 60 s), rồi tên. Các service có cảnh báo nhưng không nhận phiếu nào đứng sau, để Hit@3 vẫn tìm thấy chúng. Mỗi
service góp đúng một phiếu và điểm được chia cho $|A|$, nên thứ hạng **không phụ thuộc số cảnh báo tuyệt đối** — điều
cần thiết vì detector đưa lên tỉ lệ candidate khác nhau giữa các split.

Baseline so sánh (đã đăng ký ở H5): service có anomaly score cao nhất trong các cảnh báo của sự cố.

Mức 2 — để LLM lập luận ngược trên toàn bộ chuỗi gọi — đã bị cắt khỏi phạm vi (QĐ-037); luận văn không có so sánh
"một bước" với "toàn chuỗi".

### A.4 Báo cáo chẩn đoán

Với mỗi sự cố, LLM (`gemini-2.5-flash`, temperature 0) nhận: khoảng thời gian, các service, thứ hạng service gốc của
mức 1, các cạnh gọi liên quan, lý do của judge cho từng cảnh báo, và tối đa 12 bằng chứng mà các cảnh báo đã trích
(bằng chứng của service gốc đứng trước). **Service gốc không do LLM chọn** mà lấy hạng 1 của mức 1; LLM viết loại lỗi,
độ tin cậy, danh sách bằng chứng, đường lan truyền và việc nên làm. Câu trả lời bị loại — và được ghi vào bảng
`diagnostic_rejected` kèm lý do, không bao giờ bị bỏ qua im lặng — khi: không phải JSON đúng lược đồ; độ tin cậy ngoài
$[0, 1]$; một "việc nên làm" có dạng câu lệnh thực thi (bắt đầu bằng `kubectl`, `sudo`, `docker`, `rm`..., hoặc chứa
`&&`, `$(`); hoặc không trích được bằng chứng nào có trong ngữ cảnh (`require_evidence`; id bịa bị bỏ và ghi lại).
Service gốc không có trong đồ thị thì báo cáo vẫn được phát hành nhưng gắn cờ nghi vấn.

### A.5 Cách chấm

- **Nhãn sự cố.** Một lần tiêm lỗi phủ từ cửa sổ lỗi đầu tiên đến hết cửa sổ lỗi cuối cùng (7 phút). Một cảnh báo
  thuộc lần tiêm lỗi mà cửa sổ của nó giao về thời gian, bất kể service. Sự cố có nhãn khi các cảnh báo của nó thuộc
  đúng một lần tiêm lỗi (service gốc thật = service bị tiêm, nhãn mức service — bảy service chạy nhiều bản sao nên
  chấm mức service dễ hơn mức pod); thuộc từ hai lần trở lên thì là *mơ hồ*, loại khỏi Hit@k và có báo số lượng;
  không thuộc lần nào thì không có service gốc để tìm.
- **Hit@k** = tỉ lệ sự cố có nhãn mà service gốc thật nằm trong $k$ hạng đầu. Báo thêm Hit@k trên mọi lần tiêm lỗi
  (lần không có sự cố có nhãn nào tính là trượt).
- **Alert Reduction Ratio** trên một tập cảnh báo = $1 - (\text{số sự cố chứa ít nhất một cảnh báo của tập}) / (\text{số cảnh báo của tập})$.
  Lỗi *cascade* = lần tiêm lỗi có cảnh báo ở ít nhất hai service.
- **JSON valid rate** = số báo cáo qua kiểm tra / số lần gọi LLM.

### A.6 Chọn tham số trên `val`

Hai quy tắc được viết vào mã nguồn và commit **trước** lần chạy đầu tiên trên `val`:

1. $T_{group} \in \{180, 300, 600\}$ s: chỉ giữ các giá trị có ít sự cố mơ hồ nhất; mốc tham chiếu là 300 s nếu còn
   được giữ, không thì giá trị nhỏ nhất còn lại; một giá trị khác chỉ thay mốc khi Alert Reduction Ratio trên cảnh báo
   trong lỗi cao hơn với cận dưới CI95 ghép cặp lớn hơn 0. Chênh lệch nằm trong CI, hoặc hoà, thì giữ mốc.
2. Dấu hiệu bất thường của callee: mặc định chỉ tính service có cảnh báo CTAV; phương án tính thêm service có cửa sổ
   bị detector gắn cờ chỉ thay mặc định khi ΔHit@1 ghép cặp có cận dưới CI95 lớn hơn 0.

Kết quả: $T_{group} = 180$ s (1 sự cố mơ hồ, so với 2 ở 300 s và 600 s) và dấu hiệu mặc định (phương án kia thêm
+0,091 Hit@1, CI95 [0,000; +0,273]).

---

## B. Kết quả trên `val` (cho Ch5 §5.9, phần chọn tham số)

**Bảng 5.x-1. Đầu vào của tác tử RCA trên `val`.**

| | Số lượng |
|---|---:|
| Cảnh báo CTAV (`ctav_final_val_v1`) | 80 (8 service) |
| — giao thời gian với một lần tiêm lỗi | 36 (29 ở đúng pod bị tiêm, 7 ở pod / service khác) |
| — nằm ngoài mọi lần tiêm lỗi | 44 |
| Lần tiêm lỗi trên `val` | 30 |
| — có ít nhất một cảnh báo CTAV | 12 |
| — không có cảnh báo nào | 18 (5 / 5 `return`, 4 / 6 `exception`, 6 / 9 `network_delay`, 2 / 7 `cpu_contention`, 1 / 3 `cpu_consumed`) |

**Bảng 5.x-2. Quét $T_{group}$ trên `val`** (CI95 lấy mẫu lại theo 13 cụm thời gian của 600 s).

| $T_{group}$ | Sự cố | Có nhãn | Mơ hồ | Không ứng với lỗi | ARR mọi cảnh báo | ARR cảnh báo trong lỗi | ARR `network_delay` |
|---:|---:|---:|---:|---:|---|---|---|
| **180 s** | 26 | 11 | 1 | 14 | 0,675 [0,543; 0,728] | 0,667 [0,545; 0,733] | 0,250 [0,000; 0,500] |
| 300 s | 19 | 9 | 2 | 8 | 0,763 [0,585; 0,835] | 0,694 [0,550; 0,788] | 0,250 [0,000; 0,500] |
| 600 s | 17 | 9 | 2 | 6 | 0,788 [0,590; 0,865] | 0,694 [0,550; 0,788] | 0,250 [0,000; 0,500] |

**Bảng 5.x-3. Cấu hình chốt trên `val`** ($T_{group}$ = 180 s; Hit@k trên 11 sự cố có nhãn; ARR lấy mẫu lại theo 22
cụm thời gian).

| Chỉ số | Mức 1 (lan truyền ngược một bước) | Baseline (anomaly score cao nhất) | Chênh lệch ghép cặp |
|---|---|---|---|
| Hit@1 | 7 / 11 = 0,636 [0,364; 0,909] | 7 / 11 = 0,636 [0,364; 0,909] | 0,000 [0,000; 0,000] |
| Hit@3 | 7 / 11 = 0,636 [0,364; 0,909] | 7 / 11 = 0,636 [0,364; 0,909] | 0,000 [0,000; 0,000] |
| Hit@1 trên mọi lần tiêm lỗi | 6 / 30 = 0,200 [0,067; 0,333] | 6 / 30 = 0,200 | |

| Chỉ số | Giá trị [CI95] |
|---|---|
| ARR mọi cảnh báo (80 → 26 sự cố) | 0,675 [0,600; 0,730] |
| ARR cảnh báo trong lỗi (36 → 12) | 0,667 [0,565; 0,725] |
| ARR lỗi cascade (6 → 2; chỉ một lần tiêm lỗi) | 0,667 |
| ARR `network_delay` (4 → 3) | 0,250 [0,000; 0,500] |
| ARR `cpu_contention` (21 → 6) | 0,714 [0,667; 0,769] |
| JSON valid rate (26 lần gọi) | 1,000 |

**Bảng 5.x-4. Hit@1 theo loại lỗi trên `val`.**

| Loại lỗi | Lần tiêm lỗi | Có cảnh báo | Sự cố có nhãn | Trúng hạng 1 | Trúng / mọi lần tiêm lỗi |
|---|---:|---:|---:|---:|---:|
| `cpu_contention` | 7 | 5 | 6 | 5 | 4 / 7 |
| `cpu_consumed` | 3 | 2 | 2 | 2 | 2 / 3 |
| `network_delay` | 9 | 3 | 3 | 0 | 0 / 9 |
| `exception` | 6 | 2 | 0 (một sự cố mơ hồ) | — | 0 / 6 |
| `return` | 5 | 0 | 0 | — | 0 / 5 |

### Đoạn văn

Trên `val`, 80 cảnh báo của CTAV được gom thành 26 sự cố ($T_{group}$ = 180 s), tức số việc người vận hành phải xem
giảm 67,5% (CI95 [60,0%; 73,0%]). Mức giảm đến gần như hoàn toàn từ việc gom các cảnh báo liên tiếp của **cùng một
service**: 25 trong 26 sự cố chỉ có một service. Riêng với `network_delay`, mức giảm chỉ 25% và không đạt mục tiêu
30%. Nguyên nhân không nằm ở $T_{group}$ — ba giá trị cho cùng một con số — mà ở chỗ CTAV chỉ phát cảnh báo cho 3
trong 9 lần tiêm `network_delay`, mỗi lần một hoặc hai cảnh báo; với 4 cảnh báo thuộc 3 lỗi khác nhau, 25% là mức
giảm tối đa có thể đạt mà không gộp nhầm hai lỗi.

Trong 26 sự cố, 11 ứng với đúng một lần tiêm lỗi và được chấm định vị. Lan truyền ngược một bước tìm đúng service gốc
ở hạng 1 trong 7 sự cố (Hit@1 = 0,636, CI95 [0,364; 0,909]), **bằng đúng baseline** trên cả 11 sự cố: khi sự cố chỉ có
một service, mọi cách xếp hạng đều trả về chính service đó, và Hit@3 trùng Hit@1. Bốn sự cố trượt có chung một dạng —
cảnh báo xuất hiện ở một service khác service bị tiêm lỗi: cả ba sự cố `network_delay` (độ trễ mạng lộ ra ở service
gọi, không lộ ở service bị tiêm) và một sự cố `cpu_contention` mà service gốc cảnh báo muộn hơn service lân cận ba
phút. Tính trên cả 30 lần tiêm lỗi, service gốc được chỉ đúng ở 6 lần (0,200): 18 lần không có cảnh báo nào để bắt
đầu. Giới hạn của định vị trên `val` vì vậy đến từ độ phủ của cảnh báo đầu vào nhiều hơn là từ thuật toán xếp hạng.

Cả 26 báo cáo chẩn đoán do LLM viết đều qua kiểm tra lược đồ (JSON valid rate = 1,000), không báo cáo nào trích bằng
chứng ngoài ngữ cảnh hay đề xuất câu lệnh thực thi. Chỉ số này chỉ nói về hình thức: loại lỗi LLM ghi là
`cpu_contention` ở 22 / 26 báo cáo, kể cả ở 14 sự cố không ứng với lỗi nào, nên trường loại lỗi chưa mang thông tin
phân biệt; chất lượng nội dung được đánh giá bằng người ở mục sau (M11).

### Hạn chế cần nêu

- Mẫu nhỏ: 11 sự cố có nhãn; mỗi sự cố đổi kết quả làm Hit@1 thay đổi 0,09.
- CI của ARR cascade suy biến vì chỉ có một lần tiêm lỗi cascade.
- Nhãn mức service (QĐ-001), không phải mức pod.
- Việc chọn $T_{group}$ = 180 s dựa trên khác biệt đúng một sự cố mơ hồ (1 so với 2); quy tắc được viết trước nên
  kết quả được giữ, nhưng không nên diễn giải là 180 s "tốt hơn" 300 s.
