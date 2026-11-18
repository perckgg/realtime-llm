# Chương 5 — §5.7 Kết quả trên `test` (G-test, M8) và phần `test` của §5.8

> **Trạng thái bản nháp (cập nhật 2026-11-16 — hoàn tất toàn bộ các run M8).**
> Đã có số cuối cho toàn bộ §5.7 (§5.7.1–§5.7.8: giao thức, độ lệch detector, bức tranh chung, kiểm định H0, H2,
> H3, H4 và bảng tổng hợp) và §5.8.1–§5.8.5 (ablation thành phần `val` cạnh `test`, Phát hiện 11 trên `test`,
> đường F1 theo ngân sách, C5 một điểm, độ ổn định `repeat` và chi phí thực tế).
> Riêng §5.8.6 (Bảng T15 — context precision chấm tay 50 cửa sổ) đã xuất mẫu mù tại
> `eval/manual/context_precision_test_v1.csv`, chờ người thực hiện chấm (V35 (a), QĐ-037).
> Mọi số trong file này thuộc split `test` trừ khi ghi rõ `val`. "Chỉ số chính" = cửa sổ có telemetry
> (QĐ-016/017); "mọi cửa sổ" là phụ. Nguồn: `docs/experiment-log.md` QĐ-034..038 và `eval/results/*test*`.

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

**Bảng 5.14a (T1). Các lần chạy trên `test` (`test`, toàn bộ 46.849 cửa sổ, 13.699 candidate).**

| Run | Nội dung | Lần gọi LLM | Lần gọi API mới | Lỗi judge | USD mới theo token |
|---|---|---:|---:|---:|---:|
| `m8_test_detector_count_v1` | Chỉ detector (đếm candidate) | 0 | 0 | — | 0 |
| `h0_test_bm25_v1` | BM25 + judge | 13.699 | 13.699 | 0 | 8,87 |
| `h0_test_c1_k0_v1` | C1 + judge | 13.699 | 3.299 | 0 | 4,71 |
| `h0_test_norag_v2` | LLM-không-RAG (tiếp cache `_v1`) | 13.699 | 3.287 | 0 | 1,10 |
| `h0_test_{bm25,c1_k0,norag}_b120_v1` | Ba run ngân sách 120 lần gọi | 3 × 120 | 0 | 0 | 0 |
| `ctav_final_test_v1` | Replay CTAV + 4 biến thể ablation | 0 (replay) | 0 | — | 0 |
| `m8_rescue_test_c1_v1` | C5 một điểm (chỉ chấm cửa sổ được cứu) | 61 | 61 | 0 | 0,09 |
| `h0_test_{bm25,c1_k0}_rep{1,2}_v1` | Phương sai judge, 4 run × 200 cửa sổ | 800 | 748 | 0 | 1,08 |
| **Tổng cộng M8** | | | **21.094** | **0** | **15,85** |

*Nguồn: `runtime.json` và sổ cái `data/llm_cache/gemini.jsonl` (dòng 19.157–40.251) của các run trên.*

C1 chỉ gọi API mới cho 3.299 candidate vì 10.400 candidate còn lại có cùng prompt với BM25 (không truy xuất được
bằng chứng nào) và được đọc từ cache. Tương tự, `h0_test_norag_v2` tái sử dụng 10.412 câu rỗng của BM25 và 2.917
câu đã lưu trong lần chạy `_v1` bị ngắt giữa chừng (thư mục `h0_test_norag_v1` rỗng được giữ nguyên theo quy tắc
không ghi đè, chỉ hỏi nốt 370 câu ở `_v2`); ở bốn run `repeat`, mỗi run C1 cũng tái sử dụng 26 câu rỗng tương ứng
của BM25 cùng `repeat`.

### 5.7.2 Detector trên `test` và độ lệch giữa các split

Trước khi gọi judge, detector được chạy riêng trên `test` để đếm candidate. Kết quả cho thấy detector đưa lên
nhiều candidate hơn hẳn so với `val`, dù không tham số nào thay đổi (Bảng 5.14b).

**Bảng 5.14b (T2). Detector đã đóng băng trên ba split (`dev`: 19.316 cửa sổ, 149 fault; `val`: 28.898, 209; `test`: 46.849, 346).**

| | `dev` | `val` | `test` |
|---|---:|---:|---:|
| Cửa sổ | 19.316 | 28.898 | 46.849 |
| Candidate | 2.898 (15,0%) | 5.677 (19,6%) | 13.699 (29,2%) |
| Điểm anomaly p50 / p90 | 0,500 / 0,900 | 0,549 / 0,910 | 0,588 / 0,953 |
| Recall detector-only (fault là candidate) | 73 / 149 (0,490) | 109 / 209 (0,522) | 224 / 346 (0,647) |
| FPR detector-only, cửa sổ có telemetry | 825 / 4.881 (0,1693) | 1.640 / 7.427 (0,2208) | 3.435 / 11.639 (0,2951) |
| Cửa sổ Online Boutique (2022-08): phần của split, tỉ lệ candidate | 25,8%; 28,2% | 13,2%; 42,8% | 21,8%; 66,8% |
| Cửa sổ TrainTicket (2023-01): tỉ lệ candidate | 10,4% | 16,1% | 18,8% |
| Service "luôn bật" (≥ 90% cửa sổ là candidate) | 2 | 3 | 5 |

*Nguồn: `eval/results/m8_detector_shift_test_v1/` (`m8_test_shift_dev_detector_v1`, `val_detector_count_v1`, `m8_test_detector_count_v1`).*

Điểm anomaly là hạng phần trăm trên `dev`, nên ngưỡng 0,85 cho đúng 15% candidate trên `dev` theo cách dựng; ra
ngoài `dev` tỉ lệ này tăng dần. Độ lệch giữa `val` và `test` đến từ thành phần service của mỗi split chứ không từ
một ngày bất thường. Split được chia theo lần tiêm lỗi, nên tập service của từng split khác nhau: `test` có nhiều
cửa sổ Online Boutique hơn `val` (21,8% so với 13,2%), và ở đó tỉ lệ candidate cao hơn hẳn (66,8% so với 42,8%),
trong khi phần TrainTicket chỉ tăng từ 16,1% lên 18,8%. Năm service gần như luôn vượt ngưỡng trên `test`
(`checkoutservice`, `currencyservice`, `frontend`, `productcatalogservice`, `ts-ui-dashboard`) cho 6.407 candidate,
tức 47% số candidate của `test`; riêng `frontend` không có cửa sổ nào trong `val`.

Độ lệch này có ba hệ quả cho việc đọc các kết quả phía sau. Thứ nhất, mọi so sánh `val` cạnh `test` phải tính tới
việc mẫu số candidate đã khác: detector-only trên `test` có recall 0,647 và FPR 0,2951, cao hơn `val` ở cả hai chiều.
Thứ hai, trên đường ngân sách của H4, mức "đủ" trên `test` là 13.699 lần gọi thay vì 5.677; mốc 4.000 lần gọi chỉ
phủ 29% candidate của `test` (70% trên `val`) và nằm trọn trong ngày 2022-08-22, tức chỉ phản ánh Online Boutique.
Thứ ba, chi phí chấm BM25 trên `test` gấp 2,4 lần `val`. Phân tích này thuần mô tả: ngưỡng detector không được
chỉnh và không cấu hình detector nào khác được chạy.

### 5.7.3 Bức tranh chung trên `test`

Bảng 5.14c đặt cả năm phương pháp trên `test` cạnh các chỉ số tham chiếu trên `val` trước khi đi vào từng giả
thuyết. Trên mặt phẳng Recall–FPR của tập cửa sổ có telemetry, năm phương pháp phân bố dọc theo một đường đánh
đổi rõ rệt: detector-only nằm ở góc trên bên phải với recall cao nhất (0,647) nhưng cứ ba cửa sổ bình thường có
telemetry lại báo động gần một lần (FPR 0,2951); C1 giữ được hơn một phần tư số fault (recall 0,277) với FPR giảm
gần ba lần so với detector-only (0,1061); BM25 và LLM-không-RAG nằm gần như trùng nhau ở vùng trung gian (recall
0,098 và 0,107; FPR 0,0317 và 0,0319); còn CTAV nằm ở góc dưới bên trái với FPR thấp nhất toàn bảng (0,0055, chỉ
64 cảnh báo sai trên 11.639 cửa sổ bình thường) và precision cao nhất (0,179), nhưng recall cũng giảm xuống 0,040
(14 TP).

