# Bàn giao M10 — Platform end-to-end + dashboard dữ liệu thật

> Viết 2026-11-17, ngay sau khi đóng M9 (QĐ-043). Phiên viết file này chỉ đọc repo, kiểm DB và soạn tài liệu: chưa viết code
> M10, 0 lần gọi API. Đây là bản chi tiết hoá prompt P4 (`docs/prompts/M8-M12-prompts.md`) thành 5 mốc con M10-A..E, mỗi
> mốc con có cổng chặn riêng, và một prompt dán được vào phiên mới.
> Quy tắc chung vẫn là §0 của `M8-M12-prompts.md` (bất biến, ngân sách, vùng file, đóng việc).

---

## 1. Trạng thái lúc bàn giao (đã kiểm 2026-11-17)

| Hạng mục | Trạng thái thực tế | Hệ quả cho M10 |
|---|---|---|
| Docker | `clickhouse`, `postgres` đang chạy (healthy) | Không cần dựng lại volume |
| PostgreSQL | 4 run RCA: `rca_final_val_v1` 26 incident, `rca_final_test_v1` 38, `rca_mock_val_v1` 26, `rca_sens_test_c3rolling_v1` 114; mỗi run có số báo cáo chẩn đoán bằng số incident | API đọc được incident / báo cáo ngay |
| ClickHouse `fact_alert_evaluation` | **Chỉ có 3 run smoke** (`m1-smoke` 50, `m2-clickhouse-smoke` 300, `week2-smoke` 50). **Chưa có** verdict CTAV của `val` / `test` | M10-A phải nạp verdict CTAV vào ClickHouse; nếu không, Timeline và AlertDetail không có dữ liệu thật |
| Verdict CTAV | Ở file: `eval/results/ctav_final_val_v1/judged.jsonl` (5.677 candidate → 80 cảnh báo), `ctav_final_test_v1/judged.jsonl` (13.699 candidate → 78 cảnh báo). Mỗi dòng đã có `raw_verdict`, `routing_tier`, `evidence_origin`, `threshold_applied`, `downgraded_by_gating`, `downgraded_by_anchoring` | Đủ trường để hiện "lý do policy (θ, C3)"; migration `001` của ClickHouse đã có các cột này |
| Văn bản bằng chứng | `evidence_run` của RCA: `h0_val_c1_k0_v1` / `h0_test_c1_k0_v1` (`retrieval.jsonl`) | Nạp vào `fact_retrieval_trace` cùng lúc với verdict |
| RCA Agent | `services/rca_agent/{grouping,propagation,summarizer,store}.py`, harness `eval/harness/rca.py`; **chưa có `pipeline.py`** | Pipeline gọi lại đúng các hàm này, không viết lại |
| `services/api` | Chỉ có `README.md`, `__init__.py`. FastAPI 0.141.1, uvicorn, httpx đã có trong `.venv` (`pyproject.toml`) | Viết từ đầu |
| `services/web` | MVP 4 màn hình chạy trên fixture (QĐ-007); `src/api/client.ts` đã có `httpSource` cho đúng 7 endpoint của `01` §6.6, chuyển bằng `VITE_DATA_SOURCE=http`; Vite proxy `/api` → `http://localhost:8000`; Node v24.15.0, `node_modules` có sẵn; không có URL ngoài trong `index.html` / `src` | Nối dữ liệu thật chủ yếu là việc API, ít sửa màn hình |
| `types.ts` | `Alert` **thiếu** các trường policy CTAV (`raw_verdict`, `routing_tier`, `evidence_origin`, `threshold_applied`, `downgraded_by_gating`, `downgraded_by_anchoring`); chỉ có `downgraded_by_evidence_rule` | Thêm trường (chỉ thêm, không đổi trường cũ) — QĐ-046 |
| `docker-compose.yml` | Service `api`, `web` còn comment | M10-B / M10-C bật lên trong profile `dev` |
| `docs/drafts/figures/` | Chưa tồn tại | M10-D tạo |

**Dữ liệu demo yếu (đã biết từ M9):** trên `test`, 38 incident đều chỉ có một service, không có lần tiêm lỗi cascade nào
(H5 không được chấp nhận). Bước 4 của kịch bản demo `08` §6 ("cascade → một incident → đồ thị chỉ đúng root cause") không
có ca minh hoạ trên `test` — xem V48.

