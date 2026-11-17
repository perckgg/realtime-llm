# M9 — RCA Agent

| | |
|---|---|
| Ngày hoàn tất thực nghiệm | 2026-11-17 (M9-A trên `val` 2026-11-16; M9-B trên `test` 2026-11-17) |
| Hạn mục tiêu | 2027-01-03 (sớm 47 ngày) |
| Kết luận | **CHỜ NGƯỜI DÙNG XEM** — mọi việc 1–11 đã làm. **H5 không được chấp nhận trên `test`** (Hit@1 0,471; Hit@3 0,471; ΔHit@1 = 0; không có lỗi cascade để đo ARR). DoD trên `val`: JSON valid rate đạt, Hit@k có số, **ARR `network_delay` không đạt** (0,25 < 0,30) |
| Commit | `e455004` (code + quy tắc chọn, trước số `val`) → `77786ec` (**chỉ** `rca_final.yaml`) → `2b215cf` (kết quả `val`) → `7ebe57a` (hai config `test`, trước khi chạy) → commit kết quả `test` và tài liệu |
| Quyết định liên quan | QĐ-037, QĐ-039, **QĐ-040**, **QĐ-041**, **QĐ-042** |

Mục 1 chia hai phần: **1B trên `test`** (H5, chạy một lần) và **1A trên `val`** (chọn tham số, DoD). Phiên M9-A không
đọc gì thuộc `test`; `test` chỉ được chạm sau commit `77786ec` và `7ebe57a`.

## 1. Kết quả hiện tại

### 1B. H5 trên `test` (QĐ-042)

**Bảng 4. Kiểm định H5 theo bản đăng ký `be2b985`** (`rca_final_test_v1`: 78 cảnh báo của `ctav_final_test_v1` → 38
incident, 17 có nhãn; CI95 bootstrap 1.000 mẫu, seed 42).

| Vế của H5 | Số đo trên `test` | CI95 | Đạt? |
|---|---|---|---|
| Hit@1 ≥ 0,60 | 8 / 17 = **0,471** | [0,235; 0,706] | **Không** |
| Hit@3 ≥ 0,80 | 8 / 17 = **0,471** | [0,235; 0,706] | **Không** |
| Cận dưới CI ΔHit@1 (RCA − baseline) > 0 | **0,000** (baseline 8 / 17, 0 cặp lệch) | [0,000; 0,000] | **Không** |
| Alert Reduction ≥ 30% trên incident cascade | **không tính được** — 0 / 50 lần tiêm lỗi là cascade | — | **Không** |

**Bảng 5. `val` cạnh `test` và dòng độ nhạy V36 (a).**

| | `val` | **`test` — đăng ký** | `test` — độ nhạy, **ngoài bản đăng ký** (`c3_rolling_baseline`) |
|---|---|---|---|
| Cảnh báo / service có cảnh báo | 80 / 8 | 78 / 5 | 438 / 22 |
| Lần tiêm lỗi: tổng / có incident có nhãn / chỉ trong `ambiguous` / không có cảnh báo | 30 / 10 / 2 / 18 | 50 / 17 / 4 / **29** | 50 / 34 / 15 / 1 |
| Incident: tổng / có nhãn / `ambiguous` / không ứng với lỗi | 26 / 11 / 1 / 14 | 38 / 17 / 3 / 18 | 114 / 48 / 14 / 52 |
| Incident nhiều service | 1 | **0** | 39 |
| Cảnh báo mỗi incident: trung vị / lớn nhất | 3 / 6 | 1 / 9 | 2 / 31 |
| Hit@1 mức 1 — **trên incident có cảnh báo (con số đăng ký)** | 0,636 [0,364; 0,909] | **0,471 [0,235; 0,706]** | 0,208 [0,104; 0,333] |
| Hit@3 mức 1 | 0,636 | **0,471 [0,235; 0,706]** | 0,313 [0,188; 0,458] |
| Hit@1 / Hit@3 baseline | 0,636 / 0,636 | 0,471 / 0,471 | 0,229 / 0,313 |
| ΔHit@1 ghép cặp | 0,000 [0; 0] | **0,000 [0; 0]** | −0,021 [−0,063; 0,000] |
| Hit@1 / Hit@3 **trên mọi lần tiêm lỗi** (không phải con số đăng ký) | 0,200 / 0,200 | 0,160 [0,060; 0,280] / 0,160 | 0,200 / 0,280 |
| ARR mọi cảnh báo | 0,675 [0,600; 0,730] | 0,513 [0,362; 0,626] | 0,740 [0,654; 0,796] |
| ARR cảnh báo trong lỗi | 0,667 | 0,556 [0,382; 0,674] | 0,695 [0,587; 0,762] |
| ARR cascade (số lần tiêm lỗi cascade) | 0,667 (1) | — (0) | 0,704 [0,591; 0,777] (41) |
| ARR `network_delay` | 0,250 | 0,545 [0,273; 0,703] | 0,720 [0,422; 0,835] |
| JSON valid rate | 26 / 26 | 38 / 38 | 114 / 114 |
| Lần gọi LLM / USD theo token | 26 / 0,0436 | 38 / 0,0495 | 114 / 0,1841 |

