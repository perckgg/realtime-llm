# Coverage của service dependency graph

> Sinh tự động bởi `py scripts/build_service_graph.py` (M3, `02` §1.3). Không sửa tay.

## 1. Đồ thị

| | |
|---|---|
| Nguồn | Mọi file trace Nezha (`rca_data` + `construct_data`): 307 file, 4,180,244 span |
| Liên kết cha–con trong cùng file | 4,090,762 (cùng service: 3,130,759; span gốc: 89,482) |
| Service (node) | 56 |
| Cạnh có hướng / vô hướng | 68 / 68 |
| `min_edge_count` | 5 (bị loại: 0) |
| Thành phần liên thông | 20 (lớn nhất 28 service) |
| Service cô lập | 18: ts-admin-basic-info-service, ts-admin-order-service, ts-admin-route-service, ts-admin-travel-service, ts-admin-user-service, ts-avatar-service, ts-consign-price-service, ts-consign-service, ts-food-delivery-service, ts-news-service, ts-notification-service, ts-rebook-service, ts-route-plan-service, ts-ticket-office-service, ts-travel-plan-service, ts-ui-dashboard, ts-voucher-service, ts-wait-order-service |

## 2. Ba chỉ số của `02` §1.3

Bảng GC-1. Coverage.

| Chỉ số | Giá trị | Ngưỡng | Kết luận |
|---|---|---|---|
| Service coverage (service có metric và có ≥ 1 cạnh / service có metric) | 38/56 = 67.9% | < 80% → cảnh báo | Cảnh báo |
| Edge density (cạnh có hướng / n(n−1)) | 0.0221 | ghi nhận | Đồ thị thưa |
| Fault window có service trong graph — `dev` | 149/149 = 100.0% | < 60% → fallback BM25 | Không cần fallback |
| Fault window có service trong graph — `val` | 209/209 = 100.0% | < 60% → fallback BM25 | Không cần fallback |
| Fault window có service trong graph — `test` | 346/346 = 100.0% | < 60% → fallback BM25 | Không cần fallback |

Fault window theo hệ thống (có service trong graph): `dev` {'online_boutique': 85, 'train_ticket': 64}; `val` {'online_boutique': 112, 'train_ticket': 97}; `test` {'online_boutique': 197, 'train_ticket': 149}

## 3. So với đồ thị GĐ1 (`legacy/outputs/phase2/service_graph_directed.json`)

- Cạnh: GĐ2 68, GĐ1 68, trùng 68 (cùng trọng số: 68).
- Cạnh chỉ có ở GĐ2: không; chỉ có ở GĐ1: không.
- Node: GĐ2 56, GĐ1 56; chỉ ở GĐ2: không; chỉ ở GĐ1: không.

## 4. Nhận xét

- Service cô lập là các service train-ticket không có span cha/con khác service trong dữ liệu; chúng không bị tiêm lỗi trong bất kỳ split nào nên không ảnh hưởng fault window.
- Cạnh nhẹ nhất vẫn nặng hơn nhiều `min_edge_count`, nên bộ lọc nhiễu của `02` §1.3 không đổi gì.