**Bảng 5.14c (T3). Các phương pháp trên `test` (cửa sổ có telemetry: 11.985 cửa sổ, 346 fault), cạnh `val` (7.636 cửa sổ, 209 fault).**

| Phương pháp | `test`: TP | FP | Precision | Recall [CI95] | F1 [CI95] | FPR [CI95] | `val`: Recall | F1 | FPR |
|---|---:|---:|---:|---|---|---|---:|---:|---:|
| Detector-only | 224 | 3.435 | 0,061 | 0,647 [0,601; 0,699] | 0,112 [0,100; 0,126] | 0,2951 [0,2870; 0,3036] | 0,522 | 0,111 | 0,2208 |
| LLM-không-RAG | 37 | 371 | 0,091 | 0,107 [0,077; 0,139] | 0,098 [0,071; 0,126] | 0,0319 [0,0288; 0,0351] | 0,086 | 0,092 | 0,0224 |
| BM25 | 34 | 369 | 0,084 | 0,098 [0,070; 0,130] | 0,091 [0,064; 0,119] | 0,0317 [0,0285; 0,0350] | 0,163 | 0,103 | 0,0561 |
| C1 | 96 | 1.235 | 0,072 | 0,277 [0,230; 0,321] | 0,114 [0,093; 0,135] | 0,1061 [0,1007; 0,1118] | 0,263 | 0,126 | 0,0816 |
| **CTAV** | 14 | 64 | 0,179 | 0,040 [0,022; 0,061] | 0,066 [0,036; 0,100] | 0,0055 [0,0042; 0,0069] | 0,139 | 0,201 | 0,0069 |

*Nguồn: `eval/results/m8_test_tables_v1/tables.md` (`h0_test_bm25_v1`, `h0_test_c1_k0_v1`, `h0_test_norag_v2`, `ctav_final_test_v1`) và `ctav_final_val_v1`.*

So với `val`, thứ tự theo trục FPR được bảo toàn hoàn toàn (`CTAV < BM25 ≈ không-RAG < C1 < detector-only`), và
khoảng cách giữa C1 với BM25 mở rộng ở cả recall lẫn FPR. Điểm dịch chuyển đáng chú ý nhất nằm ở F1 của CTAV:
trên `val`, CTAV đạt F1 cao nhất (0,201) nhờ giữ được 29/55 TP của C1 trong khi cắt 91,6% FP; sang `test`, tỉ lệ
cắt FP của CTAV vẫn mạnh tương đương (từ 1.235 xuống 64 FP, tức cắt 94,8%), nhưng số TP giữ lại giảm từ 96 xuống
14, kéo F1 xuống 0,066. Ngoài ra, trên tập phụ gồm **mọi cửa sổ** (46.849 cửa sổ), BM25, C1 và CTAV giữ nguyên số
TP và FP vì luật `require_evidence` tự động bác bỏ candidate không có bằng chứng, trong khi LLM-không-RAG
(`require_evidence: false`) sinh thêm 832 cảnh báo sai trên các cửa sổ không có telemetry (tổng 1.203 FP, F1 tụt
xuống 0,047).

### 5.7.4 H0 — topology chưa hiệu chỉnh tăng recall và tăng FPR

H0 phát biểu rằng truy xuất theo topology chưa hiệu chỉnh (C1) làm tăng cả recall lẫn tỉ lệ cảnh báo sai so với
BM25. Theo bản đăng ký, H0 chỉ được chấp nhận khi đồng thời đạt cả bốn vế: khoảng tin cậy 95% của
`ΔRecall(C1 − BM25)` có cận dưới > 0, khoảng tin cậy 95% của `ΔFPR(C1 − BM25)` có cận dưới > 0, kiểm định McNemar
trên cửa sổ fault có `p < 0,05`, và kiểm định McNemar trên cửa sổ normal có `p < 0,05`.

**Bảng 5.14d (T4). H0 theo tiêu chí đã đăng ký (`test`, cửa sổ có telemetry: 11.985 cửa sổ, 346 fault), cạnh `val` (7.636; 209).**

| Vế của tiêu chí | `test` | Kết quả | `val` (tham chiếu, M4) |
|---|---|---|---|
| CI ΔRecall(C1 − BM25) có cận dưới > 0 | +0,179 [+0,138; +0,226] | **đạt** | +0,100 [+0,052; +0,155] |
| CI ΔFPR(C1 − BM25) có cận dưới > 0 | +0,0744 [+0,0694; +0,0798] | **đạt** | +0,0254 [+0,0204; +0,0306] |
| McNemar trên fault, p < 0,05 | p < 0,001 (C1 đúng / BM25 sai: 65; ngược lại: 3) | **đạt** | p < 0,001 (28; 7) |
| McNemar trên normal, p < 0,05 | p < 0,001 (BM25 đúng / C1 sai: 966; ngược lại: 100) | **đạt** | p < 0,001 (276; 87) |
| ΔF1 (báo kèm, không thuộc tiêu chí) | +0,024 [−0,001; +0,052] | — | +0,023 [−0,004; +0,052] |

*Nguồn: `eval/results/h0_test_compare_bm25ref_v1/compare.json` và `eval/results/m8_test_tables_v1/tables.md`.*

**H0 được chấp nhận trên `test`.** So với BM25, C1 bắt thêm 62 fault (96 so với 34 TP; có 65 cửa sổ fault C1 bắt
đúng mà BM25 bỏ sót, chiều ngược lại chỉ 3) nhưng đồng thời sinh thêm 866 cảnh báo sai (1.235 so với 369 FP; có
966 cửa sổ bình thường BM25 giữ đúng mà C1 báo sai): recall tăng 0,179 trong khi FPR tăng 0,0744, tức cao gấp 3,3
lần. Hiện tượng đã quan sát trên `val` (M4) lặp lại trên `test` với biên độ lớn hơn ở cả hai chiều, và tương tự
`val`, khoảng tin cậy của ΔF1 vẫn chứa 0 (`[−0,001; +0,052]`) do phần recall thu thêm bị trung hòa bởi cảnh báo sai.
Lưu ý rằng H0 kiểm định hiện tượng đầu ra chứ không kiểm định lại cơ chế: trên `val`, sự gia tăng này đến từ việc
C1 chọn trace span của chính service bị cảnh báo sát thời điểm `t_0` hơn BM25 chứ không đến từ bằng chứng của
service lân cận (Phát hiện 7, §5.6.1), và thí nghiệm cơ chế đó không chạy lại trên `test`.

### 5.7.5 H2 — CTAV so với BM25 (giả thuyết chính)

H2 là giả thuyết chính của luận văn, kiểm tra liệu CTAV đã đóng băng (`C1 + θ = 0,80 + C3` với ngưỡng nền `dev`
p90) có vượt BM25 mà vẫn giữ được phần lớn recall của C1 hay không. Ba vế tiêu chí đã đăng ký nguyên văn gồm:
(i) khoảng tin cậy 95% của `ΔF1(CTAV − BM25)` có cận dưới > 0 và McNemar `p < 0,05`; (ii) FPR không tệ hơn BM25
một cách có ý nghĩa, tức khoảng tin cậy 95% của `ΔFPR(CTAV − BM25)` không có cận dưới > 0; và (iii) ước lượng điểm
`ΔRecall(CTAV − C1) ≥ −δ` với `δ = 0,05` (quy ước đã đăng ký: nếu đạt (i) và (ii) nhưng không đạt (iii) thì ghi
"H2 đạt một phần").