---

## 2. Năm mốc con

| Mốc con | Tên | Bắt đầu khi | Cổng chặn để sang mốc con sau | QĐ | Hạn đề xuất |
|---|---|---|---|---|---|
| **M10-A** | Pipeline + nạp dữ liệu thật + parity | Ngay | Parity 26 / 26 (`val`) và 38 / 38 (`test`), 0 lần gọi API, 0 cache miss | QĐ-045 | 2026-11-24 |
| **M10-B** | API FastAPI chỉ đọc | M10-A nạp xong ClickHouse `val` (A1) | 7 endpoint trả 200 trên run `val` và `test` thật; test hợp đồng với `types.ts` qua | QĐ-046 | 2026-12-01 |
| **M10-C** | Dashboard nối dữ liệu thật | M10-B xong | 4 màn hình chạy trên `VITE_DATA_SOURCE=http`; loading / empty / error state; `npm run check` sạch | QĐ-047 | 2026-12-12 |
| **M10-D** | Demo offline + tự kiểm trình duyệt | M10-C xong | Kịch bản `08` §6 đi trọn trên dữ liệu thật, lặp lại khi không có mạng / không có `GEMINI_API_KEY`; ảnh chụp đủ | QĐ-048 | 2026-12-22 |
| **M10-E** | Báo cáo + Ch6 + đóng mốc | M10-D xong | Báo cáo 4 phần; người dùng đã xem | QĐ-049 | 2026-12-29 (dư 12 ngày tới hạn 2027-01-10) |

Song song được: script bảng tĩnh `ExperimentComparison` (C3) chỉ đọc `eval/results/`, làm được bất cứ lúc nào sau M10-A.
Không chạy hai phiên cùng sửa `services/web/` hoặc `services/api/`.

Vấn đề dành riêng cho M10: **V47..V49** (V45, V46 đã dùng ở M9). QĐ-045..049 như bảng trên; số nào không dùng thì bỏ trống.

---

### M10-A — Pipeline + nạp dữ liệu thật + parity (QĐ-045)

**Việc**
1. **A1 Nạp verdict CTAV:** `services/rca_agent/pipeline.py` có bước `load_alerts` đọc `judged.jsonl` của `ctav_final_{val,test}_v1`
   (đây là "replay" của CTAV: verdict đã có từ cache judge, không gọi lại judge) và ghi vào ClickHouse `fact_alert_evaluation`
   (mọi candidate, kể cả `FALSE_POSITIVE` / `UNCERTAIN` — Timeline cần) + `fact_retrieval_trace` (bằng chứng lấy từ
   `evidence_run`). Dùng `packages/storage/clickhouse.py` (`insert_alert_evaluations`, `insert_retrieval_trace`); `run_id` mới
   `pipeline_val_v1`, `pipeline_test_v1` — không ghi đè run cũ.
2. **A2 Điều phối:** CTAV đã nạp → `grouping` (`T_group` 180 s) → `propagation` mức 1 → `summarizer` → PostgreSQL, đọc tham số
   **chỉ** từ `eval/configs/rca_final.yaml` / `rca_final_test.yaml` (dấu vân tay `b0c54fa68ef65535` phải in ra khớp). Summarizer
   chạy chế độ **chỉ đọc cache**: cache miss ⇒ dừng với lỗi, không gọi API. CLI: `py -m services.rca_agent.pipeline --config ...`.
3. **A3 Parity `val`:** so với `rca_final_val_v1` — đúng 26 incident (so theo tập `alert_ids`), đúng thứ hạng service gốc, báo cáo
   JSON giống hệt (so hash). Lệch = bug pipeline, sửa pipeline.
4. **A4 Parity `test`:** như A3 với 38 incident của `rca_final_test_v1` (QĐ-042). Không sửa số đã báo cáo ở M9.
5. **A5 `runtime.json`:** độ trễ end-to-end và từng chặng (nạp, grouping, propagation, summary, ghi DB), token (từ `usage` trong
   cache), cache hit rate. Ghi rõ đây là độ trễ **replay từ cache**, không phải độ trễ gọi LLM trực tiếp.
