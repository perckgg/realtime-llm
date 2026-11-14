# Chương 5 — §5.7 Kết quả trên `test` (G-test, M8) và phần `test` của §5.8

> **Trạng thái bản nháp (2026-11-14, đang viết cuốn chiếu theo tiến độ M8).**
> Đã có số cuối: §5.7.1 (thiết lập), §5.7.2 (detector trên `test`), §5.7.3 (H0).
> **Chưa có:** §5.7.4 (H2), §5.7.5 (H3), §5.7.6 (H4), phần `test` của §5.8 — chờ run không-RAG, replay CTAV,
> C5 và `repeat`. Các mục đó hiện chỉ có khung, chưa có con số nào.
> Mọi số trong file này thuộc split `test` trừ khi ghi rõ `val`. "Chỉ số chính" = cửa sổ có telemetry
> (QĐ-016/017); "mọi cửa sổ" là phụ. Nguồn: `docs/experiment-log.md` QĐ-034..036 và `eval/results/*test*`.

## 5.7 Kết quả trên `test` (G-test)

### 5.7.1 Thiết lập và giao thức

Split `test` chỉ được dùng một lần, sau khi các giả thuyết H0–H5, tiêu chí chấp nhận và danh sách cấu hình đã
được đăng ký và commit riêng (2026-11-14, commit `be2b985`). Tại commit đó repo chưa có cấu hình hay kết quả nào
trên `test`. Từ thời điểm này không tham số nào của phương pháp được chỉnh: detector Isolation Forest (ngưỡng
0,85, fit trên `dev`), truy xuất BM25 và C1 (trọng số của bài báo, `k_graph` = 0), judge `gemini-2.5-flash`
(temperature 0), ngưỡng θ = 0,80 và C3 với ngưỡng nền p90 của `dev`. Mỗi cấu hình `test` là bản sao của cấu hình
`val` tương ứng, chỉ khác `run_id`, `split` và tên run đầu vào.

Theo quyết định của người thực hiện (V27), judge chấm **toàn bộ** candidate của `test`, không giới hạn ở cửa sổ có
telemetry. Khoảng tin cậy 95% lấy bằng bootstrap (1.000 mẫu, seed 42) cho từng chỉ số và cho hiệu ghép cặp; kiểm
định McNemar chính xác hai phía, α = 0,05. H2 là giả thuyết chính; H0, H3, H4 là phụ và được báo p thô, không
hiệu chỉnh đa so sánh.

**Bảng 5.14a. Các run trên `test`.**

| Run | Nội dung | Lần gọi LLM | Lần gọi API mới | Lỗi judge | USD theo token |
|---|---|---:|---:|---:|---:|
| `m8_test_detector_count_v1` | Chỉ detector (đếm candidate) | 0 | 0 | — | 0 |
| `h0_test_bm25_v1` | BM25 + judge | 13.699 | 13.699 | 0 | 8,87 |
| `h0_test_c1_k0_v1` | C1 + judge | 13.699 | 3.299 | 0 | 4,71 |
| `h0_test_norag_v1` | LLM-không-RAG | ⏳ | ⏳ | ⏳ | ⏳ |
| `ctav_final_test_v1` | Replay CTAV + ablation | ⏳ | 0 (replay) | — | 0 |
| `m8_rescue_test_c1_v1` | C5 một điểm | ⏳ | ⏳ | ⏳ | ⏳ |
| `h0_test_{bm25,c1_k0}_rep{1,2}_v1` | Phương sai judge, 200 cửa sổ | ⏳ | ⏳ | ⏳ | ⏳ |

C1 chỉ gọi API mới cho 3.299 candidate vì 10.400 candidate còn lại có cùng prompt với BM25 (không truy xuất được
bằng chứng nào) và được đọc từ cache.

### 5.7.2 Detector trên `test` và độ lệch so với `val`

Trước khi gọi judge, detector được chạy riêng trên `test` để đếm candidate. Kết quả cho thấy detector đưa lên
nhiều candidate hơn hẳn so với `val`, dù không tham số nào thay đổi (Bảng 5.14b).