**Bảng 5.15 (T5). H2 theo tiêu chí đã đăng ký (`test`, cửa sổ có telemetry: 11.985 cửa sổ, 346 fault), cạnh `val` (7.636; 209).**

| Vế | So sánh | Số đo trên `test` | Kết quả | `val` |
|---|---|---|---|---|
| (i) CI ΔF1 cận dưới > 0 và McNemar p < 0,05 | CTAV − BM25 | −0,025 [−0,067; +0,014]; McNemar p < 0,001 | **không đạt** | +0,098 [+0,046; +0,149]; p < 0,001 |
| (ii) CI ΔFPR không có cận dưới > 0 | CTAV − BM25 | −0,0262 [−0,0297; −0,0229] | **đạt** | −0,0493 [−0,0545; −0,0439] |
| (iii) ΔRecall ≥ −0,05 (ước lượng điểm) | CTAV − C1 | −0,237 [−0,281; −0,193] | **không đạt** | −0,124 [−0,170; −0,079] (không đạt) |
| Phụ: ΔPrecision | CTAV − BM25 | +0,095 [+0,014; +0,186] | — | +0,279 [+0,173; +0,393] |
| Phụ: ΔRecall | CTAV − BM25 | −0,058 [−0,095; −0,022] | — | −0,024 [−0,071; +0,020] |
| Phụ: ΔF1 | CTAV − C1 | −0,048 [−0,079; −0,013] | — | +0,074 [+0,027; +0,124] |
| Phụ: ΔF1 | CTAV − LLM-không-RAG | −0,032 [−0,075; +0,008] | — | +0,109 [+0,051; +0,174] |
| **Kết luận H2** | | | **không được chấp nhận** | đạt một phần (sơ bộ) |

*Nguồn: `eval/results/m8_test_tables_v1/tables.md` (`h0_test_compare_bm25ref_v1`, `h0_test_compare_c1ref_v1`, `ctav_final_test_v1`).*

**H2 không được chấp nhận trên `test`.**

Đọc theo số đếm cụ thể trên 11.985 cửa sổ có telemetry, vế (ii) đạt rất sâu: CTAV cắt 305 cảnh báo sai so với BM25
(từ 369 xuống 64 FP, giảm 5,8 lần, `ΔFPR = −0,0262`) và cắt tới 1.171 cảnh báo sai so với C1 (từ 1.235 xuống 64
FP, giảm 94,8%), nhờ đó precision tăng hơn gấp đôi so với BM25 (từ 0,084 lên 0,179, `ΔPrecision = +0,095
[+0,014; +0,186]`). Tuy nhiên, cùng bộ lọc C3 đó cũng làm rơi 82 trong số 96 fault mà C1 đã bắt được (còn 14 TP,
thấp hơn cả 34 TP của BM25; McNemar riêng trên 346 cửa sổ fault có `p = 0,004` nghiêng về BM25). Vì mất quá nhiều
TP, vế (iii) bị vi phạm nặng (`ΔRecall = −0,237 < −0,05`) và vế (i) không đạt (`ΔF1 = −0,025 [−0,067; +0,014]`,
khoảng tin cậy chứa 0; kiểm định McNemar tổng thể có `p < 0,001` là do CTAV phân loại đúng hơn trên 305 cửa sổ
normal chứ không phải do tăng F1).

Đối chiếu với `val`, chiều giảm FPR của CTAV lặp lại nhất quán trên cả hai split (FPR 0,0069 trên `val` và 0,0055
trên `test`), nhưng mức sụt recall so với C1 tăng gần gấp đôi (từ `−0,124` trên `val` lên `−0,237` trên `test`),
khiến kết luận chuyển từ "đạt một phần" trên `val` sang "không được chấp nhận" trên `test`; ở các so sánh phụ,
khoảng tin cậy của `ΔF1(CTAV − LLM-không-RAG)` chứa 0 (`[−0,075; +0,008]`) còn `ΔF1(CTAV − C1)` âm (`−0,048`).
Nguyên nhân trực tiếp khiến 82/96 TP của C1 bị hạ nằm ở chỗ 61,0% cửa sổ fault của `test` rơi vào 32 service không
có ngưỡng nền `dev` trong `data/span_baseline.parquet` — hiện tượng đã cảnh báo trước ở Phát hiện 11 và được định
lượng riêng tại §5.8.2 cùng biến thể đối chứng ngưỡng trượt `c3_rolling_baseline`.

### 5.7.6 H3 — đóng góp của từng thành phần

H3 kiểm tra từng thành phần quanh cấu hình CTAV theo thiết kế một-thay-đổi-một-lần đã đăng ký: với thành phần đang
giữ là C3, khi bỏ C3 (`no_c3`) khoảng tin cậy 95% của `ΔPrecision` phải có cận trên < 0; với hai thành phần đã bỏ
từ M6 là C2 (thêm ngưỡng bất đối xứng `θ_topo = 0,85`, `with_c2`) và C4 (thêm định tuyến hai tầng với
`fp_confidence = 0,95`, `with_c4`), quyết định bỏ được xác nhận nếu thêm C2 cho khoảng tin cậy `ΔFPR` chứa 0 hoặc
> 0, và nếu thêm C4 làm tăng chi phí mà khoảng tin cậy `ΔF1` không có cận dưới > 0. Hai biến thể `C3-trượt`
(`c3_rolling_baseline`) và `C5` một điểm (`η = (0; 0,4; 0,6), τ = 0,8`) được đăng ký để báo mô tả biến thiên mà
không gắn ngưỡng đạt/không đạt.

**Bảng 5.16 (T6). H3 theo tiêu chí đã đăng ký (`test`, cửa sổ có telemetry: 11.985 cửa sổ, 346 fault), cạnh `val` (7.636; 209).**

| Thành phần | Tiêu chí đã đăng ký | Số đo trên `test` | Kết quả | `val` |
|---|---|---|---|---|
| C3 (đang dùng) | bỏ C3 ⇒ CI ΔPrecision cận trên < 0 | −0,107 [−0,197; −0,030] | **đạt** (C3 đóng góp) | −0,279 [−0,382; −0,187] (đạt) |
| C2 (đã bỏ) | thêm C2: xác nhận bỏ nếu CI ΔFPR chứa 0 hoặc > 0 | +0,0000 [+0,0000; +0,0000] | **đạt** (xác nhận bỏ) | −0,0003 [−0,0007; 0,0000] (đạt) |
| C4 (đã bỏ) | thêm C4: xác nhận bỏ nếu chi phí tăng và CI ΔF1 không có cận dưới > 0 | −0,001 [−0,001; +0,000]; 13,56 so với 8,16 USD | **đạt** (xác nhận bỏ) | −0,013 [−0,030; +0,008]; 5,14 so với 3,28 USD (đạt) |
| C3-trượt | báo mô tả ΔF1, ΔFPR, ΔRecall | ΔF1 +0,054 [+0,017; +0,091]; ΔFPR +0,0281; ΔRecall +0,095 | — | ΔF1 −0,064; ΔFPR +0,0275 |
| C5 một điểm | báo mô tả ΔRecall, ΔFPR, số lần gọi thêm | ΔRecall +0,000; ΔFPR +0,0001; +61 lần gọi | — | +0,010; +0,0022; +52 lần gọi |

*Nguồn: `eval/results/m8_test_tables_v1/tables.md` (`ctav_final_test_v1`, `m8_rescue_test_v1`) và `ctav_final_val_v1`, `m7_rescue_val_v1`.*