6. **A6 Test:** `tests/test_pipeline.py` — parity trên `val` (cần Docker), chế độ chỉ đọc cache ném lỗi khi miss.

**DoD M10-A:** parity 26 / 26 và 38 / 38; 0 lần gọi API; `runtime.json` có đủ ba nhóm số; 4 lệnh kiểm của §0.6 sạch.
**Agent tự quyết, ghi vào §3 báo cáo:** V47 (vị trí `store.py`, xem §3 dưới).

### M10-B — API FastAPI chỉ đọc (QĐ-046)

**Việc**
1. `services/api/main.py` (+ module con nếu cần): đúng 7 endpoint `01` §6.6 / `client.ts`: `/health`, `/runs`,
   `/runs/{run_id}/metrics`, `/alerts?run_id=&verdict=`, `/alerts/{alert_id}`, `/incidents?run_id=`, `/incidents/{incident_id}`.
   Chỉ đọc, không logic nghiệp vụ (R-B5), không auth.
2. Nguồn: `run_registry`, `incidents`, `diagnostic_reports`, `diagnostic_rejected` (PostgreSQL); `fact_alert_evaluation`,
   `fact_retrieval_trace` (ClickHouse); `RunMetrics` từ `eval/results/<run>/metrics.json` / `rca.json`; `metric_series` của
   AlertDetail từ dữ liệu Nezha (đọc qua `services/replayer/nezha_source.py`, chỉ cửa sổ của alert).
3. **Hợp đồng:** response model Pydantic khớp `types.ts`. Thêm vào `Alert` các trường policy (chỉ thêm): `raw_verdict`,
   `routing_tier`, `evidence_origin`, `threshold_applied`, `downgraded_by_gating`, `downgraded_by_anchoring`; cập nhật
   `mock/fixtures.ts` cho khớp. Ghi QĐ-046.
4. `/alerts` có `limit` / `offset` tuỳ chọn (`01` ghi "có phân trang"); mặc định trả hết vì mỗi run ≤ 13.699 dòng — đo thời gian
   trả trên `pipeline_test_v1`, nếu > 1 s thì mặc định `limit` = 2.000 và ghi lại.
5. `infra/Dockerfile.api` + bật service `api` trong `docker-compose.yml` profile `dev`.
6. `tests/test_api.py`: `TestClient` trên DB thật (Docker), mỗi endpoint một ca có dữ liệu, một ca 404, một ca run rỗng; test
   hợp đồng: khoá JSON của từng response chứa đủ khoá của interface tương ứng trong `types.ts`.

**DoD M10-B:** 7 endpoint trả 200 trên `pipeline_val_v1` và `pipeline_test_v1`; test hợp đồng qua; `docker compose --profile dev
up -d` dựng được `api`.

### M10-C — Dashboard nối dữ liệu thật (QĐ-047)

**Việc**
1. Timeline, AlertDetail, IncidentDetail chạy trên `VITE_DATA_SOURCE=http`. AlertDetail hiện **nguồn gốc bằng chứng** (tầng 1
   BM25 / tầng 2 topology, `evidence_origin`, độ lệch thời gian, loại) và **lý do policy** (θ = `threshold_applied`, hạ bởi C3
   anchoring / gating, `raw_verdict` → `verdict`).
2. Loading / empty / error state cho cả 4 màn hình (empty: run không có incident; error: API tắt).
3. **ExperimentComparison = bảng tĩnh** (cắt theo `04` §9 ưu tiên 4, QĐ-037): `scripts/m10_experiment_table.py` đọc
   `eval/results/` (bảng H0–H4 `test` của `m8_test_tables_v1`, H5 của `rca_final_test_v1` kèm dòng độ nhạy) → một file JSON tĩnh
   mà màn hình đọc. Có lệnh tái lập; số phải trùng `docs/drafts/ch5-ket-qua-test.md`. Ghi QĐ-047.
4. Bật service `web` trong `docker-compose.yml` (V49) để một lệnh `docker compose --profile dev up -d` dựng đủ.
5. `npm run check` (tsc + smoke SSR) sạch; không thêm thư viện UI.

**DoD M10-C:** 4 màn hình hiện dữ liệu thật của `pipeline_test_v1` / `pipeline_val_v1`; 3 trạng thái hiển thị đúng; `npm run check`
sạch.

