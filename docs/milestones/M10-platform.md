# M10 — Platform end-to-end + dashboard dữ liệu thật

| | |
|---|---|
| Ngày đóng mốc | **2026-11-17** (mở 2026-11-17, QĐ-043) |
| Hạn mục tiêu | 2027-01-10 (**sớm 54 ngày**) |
| Kết luận | **QUA** (đóng 2026-11-17, người dùng đã xem và chốt — **QĐ-049**). Toàn bộ platform end-to-end, 7 endpoint API, dashboard 4 màn hình tiếng Anh, chế độ `DEMO_OFFLINE=1` và bản nháp Chương 6 đã hoàn tất; `0` USD chi phí API mới |
| Commit | `45c75c6` (M10-A), `8f2ba70` (M10-B), `55228a7` (M10-C), `2d933b1` (M10-C.1), `fa80590` (M10-D) *(cộng commit đóng M10-E)* |
| Quyết định liên quan | QĐ-043, QĐ-045, QĐ-046, QĐ-047 (+ bổ sung M10-C.1), QĐ-048, QĐ-049 |

---

## 1. Kết quả hiện tại

Theo dõi DoD theo 5 mốc con (`docs/prompts/M10-handoff.md` §2):

| Mốc con / DoD | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|
| **M10-A:** `pipeline.py` + nạp verdict CTAV vào ClickHouse + grouping/propagation/summary (chỉ đọc cache) + PostgreSQL + parity 26/26 (`val`) & 38/38 (`test`) + `runtime.json` | **Đạt** (2026-11-17) | `services/rca_agent/pipeline.py`, `tests/test_pipeline.py`, `eval/results/pipeline_val_v1/runtime.json`, `eval/results/pipeline_test_v1/runtime.json`; 0 lần gọi API, `method fingerprint b0c54fa68ef65535`; QĐ-045 |
| **M10-B:** `services/api` (FastAPI chỉ đọc, 7 endpoint) + `types.ts` trường policy CTAV + `infra/Dockerfile.api` + `tests/test_api.py` | **Đạt** (2026-11-17) | `services/api/{main,readers,schemas}.py`, `services/web/src/api/types.ts`, `infra/Dockerfile.api`, `docker-compose.yml`, `tests/test_api.py`; 7 endpoint `200 OK` trên `pipeline_{val,test}_v1` (cả qua `TestClient` và container `internship1-api-1`); `/alerts?run_id=pipeline_test_v1` (13.699 dòng) đo thực tế `0,561 s`; QĐ-046 |
| **M10-C:** Nối 4 màn hình sang `VITE_DATA_SOURCE=http` + `ExperimentComparison` bảng tĩnh + service `web` trong compose + `npm run check` sạch | **Đạt** (2026-11-17) | `scripts/m10_experiment_table.py`, `services/web/src/data/experiment_table.json` (`52.004` B), `services/web/src/{App.tsx,api/client.ts,screens/*}`, `services/web/scripts/smoke.tsx`, `infra/Dockerfile.web`, `docker-compose.yml`, `tests/test_experiment_table.py`; 4 container (`web`, `api`, `clickhouse`, `postgres`) `healthy`; `http://127.0.0.1:5173/` & `/api/{health,runs,alerts,incidents}` `200 OK`; `npm.cmd run check` (exit 0), `pytest` `248 passed`; QĐ-047 |
| **M10-C.1:** Sửa lỗi sau review M10-C (F1..F10): chuẩn hoá H1 / H5 khớp Ch5, `policySteps()`, `cache_hit` thật (`_v2`), `run_id` & `alert_count` | **Đạt** (2026-11-17) | `eval/results/m10_experiment_table_v2/experiment_table.json` (`52.379` B), `pipeline_val_v2` (26 / 26 parity, E2E `5.764,165 ms`), `pipeline_test_v2` (38 / 38 parity, E2E `4.242,424 ms`), `npm.cmd run check` sạch, `pytest` `249 passed in 28.75s`, probe proxy `:5173` & `docker compose stop/start api` qua *(Chromium tương tác chưa kiểm do người dùng huỷ subagent)*; bổ sung QĐ-047 |
| **M10-D:** Giao diện 100% tiếng Anh + `pipeline_sens_test_v1` (V48 b'+a') + `m10_pick_demo_cases.py` + `DEMO_OFFLINE=1` + tự kiểm trình duyệt + ảnh + nháp `ch6-demo-platform.md` | **Đạt** (2026-11-17) | `services/web/`, `services/rca_agent/pipeline.py`, `scripts/m10_pick_demo_cases.py`, `eval/results/m10_demo_cases_v1/demo_cases.json`, `tests/test_demo_cases.py`, `eval/results/pipeline_sens_test_v1/runtime.json` (`114/114` parity, `13.699` / `19.794` / `114`, `0` gọi API), 5 ảnh `docs/drafts/figures/m10-*.png`, `docs/drafts/ch6-demo-platform.md`; `npm run check` (`26/26`), `mypy` (43 file), `ruff`, `pytest` **`253 passed`** (`0` skipped); QĐ-048 |
| **M10-E:** Hoàn tất `M10-platform.md` (4 phần + phụ lục), `ch6-demo-platform.md`, tóm tắt gửi GVHD, cập nhật `04` §1 & đóng M10 | **Đạt** (2026-11-17) | `docs/milestones/M10-platform.md`, `docs/drafts/ch6-demo-platform.md` (§6.1–6.5), `docs/drafts/2026-11-17-mail-gvhd-platform.md`, `docs/milestones/README.md`, `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`, `docs/CURRENT-MILESTONE.md`; người dùng đã xem & chốt đóng M10 (**QĐ-049**) |

