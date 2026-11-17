# M10 — Platform end-to-end + dashboard dữ liệu thật

| | |
|---|---|
| Trạng thái | Đang làm (xong **M10-A**, **M10-B**, **M10-C**, **M10-C.1**; còn M10-D..E) |
| Ngày mở mốc | 2026-11-17 (QĐ-043) |
| Hạn mục tiêu | 2027-01-10 |
| Commit | `45c75c6` (M10-A), `8f2ba70` (M10-B), `55228a7` (M10-C); *(cập nhật tiếp qua M10-C.1..E)* |
| Quyết định liên quan | QĐ-043, QĐ-045, QĐ-046, QĐ-047 (+ bổ sung M10-C.1) |

---

## 1. Kết quả hiện tại

Theo dõi DoD theo 5 mốc con (`docs/prompts/M10-handoff.md` §2):

| Mốc con / DoD | Đạt? | Bằng chứng (số liệu / lệnh tái lập / file) |
|---|---|---|
| **M10-A:** `pipeline.py` + nạp verdict CTAV vào ClickHouse + grouping/propagation/summary (chỉ đọc cache) + PostgreSQL + parity 26/26 (`val`) & 38/38 (`test`) + `runtime.json` | **Đạt** (2026-11-17) | `services/rca_agent/pipeline.py`, `tests/test_pipeline.py`, `eval/results/pipeline_val_v1/runtime.json`, `eval/results/pipeline_test_v1/runtime.json`; 0 lần gọi API, `method fingerprint b0c54fa68ef65535`; QĐ-045 |
| **M10-B:** `services/api` (FastAPI chỉ đọc, 7 endpoint) + `types.ts` trường policy CTAV + `infra/Dockerfile.api` + `tests/test_api.py` | **Đạt** (2026-11-17) | `services/api/{main,readers,schemas}.py`, `services/web/src/api/types.ts`, `infra/Dockerfile.api`, `docker-compose.yml`, `tests/test_api.py`; 7 endpoint `200 OK` trên `pipeline_{val,test}_v1` (cả qua `TestClient` và container `internship1-api-1`); `/alerts?run_id=pipeline_test_v1` (13.699 dòng) đo thực tế `0,561 s`; QĐ-046 |
| **M10-C:** Nối 4 màn hình sang `VITE_DATA_SOURCE=http` + `ExperimentComparison` bảng tĩnh + service `web` trong compose + `npm run check` sạch | **Đạt** (2026-11-17) | `scripts/m10_experiment_table.py`, `services/web/src/data/experiment_table.json` (`52.004` B), `services/web/src/{App.tsx,api/client.ts,screens/*}`, `services/web/scripts/smoke.tsx`, `infra/Dockerfile.web`, `docker-compose.yml`, `tests/test_experiment_table.py`; 4 container (`web`, `api`, `clickhouse`, `postgres`) `healthy`; `http://127.0.0.1:5173/` & `/api/{health,runs,alerts,incidents}` `200 OK`; `npm.cmd run check` (exit 0), `pytest` `248 passed`; QĐ-047 |
| **M10-C.1:** Sửa lỗi sau review M10-C (F1..F10): chuẩn hoá H1 / H5 khớp Ch5, `policySteps()`, `cache_hit` thật (`_v2`), `run_id` & `alert_count` | **Đạt** (2026-11-17) | `eval/results/m10_experiment_table_v2/experiment_table.json` (`52.379` B), `pipeline_val_v2` (26 / 26 parity, E2E `5.764,165 ms`), `pipeline_test_v2` (38 / 38 parity, E2E `4.242,424 ms`), `npm.cmd run check` sạch, `pytest` `249 passed in 28.75s`, probe proxy `:5173` & `docker compose stop/start api` qua *(Chromium tương tác chưa kiểm do người dùng huỷ subagent)*; bổ sung QĐ-047 |
| **M10-D:** `m10_pick_demo_cases.py` + `DEMO_OFFLINE` + tự kiểm trình duyệt thật + ảnh `docs/drafts/figures/m10-*.png` | Chưa làm | — |
| **M10-E:** Hoàn tất `M10-platform.md`, `ch6-demo-platform.md`, bản tóm tắt GVHD, đóng M10 | Chưa làm | — |

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