**Cả ba tiêu chí thành phần của H3 đều được chấp nhận trên `test`.** Khi bỏ C3, cảnh báo sai tăng vọt từ 64 lên
1.235 FP kéo precision tụt 0,107 (từ 0,179 xuống 0,072); thêm lại C2 không làm đổi bất kỳ quyết định cuối cùng nào
(0 TP, 0 FP thay đổi vì cả 54 cảnh báo bị C2 hạ đều đã bị C3 hạ trước đó); còn thêm lại C4 làm tốn thêm 3.286 lần
gọi LLM (16.985 so với 13.699 lần gọi) và sinh thêm 4 FP mà không thêm TP nào. Hai kết quả mô tả cho thấy đối cực
rõ nét với `val`: C5 tiếp tục không cứu được fault nào (+0 TP, +1 FP), trong khi thay ngưỡng tĩnh `dev` bằng
`C3-trượt` làm tăng thêm 33 TP (từ 14 lên 47 TP) và nâng F1 thêm `+0,054 [+0,017; +0,091]` (lên 0,120), đảo chiều
so với `val` do độ phủ ngưỡng `dev` trên `test` quá thấp (§5.8.1–§5.8.2).

### 5.7.7 H4 — ngân sách nhỏ

H4 kiểm tra hành vi khi ngân sách gọi LLM bị khống chế chặt ở 120 lần gọi đầu tiên theo thứ tự thời gian, với tiêu
chí đã đăng ký nguyên văn là ước lượng điểm `F1(CTAV) ≥ F1(LLM-không-RAG)` ở mốc 120 lần gọi (kèm báo khoảng tin
cậy 95% và toàn bộ đường ngân sách tại §5.8.3).

**Bảng 5.17 (T7). Các phương pháp ở ngân sách 120 lần gọi LLM (`test`, cửa sổ có telemetry: 11.985 cửa sổ, 346 fault), cạnh `val` (7.636; 209).**

| Phương pháp | `test`: TP | FP | Precision | Recall | F1 [CI95] | `val`: F1 |
|---|---:|---:|---:|---:|---|---:|
| **CTAV** | 6 | 0 | 1,000 | 0,017 | **0,034 [0,011; 0,064]** | 0,028 |
| LLM-không-RAG | 3 | 3 | 0,500 | 0,009 | 0,017 [0,000; 0,038] | 0,000 |
| BM25 | 3 | 3 | 0,500 | 0,009 | 0,017 [0,000; 0,038] | 0,016 |
| C1 | 11 | 23 | 0,324 | 0,032 | 0,058 [0,026; 0,092] | 0,023 |

*Nguồn: `eval/results/ctav_final_test_v1/ctav.json` (khớp 100% với `h0_test_{bm25,c1_k0,norag}_b120_v1`) và `ctav_final_val_v1/ctav.json`.*

**H4 được chấp nhận trên `test`.** Trong 120 candidate đầu tiên, CTAV giữ 6 TP với 0 FP (`Precision = 1,000`,
`F1 = 0,034`), gấp đôi số TP của LLM-không-RAG và BM25 (cùng 3 TP, 3 FP, `F1 = 0,017`), lặp lại đúng chiều đã thấy
trên `val` (`0,028` so với `0,000`), trong khi C1 đạt `0,058` (11 TP, 23 FP). Tuy nhiên, kết quả này phải đọc kèm
hai giới hạn chặt: 120 lần gọi chỉ chiếm 0,9% tổng số candidate của `test` (120 / 13.699) nên khoảng tin cậy của F1
rất rộng và chồng nhau giữa CTAV với LLM-không-RAG; đồng thời toàn bộ 120 candidate đầu tiên đều thuộc đầu ngày
2022-08-22 (Online Boutique), nơi `frontend` có sẵn ngưỡng `dev` p90 nên C3 chưa gặp nút thắt mất độ phủ của các
service phía sau.

### 5.7.8 Tổng hợp kết quả kiểm định

Ghép bốn mục kiểm định lại, bức tranh thực nghiệm trên `test` tách bạch rõ hai phần: phần chẩn đoán vấn đề và vai
trò thành phần lặp lại hoàn toàn nhất quán với `val` (H0 được chấp nhận ở cả bốn vế; H3 xác nhận C3 là thành phần
duy nhất tạo khác biệt về precision và xác nhận việc loại bỏ C2, C4; H4 đạt ở mốc 120 lần gọi), trong khi giả
thuyết chính H2 bị bác bỏ trên cấu hình CTAV đóng băng vì C3 dùng ngưỡng tĩnh `dev` làm rơi phần lớn TP của C1 ở
các service mới xuất hiện hoặc ít xuất hiện trong `dev`. Bảng 5.18 tổng hợp trạng thái chính thức của toàn bộ sáu
giả thuyết H0–H5 để dẫn chiếu sang Chương 8.

**Bảng 5.18 (T8). Tổng hợp kết quả kiểm định H0–H5 trên `test` so với kết quả sơ bộ trên `val`.**

| Giả thuyết | So sánh kiểm định | Kết luận chính thức trên `test` | Kết luận sơ bộ trên `val` |
|---|---|---|---|
| **H0** | C1 − BM25 | **Được chấp nhận** (đạt 4/4 vế) | Được chấp nhận |
| **H1** | Thí nghiệm cơ chế trên mẫu dựng | *Không chạy lại trên `test`* | Giữ một phần (M5, QĐ-028) |
| **H2** (chính) | CTAV − BM25, CTAV − C1 | **Không được chấp nhận** (đạt vế (ii) FPR; không đạt vế (i) F1 và (iii) recall) | Đạt một phần (không đạt vế (iii)) |
| **H3** | Một-thay-đổi-một-lần quanh CTAV | **Được chấp nhận** (C3 đóng góp; xác nhận bỏ C2, C4; C3-trượt tăng F1 +0,054; C5 +0 TP) | C3 đóng góp; xác nhận bỏ C2, C4 |
| **H4** | CTAV và LLM-không-RAG ở 120 lần gọi | **Được chấp nhận** (ước lượng điểm 0,034 ≥ 0,017; CI chồng nhau) | Đạt (0,028 so với 0,000) |
| **H5** | Tác tử RCA trên sự cố gom từ cảnh báo CTAV | **Không được chấp nhận** (0/4 vế: Hit@1 = Hit@3 = 0,471 = baseline, ΔHit@1 = 0; không có lỗi cascade nên vế Alert Reduction không tính được) | Không đạt (đạt vế Hit@1 0,636 và ARR cascade 0,667 trên 1 lần tiêm lỗi; không đạt vế Hit@3 và ΔHit@1 = 0) |

*Nguồn: tổng hợp từ Bảng 5.14d–5.17 (`eval/results/m8_test_tables_v1/verdicts.json`), Bảng 5.26–5.27 (`eval/results/rca_final_test_v1/`, `eval/results/rca_final_val_v1/`) và QĐ-028, QĐ-038, QĐ-042.*

---

## 5.8 Phân tích thành phần, cơ chế và đường cong trên `test`

### 5.8.1 Ablation thành phần, `val` cạnh `test`

Bảng 5.19 đặt các biến thể quanh CTAV của `val` và `test` cạnh nhau để tách rõ đóng góp của từng tầng quyết định.
Đi theo phễu quyết định trên 11.985 cửa sổ có telemetry của `test` (346 fault, 11.639 normal): detector đưa lên
3.659 candidate (224 fault, 3.435 normal); judge với bằng chứng C1 trả `TRUE_ALERT` thô cho 1.418 cửa sổ (96 fault,
1.322 normal); luật `require_evidence` hạ 87 cửa sổ normal không trích mã sự kiện hợp lệ (và hạ thêm 883 cửa sổ ở
nhánh không có telemetry, tổng 970 cửa sổ trên toàn split), còn ngưỡng tin cậy `θ = 0,80` hạ 0 cửa sổ, để lại đúng
1.331 cảnh báo của C1 (96 TP, 1.235 FP). Ở tầng cuối cùng, C3 (`dev` p90) hạ tiếp **1.253 trong số 1.331 cảnh báo**
đó — gồm **1.171 cảnh báo sai** (cắt 94,8% FP) nhưng đồng thời hạ **82 cảnh báo đúng** (mất 85,4% TP của C1) — để
lại 78 cảnh báo cuối cùng của CTAV (14 TP, 64 FP).