### Số liệu M10-A (thực đo 2026-11-17, QĐ-045)

**Bảng 1. Parity và số bản ghi DB của `pipeline_val_v1` và `pipeline_test_v1`** (0 lần gọi API, 0,0000 USD).

| Hạng mục | `pipeline_val_v1` (`val`) | `pipeline_test_v1` (`test`) |
|---|---|---|
| Run M9 đối chiếu parity | `rca_final_val_v1` | `rca_final_test_v1` |
| Dòng ClickHouse `fact_alert_evaluation` | 5.677 (80 `TRUE_ALERT`) | 13.699 (78 `TRUE_ALERT`) |
| Dòng ClickHouse `fact_retrieval_trace` | 7.716 | 19.794 |
| PostgreSQL `incidents` / `diagnostic_reports` / `diagnostic_rejected` | 26 / 26 / 0 | 38 / 38 / 0 |
| Parity `alert_ids` | 26 / 26 | 38 / 38 |
| Parity thứ hạng `level1` & `baseline` | 26 / 26 | 38 / 38 |
| Parity hash JSON `DiagnosticReport` | 26 / 26 | 38 / 38 |
| `summarizer` cache hit rate | 26 / 26 (100%) | 38 / 38 (100%) |

**Bảng 2. Độ trễ từng chặng và token trong cache** (`eval/results/pipeline_{val,test}_v1/runtime.json`).
*Lưu ý:* đây là độ trễ **replay từ cache / đĩa**, không phải độ trễ gọi API LLM trực tiếp.

| Chặng / chỉ số | `pipeline_val_v1` (`val`) | `pipeline_test_v1` (`test`) |
|---|---:|---:|
| `load_alerts_ms` | 605,644 ms | 1.238,991 ms |
| `clickhouse_write_ms` | 2.561,603 ms | 1.339,031 ms |
| `grouping_ms` | 3,166 ms | 3,588 ms |
| `propagation_ms` | 1,355 ms | 2,080 ms |
| `summarizer_ms` (cache-only) | 374,643 ms | 465,857 ms |
| `postgres_write_ms` | 340,412 ms | 185,270 ms |
| **Tổng thời gian E2E (`e2e_wall_ms`)** | **5.031,030 ms** | **4.313,077 ms** |
| Token CTAV trong cache (prompt / completion) | 5.173.670 / 691.941 | 12.736.820 / 1.734.808 |
| Token Summarizer trong cache (prompt / completion) | 66.080 / 9.528 | 74.151 / 10.887 |

