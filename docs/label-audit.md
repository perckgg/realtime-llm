# Kiểm tra nhãn Nezha — Tuần 1

Sinh tự động bởi `scripts/verify_labels.py` lúc 2026-08-31T02:52:52+00:00.
Không sửa tay: chạy lại script để cập nhật.

- Dataset: `C:\Working\Internship1\data\Nezha`
- Cửa sổ: 1 mẫu metric của 1 pod = 60 s
- Quy tắc gán nhãn: cùng pod và `start_ts` nằm trong `[inject_ts − 60 s, inject_ts + 360 s]` — chép từ pipeline Giai đoạn 1 (`legacy/nezha_setup/prepare_nezha_data.py`) để cổng chặn tái lập baseline ở Tuần 3 còn ý nghĩa
- Nguồn thời gian dùng để join: cột **wall-clock** (`--time-source wall`)
- Số file trace đã quét: 303

## 1. Kết luận nhanh

**Cổng chặn Tuần 1: QUA.** Nezha có sẵn nhãn root-cause ở mức pod cho cả 101 lần tiêm lỗi, ánh xạ được 100% lên tên service, và trace có đủ `SpanID`/`ParentID` để dựng call chain (97.86% span giải được về span cha). Không phải gán nhãn tay, không phải đổi dataset. Được phép sang Tuần 2.

## 2. Phạm vi dữ liệu

| Ngày | Hệ thống | Số lần tiêm lỗi | Pod có metric | Fault window |
|---|---|---|---|---|
| 2022-08-22 | online_boutique | 24 | 10 | 169 |
| 2022-08-23 | online_boutique | 32 | 10 | 225 |
| 2023-01-29 | train_ticket | 28 | 46 | 191 |
| 2023-01-30 | train_ticket | 17 | 46 | 119 |
| **Tổng** |  | 101 | 103 | 704 |

- File metric đã đọc: 112
- Dòng metric đã đọc: 95,660 (bỏ qua 0, trùng `window_id` 0)
- Dòng có cột `TimeStamp` lệch cột `Time` quá 2 s: 1,209
- Pod xuất hiện trong metric: 103 → 56 service

## 3. Câu hỏi 1–2 — Nhãn root-cause có không, ở mức nào

Có. Mỗi lần tiêm lỗi được ghi trong `rca_data/<ngày>/<ngày>-fault_list.json` với `inject_time`, `inject_timestamp`, `inject_pod`, `inject_type`. **Nhãn ở mức pod**, không phải mức service.

Ánh xạ pod → service dùng danh sách service chuẩn trong `construct_data/root_cause_hipster.json` và `root_cause_ts.json` (21 service), fallback là cắt hậu tố ReplicaSet của Kubernetes.

| Cách khớp | Số pod bị tiêm lỗi | Ý nghĩa |
|---|---|---|
| exact | 0 | Tên pod trùng luôn tên service |
| prefix | 28 | Khớp tiền tố với service chuẩn — tin cậy |
| regex | 0 | Chỉ cắt được hậu tố, cần rà tay |
| **Tổng** | 28 |  |

**Toàn bộ 28 pod bị tiêm lỗi ánh xạ được lên 20 service chuẩn.** Nhãn `root_cause_service` dùng được cho Hit@1 / Hit@3 của Nhánh B.

## 4. Câu hỏi 3–4 — Số lượng và phân bố nhãn

Tổng số fault window có nhãn root-cause: **704 / 95,660** cửa sổ (0.74%), sinh từ **101** lần tiêm lỗi.

| Loại lỗi | Số lần tiêm | Fault window | Window / lần tiêm |
|---|---|---|---|
| cpu_consumed | 10 | 71 | 7.1 |
| cpu_contention | 23 | 161 | 7.0 |
| exception | 20 | 138 | 6.9 |
| network_delay | 30 | 210 | 7.0 |
| return | 18 | 124 | 6.9 |
| **normal** | — | 94,956 | — |

- Lần tiêm lỗi không sinh được window nào: **0**
- Tỷ lệ mất cân bằng fault : normal ≈ 1 : 135

Con số 101 lần tiêm lỗi khớp với `fault_count` trong `legacy/nezha_setup/processed/summary.json` của Giai đoạn 1 — hai lần đếm độc lập cho cùng kết quả.

## 5. Chọn cột thời gian nào để join

Nezha ghi mọi mốc thời gian hai lần và hai bản **không khớp nhau ở hai chỗ**:

