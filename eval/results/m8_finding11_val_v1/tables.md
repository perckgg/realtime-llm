**Bảng F11-1. Phát hiện 11 trên `val` (cửa sổ có telemetry), theo việc service của cảnh báo có ngưỡng `dev` hay không.**

| | Có ngưỡng `dev` | Không có ngưỡng `dev` |
|---|---:|---:|
| Service | 11 | 30 |
| Service có fault | 8 | 10 |
| Cửa sổ | 1438 | 6198 |
| Fault | 104 | 105 |
| Fault là candidate | 50 | 59 |
| C1: TP | 32 | 23 |
| CTAV: TP | 29 | 0 |
| C1 TP bị C3 hạ | 3 | 23 |
| C1: FP | 290 | 316 |
| CTAV: FP | 51 | 0 |
| Recall C1 | 0,308 | 0,219 |
| Recall CTAV | 0,279 | 0,000 |

Recall CTAV mất so với C1 ở nhóm không có ngưỡng `dev`: 0,110 (23 − 0 TP trên 209 fault).

**Bảng F11-2. Fault theo service trên `val`.**

| Service | Ngưỡng `dev` | Fault | C1 TP | CTAV TP |
|---|---|---:|---:|---:|
| adservice | **không** | 21 | 8 | 0 |
| cartservice | có | 14 | 7 | 6 |
| currencyservice | **không** | 7 | 0 | 0 |
| emailservice | **không** | 7 | 4 | 0 |
| paymentservice | có | 14 | 0 | 0 |
| productcatalogservice | **không** | 14 | 2 | 0 |
| recommendationservice | có | 28 | 13 | 13 |
| shippingservice | có | 7 | 4 | 4 |
| ts-basic-service | **không** | 7 | 0 | 0 |
| ts-contacts-service | **không** | 14 | 0 | 0 |
| ts-food-service | **không** | 7 | 2 | 0 |
| ts-preserve-service | **không** | 7 | 5 | 0 |
| ts-price-service | có | 7 | 0 | 0 |
| ts-route-service | **không** | 7 | 0 | 0 |
| ts-security-service | có | 7 | 0 | 0 |
| ts-travel-service | có | 14 | 6 | 4 |
| ts-travel2-service | có | 13 | 2 | 2 |
| ts-verification-code-service | **không** | 14 | 2 | 0 |