**Lệnh tái lập M10-A:**
```bash
docker compose --profile dev up -d
py -m services.rca_agent.pipeline --config eval/configs/rca_final.yaml
py -m services.rca_agent.pipeline --config eval/configs/rca_final_test.yaml
```
*(Nếu `pipeline_val_v1` / `pipeline_test_v1` đã có trong DB/thư mục kết quả, truyền `--run-id <mới>` vì không ghi đè `run_id` cũ.)*

### Số liệu M10-C.1 & M10-D — các lượt replay chính thức `_v2` và độ nhạy `pipeline_sens_test_v1` (QĐ-047, QĐ-048)

**Bảng 3. Tóm tắt các lượt replay bổ sung sau kiểm `cache_hit` thật (`_v2`) và dòng độ nhạy V48 `(b')`** (`0` gọi API, tỷ lệ trúng `cache` `100%`, dấu vân tay `b0c54fa68ef65535`).

| Hạng mục / Chỉ số | `pipeline_val_v2` (`val`) | `pipeline_test_v2` (`test` chính thức) | `pipeline_sens_test_v1` (`c3_rolling_baseline`) |
|---|---:|---:|---:|
| Run M9 đối chiếu parity | `rca_final_val_v1` | `rca_final_test_v1` | `rca_sens_test_c3rolling_v1` |
| Dòng ClickHouse `fact_alert_evaluation` (`TRUE_ALERT`) | 5.677 (80) | 13.699 (78) | 13.699 (438) |
| Dòng ClickHouse `fact_retrieval_trace` | 7.716 | 19.794 | 19.794 |
| PostgreSQL `incidents` / `reports` / `rejected` | 26 / 26 / 0 | 38 / 38 / 0 | 114 / 114 / 0 |
| Parity (`alert_ids` / `level1` / JSON hash) | **26 / 26** | **38 / 38** | **114 / 114** |
| Thời gian E2E (`e2e_wall_ms`, replay từ cache) | 5.764,165 ms | 4.242,424 ms | 10.646,898 ms |
| Token CTAV trong cache (prompt / completion) | 5.173.670 / 691.941 | 12.736.820 / 1.734.808 | 12.736.820 / 1.734.808 |
| Token Summarizer trong cache (prompt / completion) | 66.080 / 9.528 | 74.151 / 10.887 | 290.535 / 38.789 |

- **Bộ ca demo chọn tự động (`py scripts/m10_pick_demo_cases.py --seed 42` → `eval/results/m10_demo_cases_v1/demo_cases.json`):**
  - Bước 1 (`Timeline`): `pipeline_test_v2` → `docs/drafts/figures/m10-timeline.png` (`13.699` candidate, `78` confirmed alerts, `38` incidents, `1.253` ca C3 downgrade trong `2.223` tổng ca hạ chính sách).
  - Bước 2 (`C3 downgrade`, pool `1.171` normal trên `test`): `cand-ad327c0b162f6198:hybrid_bm25_graph:r0` (`productcatalogservice`, `pipeline_test_v2`) → `docs/drafts/figures/m10-alert-c3-downgrade.png`.
  - Bước 3 (`network_delay` BM25 bỏ sót / CTAV xác nhận, pool `2` trên `test`): `cand-fa85e82f02f08574:hybrid_bm25_graph:r0` (`cartservice`, `pipeline_test_v2`) → `docs/drafts/figures/m10-alert-topo-rescue.png`.
  - Bước 4 (`Cascade`, V48 `(b')` pool `3` + V48 `(a')`): `inc-46289ea526eaa3f3` (`pipeline_sens_test_v1`, `ts-basic-service → ts-preserve-service`) kèm ca tách `val` `2023-01-30#009` (`pipeline_val_v2`) → `docs/drafts/figures/m10-incident-cascade.png`.
  - Bước 5 (`Experiment Comparison`): `/compare` (`test` G-test + chuyển đổi `val`) → `docs/drafts/figures/m10-experiment-comparison.png`.