### M10-D — Demo offline + tự kiểm trình duyệt (QĐ-048)

**Việc**
1. **Chọn ca demo bằng quy tắc, không chọn tay:** `scripts/m10_pick_demo_cases.py` (seed 42) chọn từ dữ liệu thật: bước 2 — một
   cửa sổ normal mà `raw_verdict = TRUE_ALERT` nhưng bị C3 hạ; bước 3 — một lần tiêm `network_delay` mà BM25 (`h0_test_bm25_v1`)
   bỏ sót, tầng 2 topology tìm được và CTAV xác nhận (nếu không có trên `test` thì tìm trên `val`, ghi rõ); bước 4 — theo V48.
   Mọi ca ghi `window_id` / `alert_id` / `incident_id` vào `docs/drafts/ch6-demo-platform.md`.
2. **Offline:** biến `DEMO_OFFLINE=1` (hoặc không có `GEMINI_API_KEY`) ⇒ mọi chặng chỉ đọc cache / DB; image Docker và
   `node_modules` có sẵn; không tải font / script ngoài.
3. **Tự kiểm bằng trình duyệt thật:** `docker compose --profile dev up -d` → chạy pipeline (replay) → mở 4 màn hình → đi hết 5 bước
   `08` §6. Chụp từng màn hình vào `docs/drafts/figures/m10-*.png`. Lặp lại khi đã ngắt mạng ra ngoài (agent làm phần không có
   `GEMINI_API_KEY` + chặn outbound được; **rút mạng thật là việc của người dùng**, xem §4). Cái gì chưa mở lên xem được thì ghi
   "chưa kiểm".

**DoD M10-D:** kịch bản 5 bước chạy trọn trên dữ liệu thật; một lần chạy không có API key / không mạng ra ngoài; đủ ảnh 4 màn hình.

### M10-E — Báo cáo + Ch6 + đóng mốc (QĐ-049)

**Việc**
1. `docs/milestones/M10-platform.md` đủ 4 phần theo `docs/milestones/README.md` (DoD từng dòng có bằng chứng; bảng độ trễ /
   token / cache hit; parity; danh sách lỗi demo xếp theo mức nghiêm trọng).
2. `docs/drafts/ch6-demo-platform.md` §6.1–6.5 theo sườn (`docs/drafts/suon-bao-cao-gd2.md` dòng 1016–1046): vai trò platform,
   luồng end-to-end, 4 màn hình (kèm ảnh), kịch bản 5 phút (kèm id ca), kiểm thử demo và dự phòng. Markdown, không tạo .docx.
3. Bản tóm tắt 1 trang gửi GVHD (`04` §10: sau M3, M8, M10): `docs/drafts/<ngày>-mail-gvhd-platform.md` — chỉ soạn, người dùng gửi.
4. Cập nhật `CURRENT-MILESTONE.md`, bảng `04` §1, `docs/milestones/README.md`, ghi chú bàn giao; QĐ-049 khi người dùng đã xem.

**DoD M10 (`04` M10):** `docker compose --profile dev up -d` + replay → 4 màn hình hiển thị dữ liệu thật, có loading / empty state;
chạy được khi rút mạng; kịch bản demo `08` §6 chạy trọn. Hạn 2027-01-10.

---

## 3. Vấn đề đã thấy trước (V47..V49)

| # | Vấn đề | Phương án | Khuyến nghị | Chặn gì |
|---|---|---|---|---|
| V47 | `store.py` (ghi PostgreSQL) đang ở `services/rca_agent/` (V42); API cũng cần đọc PostgreSQL | (a) để nguyên, API có module đọc riêng trong `services/api/`; (b) chuyển sang `packages/storage/postgres.py`, sửa import của harness M9 | **(a)**: không đụng code đã cho ra số M9; API chỉ đọc nên không trùng logic ghi. Cập nhật câu "PostgreSQL client chưa có" trong `packages/storage/README.md` | Không — agent tự quyết, ghi §3 báo cáo |
| V48 | Bước 4 kịch bản demo (cascade → một incident → đồ thị chỉ đúng root cause) không có ca nào trên `test` | (a) dùng lần tiêm cascade duy nhất của `val` (`rca_final_val_v1`, ARR 0,667); (b) dùng một incident nhiều service của dòng độ nhạy `rca_sens_test_c3rolling_v1` (ngoài đăng ký, ghi rõ trên màn hình); (c) bỏ bước 4, nói giới hạn | **(a)**, (b) làm dự phòng; cả hai đều phải ghi nguồn trên slide / Ch6 và không trình bày như kết quả H5 | Chặn M10-D bước chọn ca; cần người dùng chốt trước khi tổng duyệt demo |
| V49 | Dashboard chạy thế nào khi demo | (a) service `web` trong compose (build tĩnh + `vite preview` hoặc nginx); (b) chạy `npm run dev` ngoài Docker | **(a)**: DoD là một lệnh `docker compose ... up -d`; image phải pull sẵn trước buổi bảo vệ | Không — agent tự quyết |

