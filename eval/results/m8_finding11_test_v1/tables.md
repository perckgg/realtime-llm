**Bảng F11-1. Phát hiện 11 trên `test` (cửa sổ có telemetry), theo việc service của cảnh báo có ngưỡng `dev` hay không.**

| | Có ngưỡng `dev` | Không có ngưỡng `dev` |
|---|---:|---:|
| Service | 10 | 32 |
| Service có fault | 9 | 11 |
| Cửa sổ | 1428 | 10557 |
| Fault | 135 | 211 |
| Fault là candidate | 93 | 131 |
| C1: TP | 29 | 67 |
| CTAV: TP | 14 | 0 |
| C1 TP bị C3 hạ | 15 | 67 |
| C1: FP | 99 | 1136 |
| CTAV: FP | 64 | 0 |
| Recall C1 | 0,215 | 0,318 |
| Recall CTAV | 0,104 | 0,000 |

Recall CTAV mất so với C1 ở nhóm không có ngưỡng `dev`: 0,194 (67 − 0 TP trên 346 fault).

**Bảng F11-2. Fault theo service trên `test`.**

| Service | Ngưỡng `dev` | Fault | C1 TP | CTAV TP |
|---|---|---:|---:|---:|
| adservice | **không** | 21 | 9 | 0 |
| cartservice | có | 14 | 1 | 1 |
| checkoutservice | **không** | 35 | 17 | 0 |
| currencyservice | **không** | 21 | 10 | 0 |
| emailservice | **không** | 21 | 2 | 0 |
| frontend | có | 50 | 15 | 7 |
| paymentservice | có | 7 | 0 | 0 |
| productcatalogservice | **không** | 14 | 8 | 0 |
| recommendationservice | có | 7 | 0 | 0 |
| shippingservice | có | 7 | 1 | 1 |
| ts-basic-service | **không** | 32 | 5 | 0 |
| ts-contacts-service | **không** | 7 | 0 | 0 |
| ts-food-service | **không** | 18 | 9 | 0 |
| ts-preserve-service | **không** | 7 | 7 | 0 |
| ts-price-service | có | 7 | 0 | 0 |
| ts-route-service | **không** | 14 | 0 | 0 |
| ts-security-service | có | 7 | 0 | 0 |
| ts-travel-service | có | 29 | 8 | 2 |
| ts-travel2-service | có | 7 | 4 | 3 |
| ts-verification-code-service | **không** | 21 | 0 | 0 |