**Bảng 5.14b. Detector đã đóng băng trên ba split.**

| | `dev` | `val` | `test` |
|---|---:|---:|---:|
| Cửa sổ | 19.316 | 28.898 | 46.849 |
| Candidate | 2.898 (15,0%) | 5.677 (19,6%) | 13.699 (29,2%) |
| Điểm anomaly p50 / p90 | 0,500 / 0,900 | 0,549 / 0,910 | 0,588 / 0,953 |
| Recall detector-only (fault là candidate) | 73 / 149 (0,490) | 109 / 209 (0,522) | 224 / 346 (0,647) |
| FPR detector-only, cửa sổ có telemetry | 825 / 4.881 (0,169) | 1.640 / 7.427 (0,221) | 3.435 / 11.639 (0,295) |
| Cửa sổ Online Boutique (2022-08): phần của split, tỉ lệ candidate | 25,8%; 28,2% | 13,2%; 42,8% | 21,8%; 66,8% |
| Cửa sổ TrainTicket (2023-01): tỉ lệ candidate | 10,4% | 16,1% | 18,8% |
| Service "luôn bật" (≥ 90% cửa sổ là candidate) | 2 | 3 | 5 |

Điểm anomaly là hạng phần trăm trên `dev`, nên ngưỡng 0,85 cho đúng 15% candidate trên `dev` theo cách dựng; ra
ngoài `dev` tỉ lệ này tăng dần. Độ lệch giữa `val` và `test` đến từ thành phần service của mỗi split chứ không từ
một ngày bất thường. Split được chia theo lần tiêm lỗi, nên tập service của từng split khác nhau: `test` có nhiều
cửa sổ Online Boutique hơn `val` (21,8% so với 13,2%), và ở đó tỉ lệ candidate cao hơn hẳn (66,8% so với 42,8%),
trong khi phần TrainTicket chỉ tăng từ 16,1% lên 18,8%. Năm service gần như luôn vượt ngưỡng trên `test`
(`checkoutservice`, `currencyservice`, `frontend`, `productcatalogservice`, `ts-ui-dashboard`) cho 6.407 candidate,
tức 47% số candidate của `test`; riêng `frontend` không có cửa sổ nào trong `val`.

Độ lệch này có ba hệ quả cho việc đọc các kết quả phía sau. Thứ nhất, mọi so sánh `val` cạnh `test` phải tính tới
việc mẫu số candidate đã khác: detector-only trên `test` có recall 0,647 và FPR 0,295, cao hơn `val` ở cả hai chiều.
Thứ hai, trên đường ngân sách của H4, mức "đủ" trên `test` là 13.699 lần gọi thay vì 5.677; mốc 4.000 lần gọi chỉ
phủ 29% candidate của `test` (70% trên `val`) và nằm trọn trong ngày 2022-08-22, tức chỉ phản ánh Online Boutique.
Thứ ba, chi phí chấm BM25 trên `test` gấp 2,4 lần `val`. Phân tích này thuần mô tả: ngưỡng detector không được
chỉnh và không cấu hình detector nào khác được chạy.

### 5.7.3 H0 — topology chưa hiệu chỉnh tăng recall và tăng FPR

H0 phát biểu rằng truy xuất theo topology chưa hiệu chỉnh (C1) làm tăng cả recall lẫn tỉ lệ cảnh báo sai so với
BM25. Tiêu chí chấp nhận đã đăng ký gồm bốn vế, đều phải đạt.

**Bảng 5.14c. BM25, C1 và detector-only trên `test`.**