Còn mở từ trước, không chặn M10: **V45** (cách trình bày H5 không đạt — cần trước chương thảo luận / kết luận), **V35** (chấm 525
dòng context precision, hạn trước M12).

---

## 4. Việc chỉ người dùng làm được trong M10

| Khi | Việc | Ước lượng |
|---|---|---|
| Trước M10-D | Chốt V48 (ca minh hoạ cascade) | 10 phút |
| Sau M10-C | Mở dashboard, bấm thử 4 màn hình, báo chỗ khó hiểu | 30 phút |
| M10-D | Tự rút mạng thật (tắt Wi-Fi / Zscaler) và chạy lại kịch bản demo | 20 phút |
| M10-E | Đọc `M10-platform.md` §2–§3, đóng mốc; gửi bản tóm tắt cho GVHD | 1 buổi |

---

## 5. Ngân sách và bất biến

- API: **0 USD** (ngân sách M10–M12 = 0, ngưỡng dừng 1 USD — `CURRENT-MILESTONE.md`). Mọi chặng LLM chỉ đọc cache; cache miss là lỗi.
- Không sửa `eval/configs/rca_final*.yaml`, không ghi đè `eval/results/`, không chạy biến thể nào mới trên `test`. M10 chỉ **tái
  lập** M9-B và đo thêm độ trễ.
- Mục đăng ký H0–H5 (`be2b985`) không sửa.
- Vùng file M10 (§0.4): `services/api/`, `services/web/`, `services/rca_agent/pipeline.py`, `docker-compose.yml`,
  `docs/milestones/M10-*`, `docs/drafts/ch6-demo-platform.md`; bổ sung theo bàn giao này: `infra/Dockerfile.api` (+ Dockerfile
  web nếu V49 (a)), `tests/test_pipeline.py`, `tests/test_api.py`, `scripts/m10_*`, `docs/drafts/figures/m10-*`.
- Trước commit: `py -m pytest tests/ -q` (Docker bật, gồm `tests/test_storage.py`), `py -m mypy packages services`,
  `py -m ruff check .`, và `npm run check` trong `services/web/`. Không add file bẩn sẵn (V4–V6), không push.

---

## 6. Prompt cho từng mốc con

Dán nguyên một khối vào một phiên mới mở tại `C:\Working\Internship1`. Mỗi phiên làm **một** mốc con, đóng xong mới mở phiên sau.

### P4-A — M10-A

```text
Đọc docs/prompts/M8-M12-prompts.md §0, rồi docs/prompts/M10-handoff.md (§1, §2 M10-A, §3, §5). Làm M10-A.
Docker đang bật (kiểm bằng docker ps; nếu tắt: docker compose --profile dev up -d).
Viết services/rca_agent/pipeline.py: nạp judged.jsonl của ctav_final_{val,test}_v1 vào ClickHouse (run_id pipeline_val_v1,
pipeline_test_v1, mọi candidate) + bằng chứng từ evidence_run vào fact_retrieval_trace; rồi grouping → propagation mức 1 →
summarizer chỉ đọc cache → PostgreSQL. Tham số chỉ lấy từ rca_final.yaml / rca_final_test.yaml; in dấu vân tay phương pháp.
Dựng và debug trên val tới khi parity 26/26 với rca_final_val_v1 (tập alert_ids, thứ hạng service gốc, hash báo cáo JSON),
rồi chạy test và kiểm parity 38/38 với rca_final_test_v1. Lệch là bug pipeline: sửa pipeline, không sửa số M9.
0 lần gọi API; cache miss = lỗi. Ghi runtime.json (độ trễ E2E và từng chặng, token, cache hit). Viết tests/test_pipeline.py.
Ghi QĐ-045 (kèm V47 agent tự quyết). Bắt đầu bản nháp docs/milestones/M10-platform.md (phần M10-A).
Cuối phiên: số parity, bảng runtime, cái gì chưa kiểm.
```

