# M9 — RCA Agent (BẢN NHÁP — mới xong M9-A trên `val`)

| | |
|---|---|
| Ngày | 2026-11-16 (M9-A xong; M9-B trên `test` chưa chạy) |
| Hạn mục tiêu | 2027-01-03 |
| Kết luận | **CHƯA QUA** — M9-A xong, đã đo đủ ba chỉ số DoD trên `val`: JSON valid rate đạt (1,000), Hit@1 / Hit@3 có số (0,636 / 0,636, bằng baseline), **ARR trên `network_delay` không đạt** (0,25 < 0,30); còn M9-B (bảng H5 trên `test`) |
| Commit | `e455004` (code + quy tắc chọn, trước khi có số `val`) → `77786ec` (**chỉ** `eval/configs/rca_final.yaml`) → commit kết quả và tài liệu M9-A |
| Quyết định liên quan | QĐ-037 (cắt mức 2, chia M9-A / M9-B), QĐ-039 (V36 (a)), **QĐ-040**, **QĐ-041** |

Mọi con số dưới đây thuộc **`val`**. Phiên M9-A không đọc, không chạy, không tạo gì thuộc `test`.

## 1. Kết quả hiện tại

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
| DoD: bảng H5 trên `test` | Chưa | M9-B |
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
| V40 | Định nghĩa "incident cascade" của H5 — agent tự quyết, chờ xác nhận | (a) lần tiêm lỗi có cảnh báo chạm ≥ 2 service; (b) ≥ 2 cảnh báo | **(a)**, đã ghi trong `rca_final.yaml` trước khi chạm `test`. Trên `val` chỉ 1 lần tiêm lỗi thoả (a) | Nên xác nhận trước M9-B; đổi sau khi thấy số `test` là không được |
| V41 | Incident gộp hai lần tiêm lỗi liền nhau **cùng service gốc** vẫn tính `ambiguous` — agent tự quyết | (a) giữ nguyên văn `02` §4.3; (b) coi là `labelled` khi cùng service gốc | **(a)**: không nới định nghĩa sau khi thấy rằng (b) có lợi cho mức 1 | Không |
| V42 | `store.py` nằm ở `services/rca_agent/` thay vì `packages/storage/` — agent tự quyết | (a) để nguyên; (b) M10 chuyển sang `packages/storage/postgres.py` | (a) cho tới M10 | Không |
| V43 | Ba file sửa ngoài vùng P2, đều chỉ thêm: `packages/schemas/models.py` (model báo cáo `03` §2), `tests/test_harness.py` (loại config `rca`), `eval/__main__.py` (lệnh con `rca`) — agent tự quyết | (a) giữ; (b) chuyển chỗ | (a): model dùng chung phải ở `packages/schemas` (quy tắc R-B2) | Không |
| V44 | DoD "ARR ≥ 30% trên `network_delay`" không đạt trên `val` (0,25) | (a) ghi nhận không đạt, sang M9-B; (b) dừng M9 | **(a)**: nguyên nhân là recall của CTAV trên `network_delay` (3 / 9 lần có cảnh báo), nằm ngoài RCA; không có tham số RCA nào sửa được mà không đổi phương pháp đã đóng băng | Cần bạn đồng ý để M9-B chạy |
| — | Triển vọng H5 (không phải việc cần quyết, chỉ để biết trước) | | Trên `val`: Hit@3 0,636 < 0,80 và ΔHit@1 = 0. Nếu incident trên `test` cũng chủ yếu một service thì hai vế đó của H5 sẽ không đạt | Không |

## 4. Plan cho mốc tiếp theo (M9-B, rồi M10)

- `eval/configs/rca_final_test.yaml` = `rca_final.yaml`, chỉ đổi `split: test`, thêm `h5_test: true`, `input.alerts_run`
  và `input.evidence_run` sang run `test` tương ứng, `run_id`; in `git diff --no-index` hai file, commit trước khi chạy.
- Chạy một lần; kiểm dòng `method fingerprint b0c54fa68ef65535` in ra trùng bản `val`.
- Dòng độ nhạy V36 (a): cùng tham số, `input: {ctav_config: <config CTAV test>, variant: c3_rolling_baseline,
  evidence_run: <run C1 test>}`, `run_id` riêng, ghi nhãn "độ nhạy, ngoài bản đăng ký".
- Ước chi phí trước khi chạy (harness tự in và dừng nếu vượt 1 USD): `val` tốn 0,0017 USD / incident.
- Bảng H5 lấy từ `rca.json`: `main.hit.level1_hit1`, `level1_hit3`, `d_hit1_ci95`, `main.reduction.cascade`,
  `main.per_injection` (tách "trên incident có cảnh báo" và "trên mọi lần tiêm lỗi").
- QĐ-042..: kết quả H5; hoàn tất báo cáo này; §5.9 vào bản nháp chương kết quả `test`; chuyển `CURRENT-MILESTONE.md` sang M10.
- DoD M9: như trên + bảng kiểm định H5 trên `test`.