**Bảng 5.19 (T9). Các biến thể ablation quanh CTAV trên `test` (11.985 cửa sổ có telemetry, 346 fault) cạnh `val` (7.636; 209).**

| Biến thể | `val`: TP / FP | Recall | F1 | FPR | `test`: TP / FP | Precision | Recall | F1 [CI95] | FPR | Lần gọi LLM (`test`) | USD (`test`) |
|---|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|
| **CTAV** (`dev` p90) | 29 / 51 | 0,139 | 0,201 | 0,0069 | 14 / 64 | 0,179 | 0,040 | 0,066 [0,036; 0,100] | 0,0055 | 13.699 | 8,16 |
| Bỏ C3 (`no_c3` = C1) | 55 / 606 | 0,263 | 0,126 | 0,0816 | 96 / 1.235 | 0,072 | 0,277 | 0,114 [0,093; 0,135] | 0,1061 | 13.699 | 8,16 |
| + C2 (`θ_topo = 0,85`) | 29 / 49 | 0,139 | 0,202 | 0,0066 | 14 / 64 | 0,179 | 0,040 | 0,066 [0,036; 0,100] | 0,0055 | 13.699 | 8,16 |
| + C4 (`fp_conf = 0,95`) | 31 / 90 | 0,148 | 0,188 | 0,0121 | 14 / 68 | 0,171 | 0,040 | 0,065 [0,036; 0,099] | 0,0058 | 16.985 | 13,56 |
| **C3-trượt** (60 phút p90) | 34 / 255 | 0,163 | 0,137 | 0,0343 | **47 / 391** | **0,107** | **0,136** | **0,120 [0,090; 0,151]** | **0,0336** | 13.699 | 8,16 |

*Nguồn: `eval/results/m8_test_tables_v1/tables.md` (`ctav_final_test_v1`) và `eval/results/ctav_final_val_v1/ctav.json`.*

Hai thành phần đã loại ở M6 tiếp tục tỏ ra dư thừa trên `test` vì đúng những cơ chế đã thấy trên `val`. Với C2,
judge trả `confidence ≥ 0,85` cho hầu hết câu trả lời `TRUE_ALERT`; 54 cửa sổ duy nhất có `0,80 ≤ confidence < 0,85`
đều không có bằng chứng bất thường tại `s_0` nên đã bị C3 bác bỏ trước, làm `with_c2` trùng khít từng cửa sổ với
CTAV (`McNemar p = 1,000`). Với C4, vì tầng 1 (BM25) chỉ tự tin trả `FALSE_POSITIVE` (`≥ 0,95`) ở một phần nhỏ
candidate có bằng chứng còn toàn bộ 10.412 candidate không có bằng chứng ở tầng 1 đều bị chuyển tiếp sang tầng 2,
định tuyến hai tầng phải gọi tổng cộng 16.985 lượt LLM (tốn 13,56 USD quy đổi cả cache so với 8,16 USD khi chạy
thẳng C1 một tầng) mà chỉ giữ thêm 4 FP từ tầng 1 (14 TP, 68 FP).

### 5.8.2 Ngưỡng `dev` và recall của CTAV (Phát hiện 11 trên `test`)

Để kiểm tra vì sao C3 (`dev` p90) chỉ làm giảm nhẹ recall trên `val` (29 so với 55 TP) nhưng lại làm rơi phần lớn
recall trên `test` (14 so với 96 TP), Bảng 5.20 tách tập cửa sổ có telemetry của cả hai split theo việc service bị
cảnh báo có ít nhất một ngưỡng thao tác trong `data/span_baseline.parquet` (dựng từ các cửa sổ bình thường của
`dev`) hay không. Vì `dev` chỉ chứa span hợp lệ của 14 service trong toàn bộ hệ thống và các service của Nezha gần
như không ghi log ERROR/WARN trực tiếp lên pod có cửa sổ metric (trừ `frontend`), bất kỳ service nào vắng mặt trong
bảng ngưỡng `dev` đều không thể có bằng chứng được neo bởi C3, đồng nghĩa mọi cảnh báo `TRUE_ALERT` của C1 trên các
service đó bị hạ về 0.

**Bảng 5.20 (T10). C1 và CTAV tách theo độ phủ ngưỡng nền `dev` của service (`val`: 7.636 cửa sổ, 209 fault; `test`: 11.985 cửa sổ, 346 fault).**

| Chỉ tiêu | `val`: có ngưỡng `dev` | `val`: không có | `test`: có ngưỡng `dev` | `test`: không có |
|---|---:|---:|---:|---:|
| Tổng số service có cửa sổ telemetry | 11 | 30 | 10 | 32 |
| Số service có fault | 8 | 10 | 9 | 11 |
| Cửa sổ có telemetry | 1.438 | 6.198 | 1.428 | 10.557 |
| Cửa sổ fault | 104 | 105 | 135 | 211 |
| Fault là candidate của detector | 50 | 59 | 93 | 131 |
| C1: TP | 32 | 23 | 29 | 67 |
| CTAV (`dev` p90): TP | 29 | **0** | 14 | **0** |
| C1: FP | 290 | 316 | 99 | 1.136 |
| CTAV (`dev` p90): FP | 51 | **0** | 64 | **0** |
| Recall của C1 | 0,308 | 0,219 | 0,215 | 0,318 |
| Recall của CTAV (`dev` p90) | 0,279 | **0,000** | 0,104 | **0,000** |

*Nguồn: `eval/results/m8_finding11_val_v1/tables.md` và `eval/results/m8_finding11_test_v1/tables.md`.*

Bảng 5.20 giải thích trọn vẹn sự đảo chiều giữa `val` và `test`. Trên `val`, nhóm có ngưỡng `dev` chiếm một nửa số
fault (104 / 209) và chứa 32 / 55 TP của C1 (như `recommendationservice` 13 TP, `cartservice` 7 TP), nơi CTAV giữ
được 29 / 32 TP (90,6%) trong khi cắt 239 / 290 FP; phần mất trắng ở nhóm thiếu ngưỡng chỉ là 23 TP (`0,110`
recall toàn tập). Ngược lại, do split được chia theo lần tiêm lỗi (§5.7.2), trên `test` có tới **88,1% cửa sổ có
telemetry** (10.557 / 11.985) và **61,0% cửa sổ fault** (211 / 346) rơi vào 32 service không có ngưỡng `dev` — bao
gồm hầu hết các service có nhiều TP nhất của C1 như `checkoutservice` (17 TP), `currencyservice` (10 TP),
`adservice` (9 TP), `ts-food-service` (9 TP), `productcatalogservice` (8 TP), `ts-preserve-service` (7 TP) và
`ts-basic-service` (5 TP). Toàn bộ **67 / 96 TP của C1** ở nhóm này bị hạ sạch về 0, làm CTAV mất ngay **0,194
recall** trên toàn tập (chưa kể 15 TP bị hạ tiếp ở nhóm có ngưỡng, chủ yếu tại `frontend` và `ts-travel-service`).

Đối chiếu với dòng `C3-trượt` ở Bảng 5.19 xác nhận rằng nút thắt nằm ở **cách ước lượng ngưỡng tĩnh từ một split
nhỏ (`dev`)**, không phải ở bản thân ý tưởng neo bằng chứng C3: khi ước lượng p90 trên cửa sổ trượt 60 phút ngay
trước thời điểm cảnh báo (nâng độ phủ span C1 từ 16,1% lên 91,2%, QĐ-037), C3 giữ lại được **47 TP** (nhiều hơn
BM25 13 TP, tức +38% số fault bắt được), đồng thời vẫn loại bỏ **844 / 1.235 cảnh báo sai của C1** (cắt 68,3% FP,
đưa FPR xuống 0,0336 — sát mức 0,0317 của BM25) và đạt F1 0,120 `[0,090; 0,151]`, cao hơn CTAV đóng băng một cách
có ý nghĩa thống kê (`ΔF1 = +0,054 [+0,017; +0,091]`, McNemar `p < 0,001`). Nói cách khác, trên `val` quy tắc chọn
đã ưu tiên `dev` p90 vì nó cắt sâu thêm FP trên các service quen thuộc, nhưng khi sang `test` có phân phối service
lệch mạnh, chỉ ngưỡng nền thích nghi theo lịch sử gần (`C3-trượt`) mới duy trì được cân bằng giữa giữ recall của
topology và kìm hãm cảnh báo sai.