**Nguyên nhân, đọc từ dữ liệu `test`.**
1. 78 cảnh báo chỉ nằm ở 5 service (Phát hiện 11) ⇒ cả 38 incident đều một service ⇒ mức 1 = baseline ở mọi incident,
   Hit@3 = Hit@1, không có lỗi cascade nào.
2. 9 / 17 incident trượt cùng một dạng: cảnh báo ở service phía gọi (`frontend` ×5, `ts-travel-service` ×4), lỗi tiêm ở
   service phía sau không có cảnh báo nào. 8 incident trúng đều là lỗi tiêm ngay tại service có cảnh báo.
3. 29 / 50 lần tiêm lỗi không có cảnh báo CTAV nào (8 / 9 `return`, 4 / 5 `cpu_consumed`, 7 / 10 `exception`, 5 / 11
   `cpu_contention`, 5 / 15 `network_delay`): **không thể định vị**.
4. Dòng độ nhạy: có cảnh báo ở 49 / 50 lần tiêm lỗi và 39 incident nhiều service, nhưng Hit@1 chỉ 0,208 và thấp hơn
   baseline 0,021. Service gốc thật chỉ nằm trong số service có cảnh báo ở 15 / 48 incident có nhãn (= số trúng Hit@3),
   nên trần là 0,313. H5 không đạt không chỉ vì tập đăng ký hẹp.
5. `test` có incident nhỏ hơn `val` (trung vị 1 cảnh báo so với 3) nên ARR chung thấp hơn; không chọn lại tham số nào.

Chi phí API cả mốc M9: 178 lần gọi, **0,2772 USD theo token** (ngân sách 1 USD). PostgreSQL: 38 + 114 `incidents`,
38 + 114 `diagnostic_reports`, 0 `diagnostic_rejected` cho hai run `test`. Cả hai run in dấu vân tay `b0c54fa68ef65535`.

### 1A. Trên `val` (QĐ-040, QĐ-041)

Mọi con số dưới đây thuộc **`val`**. Phiên M9-A không đọc, không chạy, không tạo gì thuộc `test`.