---

## 2. Cần review gì

| # | Kiểm gì | Ở đâu | Vì sao rủi ro |
|---|---|---|---|
| 1 | Cách giữ `incident_id` theo `rca_final_*` khi dựng prompt tra cache, rồi ánh xạ về `incident_id` của `pipeline_*` khi lưu PostgreSQL | `services/rca_agent/pipeline.py` `_summarize_from_cache` | `incidents.incident_id` là PRIMARY KEY toàn bảng PostgreSQL và nằm trong nội dung prompt; nếu không tách, hoặc đụng khoá chính M9 hoặc cache miss |
| 2 | Cách chuẩn hoá hash báo cáo khi kiểm parity (bỏ `incident_id`, `run_id`, `generated_at`) | `services/rca_agent/pipeline.py` `normalized_report_hash`, `check_parity` | Xác nhận phần nội dung chẩn đoán (`root_cause_service`, `fault_type`, `confidence`, `evidence`, `propagation_path`, `suggested_actions`) giống hệt M9 |
| 3 | Lưu `content` của sự kiện bằng chứng trong `debug_json` khi ghi `fact_retrieval_trace` | `services/rca_agent/pipeline.py` `load_alerts` | Bảng `fact_retrieval_trace` không có cột `content` riêng; M10-B API sẽ đọc `content` từ đây (hoặc từ `retrieval.jsonl`) |

---

## 3. Vấn đề cần bạn giải quyết

| # | Vấn đề | Phương án | Chốt / Khuyến nghị | Chặn mốc sau? |
|---|---|---|---|---|
| ~~V47~~ | Vị trí `store.py` khi API cần đọc PostgreSQL | (a) Giữ ở `services/rca_agent/`, API đọc riêng; (b) Chuyển sang `packages/storage/` | **Đã chốt (a) 2026-11-17 (QĐ-045);** đã cập nhật `packages/storage/README.md` | Không |
| ~~V48~~ | Ca minh hoạ cascade cho bước 4 kịch bản demo (`test` không có incident nhiều service) | (a) Dùng ca cascade của `val` + (b) dự phòng; mở lại sau review M10-C: (b') nạp `pipeline_sens_test_v1` kèm (a') giới hạn Ch6; (c) bỏ | **Đã chốt (b') kèm (a') 2026-11-17** (triển khai ở M10-D) | Đã gỡ chặn M10-D |
| ~~V49~~ | Cách chạy `web` khi demo | (a) Service `web` trong `docker-compose.yml` profile `dev`; (b) `npm run dev` ngoài Docker | **Đã chốt (a) 2026-11-17 (QĐ-045)** | Không |

*(Còn mở từ M8/M9, không chặn M10: **V35** chấm 525 dòng context precision trước M12; **V45** đã chốt **(b)** 2026-11-17 cho Ch7/Ch8.)*

---

## 4. Plan cho mốc tiếp theo

- **Tiếp theo trong M10:** **M10-D** (`scripts/m10_pick_demo_cases.py` trên `pipeline_{val,test}_v2` + triển khai **V48 (b')** nạp `pipeline_sens_test_v1` từ `rca_sens_test_c3rolling_v1` kèm ghi chú rõ *"dòng độ nhạy, không phải kết quả H5"* và **(a')** trong Ch6, kiểm `DEMO_OFFLINE` khi tắt mạng và không dùng `GEMINI_API_KEY`, tự kiểm trình duyệt thật đủ 4 màn hình & chụp ảnh `docs/drafts/figures/m10-*.png`) → **M10-E** (hoàn tất báo cáo này, `ch6-demo-platform.md`, mail GVHD, đóng M10).
- **Ghi chú M10-C.1 (đã đo):** Chạy `pipeline_val_v2` (E2E `5.764,165 ms`, `0` gọi API) và `pipeline_test_v2` (E2E `4.242,424 ms`, `0` gọi API) với `cache_hit` thật từ `judged.jsonl`; giữ nguyên `_v1`. Cả 4 container compose chạy `healthy`.