### 5.8.3 Đường F1 theo ngân sách

Bảng 5.21 trình bày F1 của bốn phương pháp dọc theo đường ngân sách {120, 250, 500, 1.000, 2.000, 4.000, đủ} khi
các candidate được duyệt theo thứ tự thời gian như một luồng vận hành thực tế. Ở mốc rất nhỏ (120 lần gọi), CTAV
đứng trên BM25 và LLM-không-RAG nhờ lọc hết cảnh báo sai (6 TP, 0 FP); tuy nhiên từ mốc 500 đến 4.000 lần gọi,
đường CTAV đi ngang quanh 0,032–0,036 (7 TP, 39 FP ở mốc 1.000–4.000), thấp hơn BM25 (0,069), LLM-không-RAG
(0,073) và C1 (0,142), rồi mới tăng lên 0,066 khi mở hết ngân sách 13.699 candidate.

**Bảng 5.21 (T11). F1 theo ngân sách lần gọi LLM theo thứ tự thời gian (`test`, cửa sổ có telemetry: 11.985 cửa sổ, 346 fault; mức đủ = 13.699 candidate).**

| Phương pháp | 120 | 250 | 500 | 1.000 | 2.000 | 4.000 | Đủ (13.699) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **CTAV** | 0,034 | 0,033 | 0,032 | 0,036 | 0,036 | 0,036 | 0,066 |
| BM25 | 0,017 | 0,023 | 0,060 | 0,069 | 0,069 | 0,069 | 0,091 |
| C1 | 0,058 | 0,072 | 0,115 | 0,142 | 0,142 | 0,142 | 0,114 |
| LLM-không-RAG | 0,017 | 0,017 | 0,049 | 0,073 | 0,073 | 0,073 | 0,098 |

*Nguồn: `eval/results/m8_test_tables_v1/tables.md` (`ctav_final_test_v1/ctav.json`).*

Có hai hiện tượng kỹ thuật cần lưu ý khi so Bảng 5.21 với đường cong tương ứng trên `val`. Thứ nhất, cả bốn phương
pháp đều giữ nguyên con số giữa ba mốc 1.000, 2.000 và 4.000 lần gọi (ví dụ C1 giữ đúng 39 TP, 164 FP): lý do là
trong khoảng candidate thứ 1.001 đến 4.000 theo thời gian, các candidate phát sinh đều rơi vào những khoảng chạy
nền không có telemetry của ngày 2022-08-22 nên không làm đổi bất kỳ ô nào trên tập con có telemetry. Thứ hai, vì
ngày 2022-08-22 (Online Boutique) có tới 4.381 candidate, toàn bộ sáu mốc ngân sách hữu hạn {120 … 4.000} của
`test` chỉ phản ánh một ngày duy nhất của Online Boutique — nơi phần lớn fault sau mốc 120 nằm ở `checkoutservice`,
`currencyservice`, `adservice` và `productcatalogservice` (đều không có ngưỡng `dev`), khiến C1 tăng vọt lên 39 TP
(`F1 = 0,142`) còn CTAV dậm chân ở 7 TP; phải tới phần sau mốc 4.381 mới chạm tới ngày 2022-08-23 và toàn bộ các
ngày TrainTicket (2023-01).

### 5.8.4 C5 (Rescue) một điểm

Theo quyết định tiền đăng ký V34 (b) (QĐ-034), C5 không thuộc phương pháp chính mà chỉ được đánh giá tại đúng một
điểm tham số đã chọn trên `val` (`η = (0; 0,4; 0,6), τ = 0,8`, công thức hai thành phần `Φ_topo` và `Δ_time`),
không quét lại lưới trên `test`, với tập cảnh báo kích hoạt `A` là các cảnh báo của chính CTAV trong cửa sổ nhân
quả 300 giây.

**Bảng 5.22 (T12). CTAV và CTAV + C5 một điểm (`η = (0; 0,4; 0,6), τ = 0,8`) trên `test` (11.985 cửa sổ có telemetry, 346 fault) cạnh `val` (7.636; 209).**

| Biến thể | Split | Cửa sổ được cứu | TP | FP | Recall | F1 [CI95] | FPR | Lần gọi thêm |
|---|---|---:|---:|---:|---:|---|---:|---:|
| CTAV (off) | `val` | 0 | 29 | 51 | 0,139 | 0,201 [0,138; 0,264] | 0,0069 | 0 |
| CTAV + C5 | `val` | 52 | 31 | 67 | 0,148 | 0,202 [0,143; 0,261] | 0,0090 | +52 |
| CTAV (off) | `test` | 0 | 14 | 64 | 0,040 | 0,066 [0,036; 0,100] | 0,0055 | 0 |
| CTAV + C5 | `test` | 61 | 14 | 65 | 0,040 | 0,066 [0,036; 0,101] | 0,0056 | +61 |

*Nguồn: `eval/results/m8_rescue_test_v1/rescue.json` (`m8_rescue_test_c1_v1`) và `eval/results/m7_rescue_val_v1/rescue.json`.*

Trên `test`, cổng Rescue vớt lên 61 cửa sổ từng bị detector bỏ qua (tất cả đều có telemetry: 3 cửa sổ fault trong
tổng số 122 fault bị detector bỏ sót, và 58 cửa sổ normal), tốn thêm 61 lần gọi API mới (0,09 USD theo token). Khi
đưa qua C1 và judge, cả 3 cửa sổ fault đều bị chính judge trả `FALSE_POSITIVE` ngay trước khi chạm tới C3 (0/3 trở
thành cảnh báo), trong khi 58 cửa sổ normal sinh 19 câu `TRUE_ALERT` ở C1 và được C3 lọc xuống còn 1 cảnh báo sai
cuối cùng (+0 TP, +1 FP; `ΔF1 = −0,000 [−0,001; +0,000]`, `ΔFPR = +0,0001 [+0,0000; +0,0003]`, McNemar `p = 1,000`).
Kết quả này xác nhận lại Phát hiện 12 trên dữ liệu độc lập: cổng cứu candidate ở tầng detector không mở rộng được
recall khi bản thân tập cảnh báo kích hoạt `A` thưa (78 cảnh báo CTAV) và nút thắt chính nằm ở tầng thẩm định phía
sau.

### 5.8.5 Độ ổn định của judge và chi phí

Để kiểm tra xem biến thiên ngẫu nhiên của API `gemini-2.5-flash` ở `temperature = 0` có ảnh hưởng tới các so sánh ở
trên hay không, hai cấu hình BM25 và C1 được chạy lặp thêm hai lần độc lập (`repeat = 1` và `repeat = 2`, bỏ qua
cache của `repeat = 0`) trên cùng một tập con cố định gồm 200 candidate có telemetry được lấy ngẫu nhiên không nhìn
nhãn hay verdict (`eval/samples/m8_repeat_test_v1.csv`, seed 42: 6 fault, 194 normal). Theo giao thức đã đăng ký,
phép đo này chỉ dùng để báo biên độ nhiễu của judge, không dùng để đổi quyết định giả thuyết.

**Bảng 5.23 (T13). Độ lệch câu trả lời của judge qua `repeat` 0, 1, 2 (`test`, tập con 200 candidate có telemetry: 6 fault, 194 normal).**