| Việc / DoD | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|
| 1. Harness `py -m eval rca --config ...`: đọc cảnh báo CTAV, gom incident, định vị, chấm Hit@1 / Hit@3 có CI bootstrap; ghi `incidents` vào PostgreSQL | Có | `eval/harness/rca.py`, lệnh con `rca` ở `eval/__main__.py`; `services/rca_agent/store.py`; PostgreSQL: 26 `incidents`, 26 `diagnostic_reports`, 0 `diagnostic_rejected` cho `rca_final_val_v1` |
| 2. Quét `T_group ∈ {180, 300, 600}` s; ARR chung / cascade / `network_delay`; quy tắc chọn viết trước | Có | `rca_select_val_v1`; quy tắc `select_t_group` ở commit `e455004`, trước lần chạy đầu; Bảng 1 |
| 3. Propagation mức 1 + baseline + ΔHit@1 ghép cặp có CI | Có | `services/rca_agent/propagation.py`; Bảng 2 |
| 4. Propagation mức 2 | **Không làm** | Đã cắt theo `04` §9 ưu tiên 1 (QĐ-037, QĐ-040 mục 10) |
| 5. `summarizer.py`: JSON `03` §2, validator + `diagnostic_rejected`, `require_evidence`, chặn câu lệnh; đo JSON valid rate | Có | `services/rca_agent/summarizer.py`; `rca_mock_val_v1` (mock) rồi `rca_final_val_v1` (Gemini thật, 26 lần gọi, 0,0436 USD) |
| 6. Chốt `eval/configs/rca_final.yaml` bằng commit riêng | Có | `77786ec`; dấu vân tay phương pháp `b0c54fa68ef65535` |
| **DoD: ARR ≥ 30% trên `network_delay`** | **Không** | **0,250 [0,000; 0,500]** (4 cảnh báo → 3 incident); nguyên nhân ở dưới |
| **DoD: có Hit@1 / Hit@3 mức 1 và baseline** | Có | Mức 1: 0,636 / 0,636; baseline: 0,636 / 0,636 (n = 11) |
| **DoD: JSON valid rate ≥ 0,95** | **Có** | 26 / 26 = 1,000 |
| 8–11. Config `test` commit trước khi chạy; H5 một lần; dòng độ nhạy; QĐ | Có | `7ebe57a`; `rca_final_test_v1`, `rca_sens_test_c3rolling_v1`; QĐ-042; mục 1B |
| **DoD: bảng kiểm định H5 trên `test`** | **Có bảng — H5 không được chấp nhận** | Bảng 4 |
| `pytest`, `mypy`, `ruff` | Sạch | 239 test qua (gồm `tests/test_storage.py` và test ghi PostgreSQL thật); `mypy packages services` sạch; `ruff` chỉ còn E402 cũ ở `scripts/` |

### Đầu vào

80 cảnh báo của `ctav_final_val_v1` ở 8 service. 36 cảnh báo giao thời gian với một lần tiêm lỗi (29 nằm đúng pod bị
tiêm — 29 TP mức cửa sổ của M6; 7 ở pod / service khác trong lúc có lỗi), 44 nằm ngoài mọi lần tiêm lỗi. `val` có
30 lần tiêm lỗi; **18 lần không có cảnh báo CTAV nào** (5 / 5 `return`, 4 / 6 `exception`, 6 / 9 `network_delay`,
2 / 7 `cpu_contention`, 1 / 3 `cpu_consumed`).

### Số liệu chính

**Bảng 1. Quét `T_group` trên `val`** (`rca_select_val_v1`; CI95 bootstrap 1.000 mẫu, seed 42, lấy mẫu lại theo 13
cụm thời gian của 600 s).

| `T_group` | Incident | `labelled` | `ambiguous` | `no_fault` | ARR mọi cảnh báo [CI95] | ARR trong lỗi [CI95] | ARR `network_delay` [CI95] | Hit@1 mức 1 | Hit@1 baseline |
|---:|---:|---:|---:|---:|---|---|---|---|---|
| **180 s (chọn)** | 26 | 11 | 1 | 14 | 0,675 [0,543; 0,728] | 0,667 [0,545; 0,733] | 0,250 [0,000; 0,500] | 7 / 11 = 0,636 | 0,636 |
| 300 s | 19 | 9 | 2 | 8 | 0,763 [0,585; 0,835] | 0,694 [0,550; 0,788] | 0,250 [0,000; 0,500] | 5 / 9 = 0,556 | 0,556 |
| 600 s | 17 | 9 | 2 | 6 | 0,788 [0,590; 0,865] | 0,694 [0,550; 0,788] | 0,250 [0,000; 0,500] | 5 / 9 = 0,556 | 0,556 |

