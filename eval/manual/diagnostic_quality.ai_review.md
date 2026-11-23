# Bản nháp điểm V50 do AI chấm — **CHƯA phải điểm của người chấm**

> **Trạng thái: NHÁP, chờ duyệt.** Người chấm chính vẫn là bạn. File này **không** thay thế `diagnostic_quality.csv`; `diagnostic_quality.csv` vẫn đang trống điểm (`0 / 30`).
> Chấm ngày 2026-11-22 bởi agent `lead` (mô hình `deepseek-flash` qua DSH), theo quyết định chọn đường **(b) "AI chấm nháp, người duyệt"** trong phiên 2026-11-22 (sẽ ghi thành QĐ-051).

## 1. Cách chấm (để tái lập và để ghi vào §7.3)

- Chỉ đọc `eval/manual/diagnostic_quality.csv`; **không mở `diagnostic_quality.key.csv`** trong suốt quá trình chấm.
- Thang 0–2 theo `eval/manual/README-diagnostic-quality.md` (tức `02` §4.4). Các quy tắc áp dụng:
  - **`root_cause_score`** — `2` khi bằng chứng **cục bộ tại `predicted_root_cause`** rõ bất thường (span dài hơn ~2× mức nền của chính thao tác đó, có `WARN`/`ERROR`, hoặc metric khớp loại lỗi) và không có bất thường mạnh hơn ở service liền kề; `1` khi bất thường nằm ở **callee/caller trực tiếp** (service liền kề) hoặc bằng chứng tại service kết luận chỉ ở mức yếu/lệch thời gian; `0` khi toàn bộ bằng chứng bình thường (span vài ms, không lỗi) hoặc thuộc service không liên quan.
  - **`evidence_score`** — `2` khi bằng chứng khớp thời điểm cửa sổ (lệch ≤ ~2 phút) và cho thấy span chậm vượt nền hoặc log lỗi chứng minh trực tiếp nhận định; `1` khi lệch thời gian rõ rệt hoặc trộn span bình thường; `0` khi lệch hẳn khỏi cửa sổ hoặc toàn span bình thường.
  - **`action_score`** — `2` khi có gợi ý bám vào một callee/endpoint/cơ chế **cụ thể xuất hiện trong bằng chứng** (ví dụ: hiệu năng `CurrencyService/Convert`, truy vấn `TripRepository.findAll`, syscall/context switch); `1` khi toàn mẫu chung (kiểm tra CPU/log/deployment của service X); `0` khi vô nghĩa.
- Giới hạn đã biết của cách đọc này: `root_cause_score = 1` **gộp hai trường hợp** (service liền kề, và service đúng nhưng bằng chứng yếu/lệch thời gian). Nếu bạn muốn tách, ghi ở cột `note` khi duyệt.

## 2. Phân bố điểm nháp

| Tiêu chí | `0` | `1` | `2` | Trung bình |
|---|---:|---:|---:|---:|
| Đúng root cause | 6 | 16 | 8 | **1,067** |
| Bằng chứng hợp lệ | 7 | 9 | 14 | **1,233** |
| Gợi ý xử lý dùng được | 0 | 22 | 8 | **1,267** |

Độ tự tin: `high` 14 · `medium` 15 · `low` 1.

## 3. Bảng duyệt (xếp theo độ tự tin, thấp trước)

Điểm ghi dạng `root_cause / evidence / action`.

