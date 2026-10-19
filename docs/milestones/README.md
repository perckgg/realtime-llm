# Báo cáo cột mốc

Sau **mỗi** mốc trong `docs/Final_Thesis_Phase2/04-implementation-roadmap.md` phải có một
báo cáo ở thư mục này, viết **trước** khi sang mốc sau (`04` §2). Quyết định chi tiết vẫn
nằm ở `docs/experiment-log.md`; báo cáo mốc tổng hợp lại và dẫn chiếu về đó.

## Danh sách

| Mốc | Báo cáo | Ngày | Kết luận |
|---|---|---|---|
| M0 | [M0-nen-tang.md](M0-nen-tang.md) | 2026-10-18 | QUA (viết bù sau review) |
| M1 | [M1-detector-bm25-judge.md](M1-detector-bm25-judge.md) | 2026-10-19 | QUA; V7–V9 đã chốt (QĐ-017) |
| M2 | [M2-harness-gport.md](M2-harness-gport.md) | 2026-10-19 | QUA — V10 (a), V11 đã chốt (QĐ-019) |

## Mẫu

Chép khối dưới vào `M<n>-<ten-ngan>.md`. Giữ đúng bốn phần chính; các phần phụ có thể để trống.

```markdown
# M<n> — <Tên mốc>

| | |
|---|---|
| Ngày đóng mốc | YYYY-MM-DD |
| Hạn mục tiêu | YYYY-MM-DD (sớm / đúng / trễ N ngày) |
| Kết luận | QUA / CHƯA QUA / QUA CÓ ĐIỀU KIỆN |
| Commit | <hash> … |
| Quyết định liên quan | QĐ-xxx … |

## 1. Kết quả hiện tại

DoD của mốc, từng dòng, kèm bằng chứng:

| DoD | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|

Số liệu chính (bảng đánh số, đủ để dán vào luận văn).

## 2. Cần review gì

Những chỗ người dùng nên tự kiểm, xếp theo mức rủi ro:

| # | Kiểm gì | Ở đâu (file:dòng / lệnh) | Vì sao rủi ro |
|---|---|---|---|

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|

## 4. Plan cho mốc tiếp theo

- Việc (theo thứ tự làm)
- DoD
- Rủi ro đã biết

## Phụ lục

- Sai lệch so với plan (gì đổi, vì sao, QĐ nào)
- Nguyên liệu cho luận văn (bảng/hình/đoạn văn có thể dùng, ở đâu)
```