| Phương pháp | Số cửa sổ | Tỉ lệ `TRUE_ALERT` thô ở `repeat` 0 / 1 / 2 | Tỉ lệ cảnh báo cuối cùng ở `repeat` 0 / 1 / 2 | Tỉ lệ cửa sổ đổi câu trả lời [CI95] |
|---|---:|---|---|---|
| BM25 | 200 | 0,120 / 0,110 / 0,120 (24 / 22 / 24) | 0,085 / 0,075 / 0,085 (17 / 15 / 17) | 0,010 [0,000; 0,025] (2 / 200 cửa sổ) |
| C1 | 200 | 0,370 / 0,375 / 0,375 (74 / 75 / 75) | 0,335 / 0,340 / 0,340 (67 / 68 / 68) | 0,005 [0,000; 0,015] (1 / 200 cửa sổ) |

*Nguồn: `eval/results/h0_test_{bm25,c1_k0}_{v1,rep1_v1,rep2_v1}/` trên `eval/samples/m8_repeat_test_v1.csv`.*

Kết quả ở Bảng 5.23 cho thấy độ lặp lại rất cao: 198/200 cửa sổ của BM25 (99,0%) và 199/200 cửa sổ của C1 (99,5%)
nhận cùng một câu trả lời ở cả ba lần gọi độc lập; không có bất kỳ cửa sổ fault nào đổi quyết định ở cả hai phương
pháp (BM25 giữ đúng 1/6 TP ở cả ba lần, C1 giữ đúng 5/6 TP ở cả ba lần), còn 3 trường hợp lật cờ duy nhất đều là
cửa sổ bình thường sát ranh giới giải thích. Biên độ dao động `0,005–0,010` nhỏ hơn một bậc độ lớn so với các hiệu
ứng chính trên `test` (`ΔRecall(C1 − BM25) = +0,179`, `ΔFPR(CTAV − BM25) = −0,0262`), xác nhận rằng nhiễu nội tại
của judge không làm sai lệch bất kỳ kết luận kiểm định nào.

Về chi phí thực nghiệm, Bảng 5.24 đối chiếu ước lượng trước khi chạy (QĐ-035, tính từ đơn giá trung bình mỗi loại
prompt trên `val`) với số thực ghi trong sổ cái cache của M8. Tổng số lần gọi API mới thực tế là 21.094 (so với ước
lượng ≈ 20.100) và tổng chi phí quy đổi theo token là **15,85 USD** (23,37 triệu token vào và 3,53 triệu token ra,
nằm dưới ngân sách 18 USD của M8). Phần vượt nhẹ +2,85 USD so với ước lượng điểm 13,00 USD đến từ hai nguyên nhân
đo được trực tiếp: (1) trên `test`, tỉ lệ candidate có bằng chứng cao hơn dự tính ở C1 và LLM-không-RAG (3.299 và
3.287 câu mới so với ước ≈ 2.700); và (2) các prompt có bằng chứng của Online Boutique trên `test` chứa chuỗi span
dài hơn `val`, làm đơn giá thực tế mỗi câu có bằng chứng tăng từ ≈ 0,00121 lên ≈ 0,00165 USD ở BM25 và từ ≈ 0,00112
lên ≈ 0,00143 USD ở C1, trong khi C5 một điểm và bốn run `repeat` đều thấp hơn hoặc sát mức dự trù.

**Bảng 5.24 (T14). Chi phí API của M8: ước lượng trước khi chạy (QĐ-035) và thực tế theo sổ cái cache (`test`).**

| Hạng mục | API mới: ước | API mới: thực | USD theo token: ước | USD theo token: thực |
|---|---:|---:|---:|---:|
| BM25 (`h0_test_bm25_v1`) | 13.699 | 13.699 | 7,80 | 8,87 |
| C1 (`h0_test_c1_k0_v1`) | ≈ 2.700 | 3.299 | 3,00 | 4,71 |
| LLM-không-RAG (`h0_test_norag_v1` + `_v2`) | ≈ 2.700 | 3.287 | 0,90 | 1,10 |
| Phương sai `repeat` (4 run, 200 cửa sổ) | 800 | 748 | 1,00 | 1,08 |
| C5 một điểm (`m8_rescue_test_c1_v1`) | vài trăm | 61 | 0,30 | 0,09 |
| **Tổng M8** | **≈ 20.100** | **21.094** | **13,00** | **15,85** |

*Nguồn: QĐ-035 và sổ cái `data/llm_cache/gemini.jsonl` (dòng 19.157–40.251, QĐ-038).*

### 5.8.6 Context precision chấm tay

Để đánh giá chất lượng ngữ cảnh truy xuất độc lập với hành vi của judge LLM (V35 (a), QĐ-037), một mẫu cố định gồm
50 candidate có telemetry trên `test` (25 cửa sổ fault và 25 cửa sổ normal mà ít nhất một trong hai bộ truy xuất
BM25 hoặc C1 trả về bằng chứng, chọn ngẫu nhiên với `seed = 42`) được trích xuất bằng
`scripts/m8_context_precision_sample.py` thành bảng chấm mù `eval/manual/context_precision_test_v1.csv` (525 dòng
bằng chứng phân biệt). Mọi thông tin về tên phương pháp truy xuất (`bm25` hay `c1`), điểm xếp hạng và nhãn thật của
cửa sổ (`is_fault`, `root_cause`) đều được tách riêng sang file khóa `.key.csv`; người chấm gán một trong ba mức
(`relevant`, `irrelevant`, `unsure`) theo quy tắc trong `eval/manual/README-context-precision.md`, sau đó mới ghép
khóa để tính context precision tách riêng cho cửa sổ fault và normal ở Bảng 5.25.

**Bảng 5.25 (T15). Context precision chấm tay trên mẫu 50 cửa sổ có telemetry của `test` (25 fault, 25 normal; `seed = 42`).**

| Phương pháp | Nhóm cửa sổ | Số bằng chứng | Liên quan (`relevant`) | Không liên quan (`irrelevant`) | Không chắc (`unsure`) | Context precision |
|---|---|---:|---:|---:|---:|---:|
| BM25 | Fault (25 cửa sổ) | ✍️ | ✍️ | ✍️ | ✍️ | ✍️ |
| BM25 | Normal (25 cửa sổ) | ✍️ | ✍️ | ✍️ | ✍️ | ✍️ |
| C1 | Fault (25 cửa sổ) | ✍️ | ✍️ | ✍️ | ✍️ | ✍️ |
| C1 | Normal (25 cửa sổ) | ✍️ | ✍️ | ✍️ | ✍️ | ✍️ |

*Nguồn: `eval/manual/context_precision_test_v1.csv` ghép với `eval/manual/context_precision_test_v1.key.csv` (chờ điền sau bước chấm tay theo V35 (a)).*


## 5.9 H5 — Tác tử RCA trên `test`

> Nguồn: `eval/results/rca_final_test_v1/` (con số đăng ký), `eval/results/rca_sens_test_c3rolling_v1/` (độ nhạy, ngoài
> bản đăng ký), `eval/results/rca_final_val_v1/` (`val`); QĐ-040..042. Phương pháp và cách chọn tham số trên `val`:
> `docs/drafts/ch5-rca-val.md`. CI95: bootstrap percentile, 1.000 mẫu, `seed = 42`.

### 5.9.1 Thiết lập

Tác tử RCA chạy trên đúng tập cảnh báo mà CTAV đóng băng phát ra trên `test` ở §5.7 (78 cảnh báo: 14 TP, 64 FP mức cửa
sổ), với cấu hình đã chốt trên `val` trước khi chạm `test` ($T_{group}$ = 180 s; lan truyền ngược một bước; cascade =
lần tiêm lỗi có cảnh báo ở ít nhất hai service). Cấu hình `test` chỉ khác cấu hình `val` ở split, run đầu vào và
`run_id`; harness in cùng một dấu vân tay phương pháp cho cả hai. Mỗi cấu hình chạy đúng một lần. Theo V36 (a), một
dòng **độ nhạy** được báo kèm: cùng phương pháp trên 438 cảnh báo của ablation `c3_rolling_baseline`; dòng này nằm
ngoài bản đăng ký và không dùng để kết luận H5.