Quy tắc viết trước (QĐ-040 mục 7) chọn **180 s**: 180 s có 1 incident `ambiguous`, 300 s và 600 s có 2 (300 s gộp
hai lần tiêm lỗi cách nhau 240 s trên `recommendationservice`). Trên tập cảnh báo trong lỗi, 300 s − 180 s là
+0,028 [0,000; +0,067]: cận dưới không > 0. Dấu hiệu bất thường giữ mặc định `alert`: `candidate` − `alert` =
+0,091 Hit@1 [0,000; +0,273].

**Bảng 2. Cấu hình chốt trên `val`** (`rca_final_val_v1`: `T_group` 180 s, mức 1 với dấu hiệu `alert`; CI95
bootstrap 1.000 mẫu, seed 42; ARR lấy mẫu lại theo 22 cụm thời gian, Hit@k theo 11 incident `labelled`).

| Chỉ số | Giá trị | CI95 | Ngưỡng |
|---|---|---|---|
| Incident / `labelled` / `ambiguous` / `no_fault` | 26 / 11 / 1 / 14 | | |
| Incident một service / nhiều service | 25 / 1 | | |
| ARR mọi cảnh báo (80 → 26) | 0,675 | [0,600; 0,730] | |
| ARR cảnh báo trong lỗi (36 → 12) | 0,667 | [0,565; 0,725] | |
| ARR `cascade` (6 → 2; chỉ 1 lần tiêm lỗi chạm ≥ 2 service) | 0,667 | suy biến | H5: ≥ 0,30 trên `test` |
| **ARR `network_delay`** (4 → 3) | **0,250** | [0,000; 0,500] | DoD: ≥ 0,30 — **không đạt** |
| **Hit@1 mức 1** | **7 / 11 = 0,636** | [0,364; 0,909] | H5: ≥ 0,60 trên `test` |
| **Hit@3 mức 1** | **7 / 11 = 0,636** | [0,364; 0,909] | H5: ≥ 0,80 trên `test` |
| Hit@1 / Hit@3 baseline (anomaly score cao nhất) | 0,636 / 0,636 | [0,364; 0,909] | |
| **ΔHit@1 (mức 1 − baseline), ghép cặp** | **0,000** | [0,000; 0,000], 0 cặp lệch | H5: cận dưới > 0 |
| Hit@1 = Hit@3 trên mọi lần tiêm lỗi | 6 / 30 = 0,200 | [0,067; 0,333] | |
| Lần tiêm lỗi có incident `labelled` / chỉ nằm trong incident `ambiguous` / không có cảnh báo | 10 / 2 / 18 | | |
| **JSON valid rate** (Gemini thật) | **26 / 26 = 1,000** | [1,000; 1,000] | DoD: ≥ 0,95 — **đạt** |

**Bảng 3. Hit@1 theo loại lỗi trên `val`** (incident `labelled`; cột cuối tính trên mọi lần tiêm lỗi).

| Loại lỗi | Lần tiêm lỗi | Có cảnh báo | Incident `labelled` | Trúng hạng 1 (mức 1 = baseline) | Trúng / mọi lần tiêm lỗi |
|---|---:|---:|---:|---:|---:|
| `cpu_contention` | 7 | 5 | 6 | 5 | 4 / 7 |
| `cpu_consumed` | 3 | 2 | 2 | 2 | 2 / 3 |
| `network_delay` | 9 | 3 | 3 | 0 | 0 / 9 |
| `exception` | 6 | 2 (cùng một incident `ambiguous`) | 0 | — | 0 / 6 |
| `return` | 5 | 0 | 0 | — | 0 / 5 |
| **Tổng** | **30** | **12** | **11** | **7** | **6 / 30** |

### Nguyên nhân, đọc từ dữ liệu