1. Ngày **2023-01-29**: 24 trên 28 lần tiêm lỗi có `inject_timestamp` chậm hơn `inject_time` đúng 8 tiếng, trong khi file metric của ngày đó đi theo `inject_time`.
2. Toàn bộ 1.209 dòng của `2022-08-22/metric/adservice-5f6585d649-fnmft_metric.csv` có `TimeStamp` vượt trước cột `Time` của chính nó khoảng 6,3 năm.

Các cột wall-clock khớp nhau trên cả bốn ngày, nên chúng là mốc chuẩn.

| Nguồn thời gian | Tổng window | Fault window | Lần tiêm lỗi có nhãn |
|---|---|---|---|
| wall-clock (`Time` / `inject_time`) ← đang dùng | 95,660 | 704 | 101 / 101 |
| epoch (`TimeStamp` / `inject_timestamp`) | 95,652 | 527 | 75 / 101 |

Pipeline Giai đoạn 1 dùng cột epoch, nên đã âm thầm mất phần chênh lệch ở trên. Split cam kết trong `data/splits/` dùng wall-clock. Cờ `--time-source epoch` được giữ lại để tái lập đúng nhãn của Giai đoạn 1 ở cổng chặn Tuần 3 (Precision 0.32, FPR 0.046) — xem `docs/experiment-log.md`.

## 6. Câu hỏi 5 — Trace có dựng được call chain không

| Chỉ số | Giá trị | Tỷ lệ trên tổng span |
|---|---|---|
| File trace đã quét | 303 | — |
| Trace phân biệt | 88,324 | — |
| Tổng span | 4,123,948 | 100% |
| Span có `SpanID` | 4,123,948 | 100.00% |
| Span gốc (`ParentID == root`) | 88,325 | 2.14% |
| Span có `ParentID` là span khác | 4,035,623 | 97.86% |
| → trong đó `ParentID` giải được về span cùng trace | 4,035,623 | 97.86% |
| → `ParentID` mồ côi | 0 | 0.00% |

Cạnh service → service suy ra trực tiếp từ quan hệ cha–con: **68 cạnh** trên **38 service**. Đây là số liệu sơ bộ cho `scripts/build_service_graph.py` ở Tuần 4, không thay thế phần đo coverage của tuần đó.

10 cạnh nặng nhất:

| Từ service | Đến service | Số span |
|---|---|---|
| frontend | productcatalogservice | 364,269 |
| frontend | currencyservice | 231,993 |
| frontend | cartservice | 70,207 |
| recommendationservice | productcatalogservice | 55,724 |
| frontend | recommendationservice | 55,724 |
| frontend | adservice | 44,554 |
| frontend | shippingservice | 16,981 |
| ts-seat-service | ts-config-service | 10,615 |
| checkoutservice | productcatalogservice | 7,422 |
| ts-seat-service | ts-order-service | 7,326 |

## 7. Rủi ro và điểm cần lưu ý

- **Mất cân bằng lớp nặng (1 : 135).** Precision phụ thuộc trực tiếp vào tỷ lệ này, nên split phải giữ nguyên toàn bộ cửa sổ normal. Lấy mẫu bớt normal sẽ đẩy Precision lên và làm hỏng cổng chặn Tuần 3.
- **Chỉ có 704 fault window trên toàn dataset.** Các lần chạy `n_windows: 300` trong `eval/configs/` là lấy mẫu từ split, không phải toàn bộ split; cần ghi rõ cách lấy mẫu khi báo cáo.
- **1,209 dòng metric có hai cột thời gian lệch nhau** (xem §5). Đã xử lý bằng cách join theo cột wall-clock, nhưng bất kỳ code nào sau này đọc `TimeStamp` trực tiếp sẽ gặp lại đúng lỗi này — Tuần 2 phải dùng `packages/schemas/loaders.py` chứ không tự parse CSV.
- Nhãn gắn ở mức pod nhưng Nhánh B báo cáo ở mức service. Với service có nhiều replica (`ts-basic-service`, `ts-food-service`, `ts-travel-service`, `ts-route-service`, `ts-contacts-service`, `ts-preserve-service`, `ts-verification-code-service`, `productcatalogservice`), Hit@1 mức service dễ hơn mức pod. Phải nói rõ trong luận văn là đang chấm ở mức nào.

## 8. Tệp sinh ra

| Tệp | Commit vào git | Mô tả |
|---|---|---|
| `docs/label-audit.md` | có | Chính tài liệu này |
| `data/window_index.csv` | không (`data/*` bị ignore) | Bảng cửa sổ đã gán nhãn, sinh lại được bằng script này |
| `data/splits/{dev,val,test}.json` | có | Do `scripts/make_splits.py` sinh |