- **Kiểm tra sau sửa cuối (`fa80590`):** `npm.cmd --prefix services/web run check` (exit `0`, `26/26` SSR smoke ok), `py -m mypy packages services` (`Success: no issues found in 43 source files`), `py -m ruff check services scripts/m10_experiment_table.py scripts/m10_pick_demo_cases.py tests` sạch, `py -m pytest tests/ -q` **`253 passed in 30.37s`** (`0` skipped, gồm cả DB thật ClickHouse & PostgreSQL).
- **Danh sách lỗi demo còn lại xếp theo mức độ nghiêm trọng:**
  1. **Thấp (`UX`):** `GET /runs` xếp nhóm `pipeline_%` theo `started_at DESC`, nên sau khi nạp `pipeline_sens_test_v1` thì mở `/` không kèm `?run_id=` sẽ mặc định chọn `pipeline_sens_test_v1` trước `pipeline_test_v2` (đã giảm thiểu bằng băng cảnh báo sensitivity ở đầu trang và truyền `?run_id=` tường minh trong kịch bản). **Đã sửa 2026-11-18 (tổng duyệt M11):** khi kiểm lại phát hiện cách giảm thiểu bằng `?run_id=` không có tác dụng — run chỉ nằm trong state của `App.tsx`, nên mọi link trực tiếp / F5 đều về `pipeline_sens_test_v1` (bước 1 hiện 438 thay vì 78 cảnh báo; băng vàng hiện cả trên `/compare`). Nay `App.tsx` đọc & ghi `?run_id=` trên URL, run mặc định là run pipeline đầu tiên không phải dòng độ nhạy (`resolveRunId` trong `src/lib/runContext.ts`, thêm 6 ca smoke); kiểm trình duyệt thật 5 bước kịch bản đúng run, `0` lỗi console.
  2. **Thấp (`UX`):** Trục X của biểu đồ Timeline chỉ gắn nhãn ngày `dd/MM` ở cột đầu tiên (`bucket 0`) thay vì nhắc lại ở mỗi lần chuyển ngày qua nửa đêm trên các tập nhiều ngày.
  3. **Thẩm mỹ (`Build`):** Bundle JS của Vite (`dist/assets/index-*.js`, `915,84 kB`) vượt mức cảnh báo 500 kB mặc định do chưa tách chunk động theo route.
- **Bổ sung sau đóng mốc (tổng duyệt M11, 2026-11-18, 0 USD API):** hai thẻ giải thích đồ thị cho hội đồng, chữ hiển thị 100% tiếng Anh — *How C1 built this context* (Alert Detail: vùng tìm `d ≤ 2` + phân rã Fusion Score; API thêm `search_scope`, `fusion_weights` vào `GET /alerts/{id}`, test kiểm ba phần cộng lại đúng `score_final` và trọng số khớp `h0_{val,test}_c1_k0.yaml`) và *How the RCA agent localized the root cause* (Incident Detail: 3 bước gom 180 s → nối cạnh gọi → lùi 1 bước, có nút từng bước). Kiểm: `npm run check` (40 ca), `pytest` `254 passed`, `mypy` / `ruff` sạch, trình duyệt thật trên `cand-fa85e82f02f08574` và `inc-46289ea526eaa3f3` / `inc-e12eb79ae09c3712`, `0` lỗi console. Phiếu bầu tính lại trên trình duyệt khớp gốc đã lưu ở 177 / 178 sự cố của 3 run `pipeline_*`; ca còn lại (`inc-dd6ada446605fb93`) là hòa 0,50 mà tác tử phá bằng điểm bất thường trên toàn khoảng sự cố, thẻ ghi rõ "Tie". Số chia sẻ bằng chứng lân cận trong Ch6 sinh từ `scripts/m11_graph_evidence_share.py`. Ảnh Hình 6.2–6.4 cần chụp lại.