1. **ARR `network_delay` không đạt vì thiếu cảnh báo, không vì `T_group`.** Chỉ 3 / 9 lần tiêm `network_delay` có
   cảnh báo, với 1, 2 và 1 cảnh báo. Mỗi lần thành đúng một incident, nên 0,25 là **trần** của chỉ số trên 4 cảnh báo
   này ở mọi `T_group` (Bảng 1: ba dòng bằng nhau).
2. **Mức 1 trùng baseline trên cả 11 incident được chấm.** 25 / 26 incident chỉ có một service; khi đó cả hai cách
   trả về chính service đó, và Hit@3 = Hit@1. Incident nhiều service duy nhất là `ambiguous` (hai lần tiêm
   `exception` liền nhau, cùng service gốc `ts-travel2-service`) nên không được chấm; ở đó mức 1 xếp đúng service
   gốc hạng 1, baseline xếp `ts-gateway-service`.
3. **4 incident trượt đều là "cảnh báo nổ ở service khác service gốc".** Ba incident `network_delay`:
   `recommendationservice` thay cho `productcatalogservice` (callee trực tiếp), `ts-travel2-service` thay cho
   `ts-contacts-service` và `ts-security-service` (không có đường gọi có hướng). Một incident `cpu_contention`:
   `ts-travel2-service` cảnh báo trước, `ts-travel-service` (gốc) cảnh báo sau 3 phút; hai service không kề nhau
   trên đồ thị nên thành hai incident, incident sau trúng.
4. **14 / 26 incident không ứng với lỗi nào** — 44 cảnh báo sai của CTAV, dồn ở `ts-travel2-service` và
   `ts-auth-service` ngày 2023-01-30.
5. **Summarizer hợp lệ về cú pháp nhưng loại lỗi không phân biệt được:** 22 / 26 báo cáo ghi `cpu_contention`, 4 ghi
   `network_delay`, không lần nào `unknown` (kể cả 14 incident `no_fault`); trên 11 incident `labelled` khớp 7.

### Lệnh tái lập

```bash
docker compose --profile dev up -d
py -m eval rca --config eval/configs/rca_select_val.yaml   # quét, 0 LLM
py -m eval rca --config eval/configs/rca_mock_val.yaml     # summarizer mock + PostgreSQL
py -m eval rca --config eval/configs/rca_final.yaml        # Gemini (đã cache: 0 USD)
```