### 5.9.2 Kết quả kiểm định H5

**Bảng 5.26. Kiểm định H5 trên `test` theo bản đăng ký (78 cảnh báo → 38 sự cố, 17 sự cố có nhãn).**

| Vế của H5 | Số đo trên `test` | CI95 | Kết luận |
|---|---|---|---|
| Hit@1 ≥ 0,60 | 8 / 17 = 0,471 | [0,235; 0,706] | Không đạt |
| Hit@3 ≥ 0,80 | 8 / 17 = 0,471 | [0,235; 0,706] | Không đạt |
| Cận dưới CI95 của ΔHit@1 (RCA − baseline) > 0 | 0,000 (baseline 8 / 17; 0 cặp lệch) | [0,000; 0,000] | Không đạt |
| Alert Reduction ≥ 30% trên sự cố cascade | không tính được: 0 / 50 lần tiêm lỗi là cascade | — | Không đạt |

**H5 không được chấp nhận.** Để tham chiếu, Alert Reduction Ratio trên mọi cảnh báo là 0,513 [0,362; 0,626] và trên
cảnh báo nằm trong lỗi là 0,556 [0,382; 0,674]; hai con số này không phải tiêu chí đăng ký.

**Bảng 5.27. Tác tử RCA trên `val`, trên `test` (đăng ký) và dòng độ nhạy.**

| | `val` | `test` — đăng ký | `test` — độ nhạy (ngoài bản đăng ký) |
|---|---|---|---|
| Cảnh báo đầu vào / service có cảnh báo | 80 / 8 | 78 / 5 | 438 / 22 |
| Lần tiêm lỗi: tổng / có sự cố có nhãn / không có cảnh báo | 30 / 10 / 18 | 50 / 17 / 29 | 50 / 34 / 1 |
| Sự cố: tổng / có nhãn / mơ hồ / không ứng với lỗi | 26 / 11 / 1 / 14 | 38 / 17 / 3 / 18 | 114 / 48 / 14 / 52 |
| Sự cố nhiều service | 1 | 0 | 39 |
| Cảnh báo mỗi sự cố (trung vị / lớn nhất) | 3 / 6 | 1 / 9 | 2 / 31 |
| Hit@1 | 0,636 [0,364; 0,909] | 0,471 [0,235; 0,706] | 0,208 [0,104; 0,333] |
| Hit@3 | 0,636 [0,364; 0,909] | 0,471 [0,235; 0,706] | 0,313 [0,188; 0,458] |
| Hit@1 baseline | 0,636 | 0,471 | 0,229 [0,125; 0,354] |
| ΔHit@1 (RCA − baseline) | 0,000 [0,000; 0,000] | 0,000 [0,000; 0,000] | −0,021 [−0,063; 0,000] |
| Hit@1 trên mọi lần tiêm lỗi | 0,200 [0,067; 0,333] | 0,160 [0,060; 0,280] | 0,200 [0,100; 0,320] |
| ARR mọi cảnh báo | 0,675 [0,600; 0,730] | 0,513 [0,362; 0,626] | 0,740 [0,654; 0,796] |
| ARR cascade (số lần tiêm lỗi cascade) | 0,667 (1) | — (0) | 0,704 [0,591; 0,777] (41) |
| JSON valid rate | 26 / 26 | 38 / 38 | 114 / 114 |

**Bảng 5.28. Định vị theo loại lỗi trên `test` (tập đăng ký).**

| Loại lỗi | Lần tiêm lỗi | Không có cảnh báo | Chỉ trong sự cố mơ hồ | Có sự cố có nhãn | Trúng hạng 1 |
|---|---:|---:|---:|---:|---:|
| `network_delay` | 15 | 5 | 2 | 8 | 2 |
| `cpu_contention` | 11 | 5 | 1 | 5 | 3 |
| `exception` | 10 | 7 | 0 | 3 | 3 |
| `return` | 9 | 8 | 0 | 1 | 0 |
| `cpu_consumed` | 5 | 4 | 1 | 0 | — |
| **Tổng** | **50** | **29** | **4** | **17** | **8** |

### 5.9.3 Vì sao H5 không đạt

Cả bốn vế cùng quy về một nguyên nhân: **cảnh báo đầu vào hiếm khi rơi vào service gốc**. Trên tập đăng ký, 78 cảnh báo
chỉ nằm ở 5 service, vì CTAV đóng băng chỉ phát cảnh báo ở các service có ngưỡng `dev` (Phát hiện 11, §5.8.2). Hệ quả
thứ nhất: 29 trong 50 lần tiêm lỗi không có cảnh báo nào, nên không thể định vị; tính trên mọi lần tiêm lỗi, service
gốc chỉ được chỉ đúng ở 8 lần (0,160). Hệ quả thứ hai: cả 38 sự cố đều chỉ có một service. Khi đó lan truyền ngược một
bước không có service lân cận bất thường nào để chuyển trách nhiệm sang và trả về đúng service có cảnh báo — cũng là
câu trả lời của baseline; vì vậy ΔHit@1 bằng đúng 0, Hit@3 trùng Hit@1, và không có lỗi cascade nào để đo mức giảm cảnh
báo. Chín sự cố trượt có cùng một dạng: cảnh báo nổ ở service phía gọi (`frontend`, `ts-travel-service`), còn lỗi được
tiêm ở một service phía sau nó (`checkoutservice`, `currencyservice`, `paymentservice`, `ts-basic-service`,
`ts-route-service`, `ts-security-service`) — service không có cảnh báo nào. Tám sự cố trúng đều là lỗi tiêm ngay tại
service có cảnh báo.

Dòng độ nhạy cho thấy nguyên nhân này không biến mất khi có nhiều cảnh báo hơn. Với 438 cảnh báo ở 22 service, 49
trong 50 lần tiêm lỗi có cảnh báo và 39 sự cố có nhiều service, nhưng Hit@1 chỉ 0,208 — thấp hơn baseline 0,021 (một
cặp lệch). Trong 48 sự cố có nhãn, service gốc thật nằm trong số service có cảnh báo ở đúng 15 sự cố, bằng số trúng
Hit@3: 0,313 là trần của mọi cách xếp hạng chỉ dựa trên service có cảnh báo. Thứ được cải thiện là gom cảnh báo: Alert
Reduction Ratio trên lỗi cascade đạt 0,704 [0,591; 0,777]. Dòng này là mô tả, không thay kết luận ở Bảng 5.26.

So với `val`, `test` có số cảnh báo gần bằng (78 so với 80) nhưng nhiều sự cố hơn và sự cố nhỏ hơn (trung vị 1 cảnh
báo so với 3), nên mức giảm cảnh báo chung thấp hơn (0,513 so với 0,675). Khác biệt này được báo như nó là; $T_{group}$
và quy tắc xếp hạng không được chọn lại.

### 5.9.4 Báo cáo chẩn đoán

Cả 38 báo cáo trên tập đăng ký (và 114 báo cáo của dòng độ nhạy) đều qua kiểm tra lược đồ, không báo cáo nào bị loại;
ở 1 (và 4) báo cáo LLM có nêu một id bằng chứng không có trong ngữ cảnh, id đó bị bỏ và báo cáo vẫn còn bằng chứng hợp
lệ. Như trên `val`, trường loại lỗi không mang thông tin phân biệt: 35 / 38 báo cáo ghi `cpu_contention`. Chất lượng
nội dung được đánh giá bằng người ở chương sau.

### 5.9.5 Hạn chế

- Mẫu nhỏ: 17 sự cố có nhãn; CI của Hit@1 rộng gần 0,5.
- Nhãn mức service, không phải mức pod.
- Vế Alert Reduction của H5 không đo được trên tập đăng ký vì không có lỗi cascade theo định nghĩa đã chốt trước; con
  số 0,704 chỉ có ở dòng độ nhạy.
- Mức 2 (LLM lập luận trên toàn chuỗi gọi) đã bị cắt khỏi phạm vi nên không có số so sánh.