### P4-B — M10-B

```text
Đọc docs/prompts/M8-M12-prompts.md §0, rồi docs/prompts/M10-handoff.md (§2 M10-B, §5). Điều kiện vào: QĐ-045 có và parity
M10-A đạt (pipeline_val_v1, pipeline_test_v1 có trong ClickHouse và PostgreSQL). Thiếu thì dừng, báo tôi.
Viết services/api (FastAPI, chỉ đọc, không auth): đúng 7 endpoint của services/web/src/api/client.ts, response model khớp
services/web/src/api/types.ts. Thêm (chỉ thêm) các trường policy CTAV vào Alert trong types.ts + fixtures.ts. /alerts có
limit/offset tuỳ chọn. infra/Dockerfile.api và service api trong docker-compose.yml profile dev. tests/test_api.py trên DB thật
gồm test hợp đồng khoá JSON ⊇ khoá interface. Ghi QĐ-046. Bổ sung phần M10-B vào docs/milestones/M10-platform.md.
```

### P4-C — M10-C

```text
Đọc docs/prompts/M8-M12-prompts.md §0, rồi docs/prompts/M10-handoff.md (§2 M10-C, §3 V49, §5). Điều kiện vào: QĐ-046 có,
API chạy được. Nối Timeline, AlertDetail, IncidentDetail sang VITE_DATA_SOURCE=http: hiện nguồn gốc bằng chứng (tầng, origin,
độ lệch thời gian, loại) và lý do policy (θ, C3 anchoring/gating, raw_verdict → verdict); loading / empty / error state cho cả
4 màn hình. ExperimentComparison = bảng tĩnh từ scripts/m10_experiment_table.py đọc eval/results (số phải trùng
docs/drafts/ch5-ket-qua-test.md). Bật service web trong docker-compose.yml (V49, agent tự quyết). Không thêm thư viện UI.
npm run check sạch. Ghi QĐ-047. Bổ sung phần M10-C vào docs/milestones/M10-platform.md.
```

### P4-D — M10-D

```text
Đọc docs/prompts/M8-M12-prompts.md §0, rồi docs/prompts/M10-handoff.md (§2 M10-D, §3 V48, §4). Điều kiện vào: QĐ-047 có và tôi
đã chốt V48. Viết scripts/m10_pick_demo_cases.py (seed 42) chọn ca cho bước 2–4 của 08 §6 bằng quy tắc. Làm chế độ
DEMO_OFFLINE. Tự kiểm bằng trình duyệt thật: docker compose --profile dev up -d → pipeline replay → 4 màn hình → 5 bước kịch
bản; chụp ảnh vào docs/drafts/figures/m10-*.png; lặp lại khi không có GEMINI_API_KEY và chặn mạng ra ngoài. Cái gì chưa mở lên
xem được thì ghi "chưa kiểm". Ghi QĐ-048. Lập danh sách lỗi demo xếp theo mức nghiêm trọng.
```

### P4-E — M10-E

```text
Đọc docs/prompts/M8-M12-prompts.md §0 (đặc biệt §0.5, §0.6), rồi docs/prompts/M10-handoff.md (§2 M10-E). Hoàn tất
docs/milestones/M10-platform.md đủ 4 phần; viết docs/drafts/ch6-demo-platform.md §6.1–6.5 theo sườn (ảnh, lệnh chạy, bảng độ trễ
/ token, id ca demo, giới hạn dữ liệu demo nhánh B); soạn docs/drafts/<ngày>-mail-gvhd-platform.md. Cập nhật CURRENT-MILESTONE,
04 §1, milestones/README, ghi chú bàn giao. Chưa ghi QĐ-049 / chưa đóng M10 cho tới khi tôi xem báo cáo.
```