| Phương pháp | Tập cửa sổ | TP | FP | Precision | Recall | F1 | FPR |
|---|---|---:|---:|---:|---:|---:|---:|
| BM25 | có telemetry (11.985; 346 fault) | 34 | 369 | 0,084 | 0,098 | 0,091 | 0,0317 |
| C1 | có telemetry | 96 | 1.235 | 0,072 | 0,277 | 0,115 | 0,1061 |
| Detector-only | có telemetry | 224 | 3.435 | 0,061 | 0,647 | 0,112 | 0,2951 |
| BM25 | mọi cửa sổ (46.849) | 34 | 369 | 0,084 | 0,098 | 0,091 | 0,0079 |
| C1 | mọi cửa sổ | 96 | 1.235 | 0,072 | 0,277 | 0,115 | 0,0266 |
| Detector-only | mọi cửa sổ | 224 | 13.475 | 0,016 | 0,647 | 0,032 | 0,2898 |

**Bảng 5.14d. H0 theo tiêu chí đã đăng ký (C1 − BM25, cửa sổ có telemetry), cạnh kết quả `val`.**

| Vế của tiêu chí | `test` | Kết quả | `val` (tham chiếu, M4) |
|---|---|---|---|
| CI ΔRecall có cận dưới > 0 | +0,179 [+0,138; +0,226] | **đạt** | +0,100 [+0,052; +0,155] |
| CI ΔFPR có cận dưới > 0 | +0,0744 [+0,0694; +0,0798] | **đạt** | +0,0254 [+0,0204; +0,0306] |
| McNemar trên fault, p < 0,05 | p < 0,001 (C1 đúng / BM25 sai: 65; ngược lại: 3) | **đạt** | p < 0,001 (28; 7) |
| McNemar trên normal, p < 0,05 | p < 0,001 (BM25 đúng / C1 sai: 966; ngược lại: 100) | **đạt** | p < 0,001 (276; 87) |
| ΔF1 (báo kèm, không thuộc tiêu chí) | +0,024 [−0,001; +0,052] | — | +0,023 [−0,004; +0,052] |

**H0 được chấp nhận trên `test`:** cả bốn vế đều đạt. So với BM25, C1 bắt thêm 62 fault (96 so với 34 TP) nhưng
sinh thêm 866 cảnh báo sai (1.235 so với 369 FP): recall tăng 0,179 trong khi FPR tăng 0,074, tức cao gấp 3,3 lần.
Hiện tượng đã thấy trên `val` (M4) lặp lại trên `test` với biên độ lớn hơn ở cả hai chiều. Như trên `val`, F1 của
C1 không cao hơn BM25 một cách có ý nghĩa (khoảng tin cậy của ΔF1 chứa 0): phần recall thu được bị bù bởi cảnh
báo sai. F1 của C1 (0,115) xấp xỉ detector-only (0,112), còn BM25 thấp hơn (0,091); khác biệt giữa hai phương pháp
có judge và detector-only nằm ở chỗ chúng đánh đổi recall lấy FPR thấp hơn nhiều.

Kết quả này xác nhận vấn đề mà luận văn đặt ra: đưa bằng chứng theo topology vào judge mà không hiệu chỉnh làm
judge xác nhận nhiều cảnh báo hơn, kể cả cảnh báo sai. Lưu ý rằng H0 kiểm hiện tượng, không kiểm cơ chế: trên
`val`, phần tăng này không đến từ bằng chứng của service lân cận mà từ việc C1 chọn span sát thời điểm cảnh báo
(Phát hiện 7, §5.6.1); cơ chế đó không được kiểm lại trên `test`.

### 5.7.4 H2 — CTAV so với BM25 (giả thuyết chính)

⏳ Chưa có số. Cần `ctav_final_test_v1` (replay) và run không-RAG.

### 5.7.5 H3 — đóng góp của từng thành phần

⏳ Chưa có số. Gồm: bỏ C3, +C2 (θ_topo 0,85), +C4, C3-trượt, C5 một điểm; kèm kiểm tra Phát hiện 11 trên `test`.

### 5.7.6 H4 — ngân sách nhỏ

⏳ Chưa có số.

### 5.7.7 Phương sai của judge và chi phí

⏳ Chưa có số (`repeat` 1, 2 trên 200 cửa sổ; chi phí thực so với ước ở QĐ-035).

## 5.8 Ablation và đường cong — phần `test`

⏳ Chưa có số (ablation H3 và đường F1 theo ngân sách trên `test`).