---

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Cách giữ `incident_id` theo `rca_final_*` khi dựng prompt tra cache, rồi ánh xạ về `incident_id` của `pipeline_*` khi lưu PostgreSQL | `services/rca_agent/pipeline.py` `_summarize_from_cache` | `incidents.incident_id` là PRIMARY KEY toàn bảng PostgreSQL và nằm trong nội dung prompt; nếu không tách, hoặc đụng khoá chính M9 hoặc cache miss |
| 2 | Cách chuẩn hoá hash báo cáo khi kiểm parity (bỏ `incident_id`, `run_id`, `generated_at`) và sắp xếp tie-break khi trùng `start_ts` | `services/rca_agent/pipeline.py` `normalized_report_hash`, `check_parity` | Xác nhận phần nội dung chẩn đoán giống hệt M9 dù `run_id` khác nhau làm thay đổi mã băm `incident_id` cùng giây |
| 3 | Lưu `content` của sự kiện bằng chứng trong `debug_json` khi ghi `fact_retrieval_trace` | `services/rca_agent/pipeline.py` `_build_loaded_alerts` | Bảng `fact_retrieval_trace` không có cột `content` riêng; M10-B API đọc `content` từ đây |
| 4 | Khớp 100% giữa bảng `ExperimentComparison` (`experiment_table.json`), dịch nhãn tiếng Anh lúc hiển thị và Bảng 5.18 / 5.26 | `scripts/m10_experiment_table.py`, `services/web/src/screens/ExperimentComparison.tsx`, `tests/test_experiment_table.py` | Đảm bảo giao diện tiếng Anh không làm sai lệch bất kỳ số đo hoặc vế kiểm định H0–H5 đã công bố |
| 5 | Luật diễn giải từng bước policy (`policySteps`) và bộ chọn ca demo xác định (`seed=42`) | `services/web/src/lib/util.ts`, `scripts/m10_pick_demo_cases.py`, `eval/results/m10_demo_cases_v1/demo_cases.json` | Bước 2 & 3 của kịch bản demo phải phản ánh đúng cơ chế CTAV (`C3` & `network_delay`) trên dữ liệu thật |
| 6 | Nội dung Chương 6 và email tóm tắt gửi GVHD | `docs/drafts/ch6-demo-platform.md`, `docs/drafts/2026-11-17-mail-gvhd-platform.md` | Cần đúng giọng văn thống nhất một đề tài (`style-guide-luan-van.md`) và trung thực về nhánh A / B của H5 |

---

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Chốt / Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| ~~V47~~ | Vị trí `store.py` khi API cần đọc PostgreSQL | (a) Giữ ở `services/rca_agent/`, API đọc riêng; (b) Chuyển sang `packages/storage/` | **Đã chốt (a) 2026-11-17 (QĐ-045);** đã cập nhật `packages/storage/README.md` | Không |
| ~~V48~~ | Ca minh hoạ cascade cho bước 4 kịch bản demo (`test` không có incident nhiều service) | (a) Dùng ca cascade của `val` + (b) dự phòng; mở lại sau review M10-C: (b') nạp `pipeline_sens_test_v1` kèm (a') giới hạn Ch6; (c) bỏ | **Đã chốt (b') kèm (a') 2026-11-17** (triển khai ở M10-D) | Đã gỡ chặn M10-D |
| ~~V49~~ | Cách chạy `web` khi demo | (a) Service `web` trong `docker-compose.yml` profile `dev`; (b) `npm run dev` ngoài Docker | **Đã chốt (a) 2026-11-17 (QĐ-045)** | Không |

*(Còn mở từ M8/M9, không chặn M10: **V35** chấm 525 dòng context precision trước M12; **V45** đã chốt **(b)** 2026-11-17 cho Ch7/Ch8.)*

---

## 4. Plan cho mốc tiếp theo (M11 — Đánh giá bằng người + phân tích lỗi)