`run_id` đã tồn tại (thư mục kết quả hoặc `run_registry`) thì lệnh dừng: đổi `run_id` trong config.

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Cách gán nhãn incident: cảnh báo thuộc lần tiêm lỗi theo **giao thời gian, bất kể service** | `eval/harness/rca.py` `alert_injections`, `label_incidents` | Quyết định mẫu số của Hit@k (11 incident) và tập ARR; định nghĩa khác sẽ ra số khác |
| 2 | Quy tắc mức 1: đi một bước **theo chiều gọi**, phiếu theo service | `services/rca_agent/propagation.py` `backward_one_hop` | `01` §6.5 chỉ mô tả một câu; đây là cách tôi cụ thể hoá |
| 3 | Thứ tự commit: quy tắc chọn có trước số `val` | `git show e455004 --stat`, `git show 77786ec --stat` | Là căn cứ để nói `T_group` không bị chọn theo kết quả |
| 4 | Chặn câu lệnh thực thi: danh sách từ lệnh và các ca không được chặn nhầm | `services/rca_agent/summarizer.py` `looks_executable`, `tests/test_rca_summarizer.py` | Danh sách do tôi đặt; bỏ sót thì lọt lệnh, quá rộng thì loại nhầm mô tả |
| 5 | 3 báo cáo bất kỳ trong `eval/results/rca_final_val_v1/reports.jsonl` | file đó | JSON valid rate 1,000 không nói gì về nội dung đúng hay sai |
| 6 | Các file sửa ngoài vùng P2 (chỉ thêm) | `packages/schemas/models.py`, `tests/test_harness.py`, `eval/__main__.py` | V43 |

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| V40 | Định nghĩa "incident cascade" của H5 — agent tự quyết, chờ xác nhận | (a) lần tiêm lỗi có cảnh báo chạm ≥ 2 service; (b) ≥ 2 cảnh báo | **(a)**, đã ghi trong `rca_final.yaml` trước khi chạm `test`. Trên `val` chỉ 1 lần tiêm lỗi thoả (a) | Không còn đổi được: `test` đã chạy với (a). Theo (a) `test` có 0 lần tiêm lỗi cascade nên vế ARR của H5 không đo được |
| V41 | Incident gộp hai lần tiêm lỗi liền nhau **cùng service gốc** vẫn tính `ambiguous` — agent tự quyết | (a) giữ nguyên văn `02` §4.3; (b) coi là `labelled` khi cùng service gốc | **(a)**: không nới định nghĩa sau khi thấy rằng (b) có lợi cho mức 1 | Không |
| V42 | `store.py` nằm ở `services/rca_agent/` thay vì `packages/storage/` — agent tự quyết | (a) để nguyên; (b) M10 chuyển sang `packages/storage/postgres.py` | (a) cho tới M10 | Không |
| V43 | Ba file sửa ngoài vùng P2, đều chỉ thêm: `packages/schemas/models.py` (model báo cáo `03` §2), `tests/test_harness.py` (loại config `rca`), `eval/__main__.py` (lệnh con `rca`) — agent tự quyết | (a) giữ; (b) chuyển chỗ | (a): model dùng chung phải ở `packages/schemas` (quy tắc R-B2) | Không |
| ~~V44~~ (đã chốt (a) 2026-11-17: người dùng cho sang M9-B) | DoD "ARR ≥ 30% trên `network_delay`" không đạt trên `val` (0,25) | (a) ghi nhận không đạt, sang M9-B; (b) dừng M9 | **(a)**: nguyên nhân là recall của CTAV trên `network_delay` (3 / 9 lần có cảnh báo), nằm ngoài RCA; không có tham số RCA nào sửa được mà không đổi phương pháp đã đóng băng | Cần bạn đồng ý để M9-B chạy |
| V45 | **H5 không được chấp nhận** — cách trình bày trong luận văn | (a) báo đúng như Bảng 4, kèm dòng độ nhạy và phân tích nguyên nhân (cảnh báo không rơi vào service gốc); (b) như (a) và nêu rõ ở chương thảo luận rằng nhánh B chỉ đạt phần gom cảnh báo và sinh báo cáo đúng lược đồ | **(b)** | Không chặn M10; cần trước khi viết chương kết luận |
| V46 | Đóng M9 | DoD của `04` có một dòng không đạt (ARR `network_delay` trên `val`) và H5 không đạt; bảng kiểm định thì đã có | Đóng M9 với kết luận "QUA — H5 không được chấp nhận", theo tiền lệ M8 (H2 không đạt vẫn đóng mốc vì DoD là *có bảng kiểm định*) | **Có** — cần bạn xem báo cáo này để mở M10 |

## 4. Plan cho mốc tiếp theo (M10 — Platform end-to-end + dashboard)

- `services/rca_agent/pipeline.py` điều phối CTAV → grouping → propagation → summary, dùng lại đúng các hàm của M9.
- **Parity với M9-B (QĐ-042):** chạy end-to-end trên `test` phải cho đúng 38 incident của `rca_final_test_v1` (so theo
  danh sách `alert_ids`) và đọc summarizer 100% từ cache; M10 chỉ đo thêm E2E latency, token, cache hit.
- `services/api` (FastAPI) đọc ClickHouse / PostgreSQL (`incidents`, `diagnostic_reports` đã có dữ liệu của 4 run).
- Nối 4 màn hình dashboard sang API thật; chế độ demo offline từ cache.
- DoD M10 (`04`): `docker compose --profile dev up -d` + replay → 4 màn hình có dữ liệu thật, chạy được khi rút mạng,
  kịch bản demo `08` §6 chạy trọn.
- Ngân sách API M10–M12: 0 (ngưỡng dừng 1 USD).
