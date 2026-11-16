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
| M6 | [M6-ctav.md](M6-ctav.md) | 2026-11-11 | QUA — H3 bỏ C2, C4; CTAV = C1 + C3 (`dev` p90), F1 `val` 0,201 vs BM25 0,103; V30 (c), V31 (a), V32 (a) (QĐ-031, QĐ-032, QĐ-037) |
| M7 | [M7-rescue-dang-ky.md](M7-rescue-dang-ky.md) | 2026-11-14 | QUA — Rescue (QĐ-033): 2 thành phần, +2 TP / +16 FP, không có ý nghĩa; H0–H5 đã đăng ký trước G-test, δ = 0,05, C5 chỉ là ablation (QĐ-034) |
| M8 | [M8-g-test.md](M8-g-test.md) | 2026-11-16 | QUA (chờ người dùng xem báo cáo) — G-test hoàn tất (0 lỗi judge, 15,85 USD theo token): H0 chấp nhận, H2 không đạt trên cấu hình tĩnh `dev` (giải thích trọn vẹn bởi Phát hiện 11 & đối chứng `C3-trượt` F1 0,120), H3 & H4 đạt (QĐ-035..038) |

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