- **Việc (theo thứ tự làm, `docs/prompts/M8-M12-prompts.md` `P5`):**
  1. Viết `scripts/m11_sample_incidents.py`: lấy mẫu ngẫu nhiên 30 incident tập `test` (`rca_final_test_v1`, `seed = 42`) sao cho 15 dòng đầu tự nó là một mẫu ngẫu nhiên hợp lệ; xuất `eval/manual/diagnostic_quality.csv` gồm báo cáo chẩn đoán, bằng chứng trích dẫn và 3 cột chấm điểm theo `02` §4.4 kèm hướng dẫn chấm `<= 1` trang (tách nhãn `root_cause` sang file riêng, không trộn vào bảng chấm mù).
  2. Trình người dùng chấm tối thiểu 15 incident đầu; song song thực hiện việc 3.
  3. Phân tích ca sai trên `test` (chỉ mô tả, không đổi tham số): phân loại 64 FP còn lại và các FN của CTAV (cùng mối liên hệ với vùng tăng cảnh báo của detector từ báo cáo M8) và phân loại toàn bộ ca RCA sai kèm số đếm và `window_id` / `incident_id` minh hoạ cho Chương 7.
  4. Tổng hợp điểm đánh giá chất lượng báo cáo (CI bootstrap + độ đồng thuận nếu có người chấm thứ hai) sau khi người dùng chấm xong.
  5. Tổng duyệt demo lần 1 theo `08` §6, xử lý hoặc cập nhật danh sách lỗi demo còn lại.
- **DoD M11:** Có `eval/manual/diagnostic_quality.csv` đã chấm (`n >= 15`), báo cáo `docs/milestones/M11-danh-gia-nguoi.md` đủ 4 phần và bản nháp `docs/drafts/ch7-phan-tich-ca-sai.md` (§7.3–7.5).
- **Rủi ro đã biết:** Người dùng cần trực tiếp chấm mù `diagnostic_quality.csv` và còn tồn đọng **V35** (`eval/manual/context_precision_test_v1.csv`, 525 dòng, hạn trước M12) cùng 3 khiếm khuyết UX/Build mức thấp ở mục 1.

---

## Phụ lục

- **Sai lệch so với kế hoạch ban đầu:**
  - `ExperimentComparison` cắt từ động sang bảng tĩnh (`experiment_table.json`) sinh bởi `scripts/m10_experiment_table.py` theo `04` §9 ưu tiên 4 (`QĐ-037`, `QĐ-047`).
  - **V47 (a):** Giữ `services/rca_agent/store.py` ở nơi cũ để không chạm mã M9, tách toàn bộ truy vấn chỉ đọc sang `services/api/readers.py` (`QĐ-045`).
  - **V48 (b') kèm (a'):** Do tập `test` chính thức (`pipeline_test_v2`, 78 cảnh báo) có `0` sự cố đa service, bước 4 demo sử dụng `pipeline_sens_test_v1` (`114 / 114` parity với `rca_sens_test_c3rolling_v1`) kèm băng cảnh báo ngoài đăng ký trên UI, đối chiếu cùng giới hạn ca tách `2023-01-30#009` trên `pipeline_val_v2` trong Chương 6 (`QĐ-048`).
  - **Chuyển ngữ 100% tiếng Anh cho UI (`services/web/`):** thực hiện ở tầng hiển thị nhằm đồng bộ giao diện kỹ thuật quốc tế và giữ nguyên `experiment_table.json` trên đĩa để bảo toàn kiểm khớp với Chương 5 (`QĐ-048`).
- **Nguyên liệu cho luận văn:**
  - Nháp Chương 6: `docs/drafts/ch6-demo-platform.md` (§6.1–6.5, Bảng 6.1, Bảng 6.2).
  - 5 ảnh chụp màn hình đã tự kiểm tại `1440x900`: `docs/drafts/figures/m10-{timeline,alert-c3-downgrade,alert-topo-rescue,incident-cascade,experiment-comparison}.png`.
  - Số đo & cấu hình tái lập: `eval/results/pipeline_{val_v2,test_v2,sens_test_v1}/runtime.json`, `eval/results/m10_experiment_table_v2/experiment_table.json`, `eval/results/m10_demo_cases_v1/demo_cases.json`.
  - Thư tóm tắt gửi GVHD: `docs/drafts/2026-11-17-mail-gvhd-platform.md`.
