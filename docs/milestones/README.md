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
| M3 | [M3-graph-c1-gpaper.md](M3-graph-c1-gpaper.md) | 2026-10-19 | QUA — G-paper đạt; V16, V17 đã chốt ở M4 (QĐ-022) |
| M4 | [M4-h0.md](M4-h0.md) | 2026-10-29 | QUA — H0 tái lập hiện tượng, không tái lập cơ chế (Phát hiện 7); V24 (b), GVHD đồng ý (QĐ-027) |
| M5 | [M5-h1.md](M5-h1.md) | 2026-11-01 | QUA — H1 giữ một phần (QĐ-028); V28 (b), trọng tâm sang C3 (QĐ-029) |
| M6 | [M6-ctav.md](M6-ctav.md) | 2026-11-11 | QUA CÓ ĐIỀU KIỆN — H3 bỏ C2, C4; CTAV = C1 + C3 (`dev` p90), F1 `val` 0,201 vs BM25 0,103; V31 (a), V32 (a) (QĐ-031, QĐ-032) |

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