| # | Kết luận của hệ thống | Điểm | Tự tin | Lý do chấm |
|---:|---|---|:--:|---|
| 4 | frontend · cpu_contention | 1/1/1 | low | Chỉ 1 span 282 ms (nhỉnh hơn nền), không đủ để khẳng định sự cố cục bộ |
| 1 | ts-travel-service · cpu_contention | 1/1/1 | medium | Span 375 ms cách cửa sổ 2 phút, chỉ 1 span; top feature là memory trong khi kết luận cpu_contention |
| 2 | frontend · cpu_contention | 2/2/1 | medium | Recv 619/567 ms cao hơn nền, metric CPU+syscall khớp; gợi ý vẫn là mẫu chung |
| 9 | ts-travel-service · cpu_contention | 2/2/1 | medium | queryInfo 803 ms + trips/left 956 ms đúng cửa sổ; có CpuUsage(m) trong top feature |
| 10 | frontend · cpu_contention | 2/2/2 | medium | Recv 307–608 ms, metric CPU/syscall khớp; gợi ý syscall/context switch bám bằng chứng |
| 11 | frontend · cpu_contention | 1/0/2 | medium | Span duy nhất ở 06:34 cách cửa sổ (06:25) 9 phút, không chứng minh được cửa sổ |
| 12 | frontend · cpu_contention | 0/0/1 | medium | Recv 144 ms + 2 span 6–15 ms: telemetry bình thường |
| 13 | ts-travel-service · cpu_contention | 1/1/1 | medium | queryInfo 2.361 ms rất mạnh nhưng ở 12:15, trước cửa sổ (12:18) 3,7 phút |
| 14 | frontend · cpu_contention | 1/1/1 | medium | Toàn bộ bằng chứng là GetAds 187–200 ms ở callee, không có tín hiệu CPU của frontend |
| 15 | frontend · cpu_contention | 0/0/1 | medium | Recv 177 ms + span 5–17 ms: bình thường |
| 18 | frontend · cpu_contention | 1/1/1 | medium | Recv 232 ms + Convert 86 ms: chỉ nhỉnh nhẹ, không có bất thường rõ |
| 19 | cartservice · cpu_contention | 1/1/1 | medium | GetCart 299 ms nhưng ở 12:46, sau cửa sổ (12:40) 6 phút |
| 20 | frontend · cpu_contention | 1/1/1 | medium | GetProduct 57 ms (nền 7–17 ms) nhỉnh ở callee, chỉ 2 span |
| 22 | ts-travel2-service · cpu_contention | 1/1/1 | medium | 3 span 287–570 ms ngay trước cửa sổ 12 s; mức tăng nhẹ |
| 25 | ts-travel-service · cpu_contention | 1/1/1 | medium | Bằng chứng trùng span của ca khác và cách cửa sổ 6 phút |
| 29 | frontend · cpu_contention | 1/2/1 | medium | Convert 199–300 ms bất thường ở callee, ngay trước cửa sổ 1 phút |
| 3 | ts-travel-service · cpu_contention | 2/2/1 | high | 2 span 1.194/972 ms đúng cửa sổ, cục bộ tại service kết luận; gợi ý là mẫu chung |
| 5 | frontend · cpu_contention | 1/2/2 | high | Recv 30 s nhưng Convert 2,0–2,8 s (nền ~10 ms) ⟹ nguồn ở callee; có gợi ý nhắc CurrencyService/Convert |
| 6 | frontend · cpu_contention | 0/0/1 | high | Bằng chứng nằm 4 phút trước cửa sổ và toàn span 7–8 ms bình thường |
| 7 | frontend · cpu_contention | 1/2/1 | high | PlaceOrder 398 ms là callee; Recv 548 ms gồm thời gian chờ callee |
| 8 | frontend · cpu_contention | 1/2/2 | high | Convert 502 ms bất thường ở callee (nền ~10 ms); Recv 953 ms phản ánh chờ callee |
| 16 | ts-travel-service · unknown | 0/0/1 | high | 3 span SELECT Trip/findByTripId 2,7–2,9 ms: hoàn toàn bình thường |
| 17 | ts-travel-service · cpu_contention | 0/0/2 | high | 4 span findAll 6,3–6,8 ms: hoàn toàn bình thường, dù gợi ý bám đúng query |
| 21 | frontend · cpu_contention | 1/2/1 | high | Recv 930 ms + Convert 378 ms; một span 07:03 nằm ngoài cửa sổ |
| 23 | ts-travel-service · cpu_contention | 2/2/1 | high | trips/left 601 ms + queryInfo 598 ms đúng cửa sổ, có CpuUsage(m) |
| 24 | ts-travel-service · cpu_contention | 2/2/1 | high | queryInfo 3.605 ms + trips/left 1.186 ms, có span WARN |
| 26 | ts-travel-service · cpu_contention | 2/2/1 | high | trips/left 865/411 ms + queryInfo 863 ms đúng cửa sổ |
| 27 | frontend · cpu_contention | 1/2/2 | high | 4 span Convert 599–730 ms (nền ~10 ms) ⟹ nguồn ở callee |
| 28 | ts-travel-service · network_delay | 2/2/2 | high | trips/left 2.167/2.325 ms + POST 1.058 ms; metric network khớp network_delay |
| 30 | ts-travel-service · cpu_contention | 0/0/2 | high | 3 span findAll ~7 ms: bình thường; lập luận chỉ lặp lại metric |

## 4. Các dòng nên soi kỹ nhất

Nhóm **lệch thời gian** (bằng chứng nằm ngoài cửa sổ — quyết định `1` hay `0` phụ thuộc cách bạn định nghĩa "khớp thời điểm"): **1, 11, 13, 19, 22, 25**.
Nhóm **bất thường nhẹ** (ranh giới giữa "nhỉnh hơn nền" và "bình thường"): **4, 18, 20**.
Nhóm **callee** (đồng ý là service liền kề, nhưng nếu bạn cho rằng lỗi nằm ở callee thì vẫn có thể là `2` theo nghĩa "đúng service gốc"): **5, 7, 8, 14, 27, 29**.

## 5. Cách duyệt (chọn một)

1. **Sửa trực tiếp** `eval/manual/diagnostic_quality.ai_scores.csv` (chỉ 3 cột điểm + `note`), rồi báo tôi "duyệt xong".
2. **Hoặc trả lời trong chat** dạng `4: 2/1/1; 11: 0/0/2; …` — tôi sẽ áp vào file.

Sau khi bạn duyệt, tôi sẽ:
1. Chép điểm đã duyệt sang `eval/manual/diagnostic_quality.csv` (giữ nguyên 14 cột nội dung, chỉ điền 3 cột điểm + `note`), lưu UTF-8.
2. Chạy:
   ```bash
   py scripts/m11_score_diagnostic_quality.py --graded eval/manual/diagnostic_quality.csv --key eval/manual/diagnostic_quality.key.csv --out eval/results/m11_diagnostic_quality_v1
   ```
3. Điền `n`, trung bình ± SD, CI 95% bootstrap vào `docs/drafts/ch7-phan-tich-ca-sai.md` §7.4.4 và báo cáo M11; đóng V50.

> **Lưu ý trung thực:** nếu bạn duyệt nhanh mà không sửa dòng nào, luận văn vẫn phải ghi *"điểm do AI chấm trước, tác giả xác nhận"* — không được ghi là "hai người chấm độc lập". Nếu bạn muốn có Cohen's κ thật thì phải giữ ít nhất 15 dòng bạn tự chấm **trước khi** xem bảng này; bảng nháp này khi đó chỉ dùng làm đối chứng và κ sẽ được tính giữa hai bản.
