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
| **M10-C.1** | Sửa lỗi sau review M10-C (xem §7) | M10-C xong (đã xong 2026-11-17) | Mọi mục mức cao + trung bình ở §7.2 đã sửa, có test; bảng H1 / H5 khớp `ch5-ket-qua-test.md` Bảng 5.18 / 5.26; parity `pipeline_*_v2` 26 / 26, 38 / 38 | Bổ sung QĐ-047 | 2026-11-24 |
| **M10-D** | Demo offline + tự kiểm trình duyệt | M10-C.1 xong và người dùng chốt lại V48 | Kịch bản `08` §6 đi trọn trên dữ liệu thật, lặp lại khi không có mạng / không có `GEMINI_API_KEY`; ảnh chụp đủ | QĐ-048 | 2026-12-22 |
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

**V48 đã chốt lại (2026-11-17):** người dùng chốt **(b') kèm (a')** (§7.3) cho **M10-D** (nạp `pipeline_sens_test_v1` parity 114 / 114 kèm ghi rõ ngoài đăng ký, và nêu ca cascade `val` bị tách đôi như giới hạn trong Ch6).

Còn mở từ trước, không chặn M10: **V45** (cách trình bày H5 không đạt — cần trước chương thảo luận / kết luận), **V35** (chấm 525
dòng context precision, hạn trước M12).

---

## 4. Việc chỉ người dùng làm được trong M10

| Khi | Việc | Ước lượng |
|---|---|---|
| Trước M10-D | Chốt lại V48 theo §7.3 (ca minh hoạ cascade) | 10 phút |
| Sau M10-C.1 | Xem bảng Experiment (dòng H1, H5) và thẻ C3 ở AlertDetail đã sửa | 10 phút |
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

### P4-C1 — M10-C.1 (sửa sau review)

Prompt ở §7.6.

### P4-D — M10-D

```text
Đọc docs/prompts/M8-M12-prompts.md §0, rồi docs/prompts/M10-handoff.md (§2 M10-D, §3 V48, §4, §7). Điều kiện vào: QĐ-047 có,
M10-C.1 xong (§7.5) và tôi đã chốt lại V48 (§7.3). Dùng run pipeline_*_v2 của M10-C.1. Viết scripts/m10_pick_demo_cases.py (seed 42) chọn ca cho bước 2–4 của 08 §6 bằng quy tắc. Làm chế độ
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

---

## 7. M10-C.1 — Sửa lỗi sau review M10-C (2026-11-17)

### 7.1 Kết quả review

Review commit `45c75c6`, `8f2ba70` và `55228a7` (M10-A..C), có mở dashboard thật ở `http://localhost:5173`.

**Đã đúng, giữ nguyên:**
- Kiểm tự động: `pytest` 248 qua, `mypy` sạch, `ruff` chỉ còn E402 cũ ở `scripts/`, `npm run check` qua.
- Parity 26 / 26 và 38 / 38; pipeline dừng trước khi ghi DB nếu lệch.
- API `pipeline_test_v1` trả 13.699 cảnh báo, 78 `TRUE_ALERT`, 14 khớp nhãn (bằng M8).
- Ánh xạ cờ policy khớp `services/judge/policy.py::decide`.
- Chiều cạnh `on_path` trong IncidentDetail đúng; `alert_id` dạng `cand-{window_id}:{strategy}:r0`; ngưỡng detector 0,85.

**Chưa kiểm:** error state khi API tắt (lệnh dừng container `api` bị hệ thống quyền chặn). M10-C.1 phải kiểm phần này.

**Ngoài phạm vi M10-C.1, để người dùng sửa:** dòng H5 của Bảng 5.18 (`docs/drafts/ch5-ket-qua-test.md` ~dòng 261) vẫn ghi
"*Chờ M9*", trong khi §5.9.2 đã kết luận "Không được chấp nhận". Agent M10-C.1 không sửa Ch5; dòng H5 của bảng Experiment
lấy theo Bảng 5.26.

Thứ tự kiểm policy để đối chiếu (`services/judge/policy.py::decide`):
1. `raw_verdict` khác `TRUE_ALERT` ⇒ giữ nguyên;
2. thiếu bằng chứng ⇒ `downgraded_by_evidence_rule`;
3. dưới θ_local ⇒ hạ, chỉ ghi trong `debug`;
4. dưới ngưỡng tier ⇒ `downgraded_by_gating`;
5. không có bằng chứng neo bất thường ⇒ `downgraded_by_anchoring` (C3).

C3 chỉ được xét khi cảnh báo qua cả 4 bước trước.

### 7.2 Danh sách sửa

Mỗi mục: chỗ sai → cách sửa → test phải có. Sửa đúng thứ tự, mức cao trước. Số dòng là lúc review (commit `55228a7`).

#### Mức cao — số liệu luận văn sai so với bản đăng ký

**F1 — Dòng H5 của bảng Experiment** (`scripts/m10_experiment_table.py`, khối `"id": "H5"`, ~dòng 350–385)
- *Sai:* nhãn "Không đạt nhánh A; đạt nhánh B (QĐ-045)"; thêm vế "Nhánh B (bổ trợ): ARR & tóm tắt JSON hợp lệ 100%" được
  đánh dấu đạt. Vế này **không có** trong bản đăng ký `be2b985`, và dùng ARR chung 0,513 thay vì ARR trên cascade. Đồng thời
  bỏ mất hai vế đã đăng ký (CI ΔHit@1, ARR cascade). Trái §5 và trái V45 (b).
- *Sửa:* đúng 4 vế, đúng chữ cột "Vế của H5" ở Bảng 5.26 (`docs/drafts/ch5-ket-qua-test.md` §5.9.2):
  1. Hit@1 ≥ 0,60
  2. Hit@3 ≥ 0,80
  3. Cận dưới CI95 của ΔHit@1 (RCA − baseline) > 0
  4. Alert Reduction ≥ 30% trên sự cố cascade

  Cả 4 có `met: false`. Số đọc từ `eval/results/rca_final_test_v1/rca.json`:
  `by_t_group.180.hit_alert.{level1_hit1, level1_hit1_count, level1_hit1_ci95, level1_hit3, level1_hit3_count,
  level1_hit3_ci95, baseline_hit1_count, d_hit1, d_hit1_ci95, discordant_hit1}`, `cascade_injections` (= 0),
  `reduction.cascade.180.arr` (= null ⇒ detail "không tính được: 0 / 50 lần tiêm lỗi là cascade").
  `status_label` = "Không được chấp nhận (0 / 4 vế)". ARR chung 0,513 [0,362; 0,626] chỉ nằm trong `summary`, kèm chữ
  "tham chiếu, không phải tiêu chí đăng ký". Ý của V45 (b) — "nhánh B chỉ đạt phần gom cảnh báo và sinh báo cáo đúng lược đồ
  (JSON hợp lệ 38 / 38)" — đặt ở trường `note` riêng (thêm vào type, chỉ thêm), **không** là một vế, **không** có chữ
  "đạt nhánh B" ở nhãn.
- *Test* (`tests/test_experiment_table.py`): H5 có đúng 4 vế; mọi `met` là `False`; tên vế khớp 4 dòng của Bảng 5.26;
  `status_label` không chứa "đạt nhánh B".

**F2 — Dòng H1 của bảng Experiment** (khối `"id": "H1"`, ~dòng 303–315)
- *Sai:* `status: "falsified"`, nhãn "Bác bỏ giả thuyết thứ tự đồ thị (M5)"; QĐ-028 và bản đăng ký ghi **H1 giữ một phần**.
  `summary` dùng dấu chấm thập phân (`+.3f`, `.3f`, "p<0.001").
- *Sửa:* `status: "partial"`, `status_label` "Giữ một phần (`val`, M5 — QĐ-028); không chạy lại trên `test`" (đúng hai cột
  của dòng H1 ở Bảng 5.18). Mọi số trong `summary` qua `_fmt_vi`
  (dấu phẩy), kể cả p-value ("p < 0,001"). Thêm màu cho `"partial"` trong `ExperimentComparison.tsx` (hàm chọn màu ~dòng 184);
  bỏ nhánh `"falsified"` nếu không còn dòng nào dùng.
- *Test:* H1 `status == "partial"`; không `summary` / `detail` nào trong JSON sinh ra khớp regex `\d\.\d`.

**Sau F1, F2:** sinh lại bảng vào thư mục **mới** `eval/results/m10_experiment_table_v2/` (không ghi đè `_v1` — §5) và vào
`services/web/src/data/experiment_table.json`. Đổi đường ra mặc định của script sang `_v2`.

#### Mức trung bình

**F3 — Thẻ C3 ở AlertDetail ghi sai** (`services/web/src/screens/AlertDetail.tsx:218`)
- *Sai:* ghi "đạt ngưỡng neo" cho mọi cảnh báo không bị C3 hạ, kể cả khi C3 chưa hề được xét. Trên `test`, 7.717 candidate
  `raw_verdict = FALSE_POSITIVE` và 970 candidate bị luật bằng chứng hạ đều hiện sai (vd. `cand-20cb5635…`). Đây là chỗ
  bước 2 của kịch bản demo chỉ vào.
- *Sửa:* theo thứ tự §7.1:
  - "đạt ngưỡng neo" **chỉ** khi `verdict === "TRUE_ALERT"`;
  - "đã hạ verdict" khi `downgraded_by_anchoring`;
  - còn lại "không áp dụng", kèm bước đã dừng (`raw_verdict` khác `TRUE_ALERT` / luật bằng chứng / θ / C2 gating).

  Dòng "C2 gating" (~224) và "Luật bằng chứng" (~228) dùng cùng logic: bước chưa tới thì "không áp dụng", không ghi
  "không kích hoạt". Viết thành một hàm thuần (vd. `policySteps(alert)`) để Timeline (`Timeline.tsx:297–299`, 489–490) dùng chung.
- *Test:* hàm thuần có 4 ca — raw FP / bị luật bằng chứng / bị C3 hạ / `TRUE_ALERT`. Đưa vào smoke `npm run check` nếu repo
  chưa có test runner; không thêm thư viện.

**F4 — `cache_hit` gán cứng** (`services/rca_agent/pipeline.py:180`, `"cache_hit": 1`)
- *Sai:* `judged.jsonl` có trường `cache_hit` gốc (vd. `False`, `llm_latency_ms` 2.904), nên UI ghi "lấy từ cache" cho lần gọi
  LLM thật ở M8.
- *Sửa:* ghi `int(bool(alert.cache_hit))` từ `judged.jsonl`. Chạy lại pipeline vào run_id **mới** `pipeline_val_v2`,
  `pipeline_test_v2` (không xoá, không ghi đè `_v1`); kiểm lại parity 26 / 26, 38 / 38, 0 lần gọi API. Card "Lý do LLM ra
  verdict" ở AlertDetail (~dòng 142) ghi theo cờ gốc ("judge M8: gọi trực tiếp" / "trúng cache"), kèm nhãn "replay từ
  `judged.jsonl`" cho run `pipeline_*`.
- *Test* (`tests/test_pipeline.py`): hàm build dòng ClickHouse giữ nguyên `cache_hit` của đầu vào (ca `True` và `False`).

**F5 — Mở chi tiết alert có thể lấy nhầm run**
- *Sai:* `services/web/src/api/client.ts:78` `getAlert` không gửi `run_id`; `readers.get_alert_detail` (~dòng 530–544) tự chọn
  `ORDER BY (run_id LIKE 'pipeline_%') DESC`. Sau F4, cùng một window có ở cả `_v1` và `_v2`.
- *Sửa:* `getAlert(alertId, runId?)` gửi `?run_id=` khi có (mock bỏ qua tham số). Link ở `Timeline.tsx:306` và
  `IncidentDetail.tsx:412` thêm `?run_id=<run đang chọn>`; AlertDetail đọc từ query string, thiếu thì lấy run đang chọn trong
  context. API vẫn chấp nhận thiếu `run_id` (giữ hợp đồng), nhưng khi đó chọn run `pipeline_%` có `started_at` mới nhất.
- *Test* (`tests/test_api.py`): cùng `alert_id` với `run_id=pipeline_test_v1` và `pipeline_test_v2` trả đúng `run_id` tương ứng.

**F6 — Hộp chọn run có run không có cảnh báo**
- *Sai:* 4 run `rca_*` (`rca_final_val_v1`, `rca_final_test_v1`, `rca_mock_val_v1`, `rca_sens_test_c3rolling_v1`) có incident ở
  PostgreSQL nhưng 0 dòng ClickHouse ⇒ Timeline hiện 0 cảnh báo nhưng 38 incident.
- *Sửa:* thêm (chỉ thêm) trường `alert_count` vào `RunResponse` (`services/api/schemas.py`) và `Run` (`types.ts`, `fixtures.ts`),
  đếm từ ClickHouse trong `readers.list_runs` bằng một truy vấn `GROUP BY run_id` (không N+1). Hộp chọn run tách hai nhóm
  "Có cảnh báo" / "Chỉ có incident (RCA M9)"; Timeline của run có `alert_count = 0` hiện thông báo rõ thay vì biểu đồ trống.
- *Test* (`tests/test_api.py`): `alert_count` của `pipeline_test_v1` = 13.699, của `rca_final_test_v1` = 0; test hợp đồng khoá
  vẫn qua.

#### Mức thấp — làm nếu còn thời gian, không chặn M10-D

| # | Việc |
|---|---|
| F7 | Trục X Timeline (bucket 10 phút) chỉ có HH:MM trong khi dữ liệu trải 4 ngày ⇒ nhãn nhảy 22:10 → 13:40. Thêm ngày (`dd/MM HH:mm`) ở nhãn đầu mỗi ngày hoặc ở tooltip |
| F8 | Ô "Đúng cảnh báo" (`Timeline.tsx:106`) đếm mọi `TRUE_ALERT` (78, trong đó 64 sai nhãn) ⇒ đổi thành "Xác nhận cảnh báo" |
| F9 | `_verify_markdown_parity` trong `m10_experiment_table.py` chỉ tìm chuỗi số trong Markdown ⇒ thêm so khớp có cấu trúc cho dòng H0–H5 của Bảng 5.18 và cột "Kết luận" của Bảng 5.26 |
| F10 | `readers._judged_details_index` / `_per_window_series_index` (~dòng 214, 235) gắn cứng `ctav_final_*` ⇒ lấy run nguồn từ `config.snapshot.yaml` / `run_registry` của run pipeline. Nếu tốn > 1 giờ thì để lại, ghi vào danh sách lỗi M10-D |
| F11 | Gợi ý cho bước 2 demo: AlertDetail hiện ngưỡng nền `dev` p90 của từng span cạnh giá trị thật, để thấy vì sao C3 hạ. Chỉ làm nếu dữ liệu đã có trong `debug`, không tính lại |

### 7.3 V48 mở lại — chọn ca minh hoạ cascade (người dùng chốt)

Kiểm trên dữ liệu thật 2026-11-17:
- **(a)** Lần tiêm cascade duy nhất của `val` (`2023-01-30#009`) bị tách thành **2 incident một service**
  (`inc-acb48b9f78c56888`, `inc-d04dd76fceb19541`). Incident nhiều service duy nhất của `val` (`inc-c7a08a0f4d7e08a3`) là
  `ambiguous`, không có nhãn. ⇒ (a) **không** minh hoạ được "nhiều alert → một incident → đồ thị chỉ đúng root cause".
- **(b)** `rca_sens_test_c3rolling_v1` có 16 incident nhiều service có nhãn, 3 đúng root cause (vd. `inc-9a91af5471680c09`),
  nhưng cảnh báo của run này **chưa** ở ClickHouse ⇒ IncidentDetail hiện 0 alert.

| Phương án mới | Việc kèm theo | Ghi chú |
|---|---|---|
| (b') Dùng (b), nạp cảnh báo của dòng độ nhạy vào ClickHouse dưới run_id `pipeline_sens_test_v1` (replay, 0 gọi API) | Pipeline thêm chế độ đọc candidate của biến thể C3-trượt; parity 114 / 114 với `rca_sens_test_c3rolling_v1` | Ngoài bản đăng ký: màn hình và Ch6 phải ghi rõ "dòng độ nhạy, không phải kết quả H5" |
| (a') Dùng (a), trình bày như ca **thất bại** (lần tiêm cascade bị tách đôi) | Không cần code mới | Trung thực, khớp V45 (b); nhưng bước 4 demo không còn là ca thành công |
| (c) Bỏ bước 4, nói giới hạn | Không | Như §3 |

Khuyến nghị: **(b')** cho demo, kèm (a') làm một câu về giới hạn trong Ch6. **M10-C.1 không làm (b')**; chỉ làm sau khi người
dùng chốt, trong M10-D.

### 7.4 Ràng buộc riêng của M10-C.1

- §5 áp nguyên: 0 USD API; không ghi đè `eval/results/` (dùng `_v2`); không sửa `eval/configs/rca_final*.yaml`; không sửa mục
  đăng ký H0–H5; không sửa `docs/drafts/ch5-ket-qua-test.md` (bảng thực nghiệm phải khớp **nó**, không phải ngược lại).
- Run `pipeline_*_v1` giữ nguyên trong ClickHouse / PostgreSQL (không xoá, không `ALTER ... UPDATE`).
- Chỉ thêm trường vào `types.ts` / `schemas.py`; không đổi tên hay xoá trường cũ.
- Không thêm thư viện npm / pip. Python chạy bằng `py`; trên Windows dùng `npm.cmd` nếu `npm` bị execution policy chặn.
- Không `git stash` / `checkout` / `reset` file của người khác; không add file bẩn sẵn (V4–V6); không push.
- Ghi vào `docs/experiment-log.md` một đoạn **"QĐ-047 — bổ sung (M10-C.1)"** ngay sau QĐ-047: liệt kê F1..F6 (+ mục thấp đã
  làm), số parity `_v2`, và câu "nội dung QĐ-047 gốc không sửa". Không dùng số QĐ mới.

### 7.5 DoD M10-C.1

1. F1–F6 sửa xong, mỗi mục có test như §7.2.
2. Dòng H1, H5 trong `services/web/src/data/experiment_table.json` khớp Bảng 5.18 / 5.26 của `ch5-ket-qua-test.md`.
3. `pipeline_val_v2` 26 / 26, `pipeline_test_v2` 38 / 38, 0 lần gọi API, `cache_hit` trong ClickHouse bằng `judged.jsonl`.
4. Kiểm trên trình duyệt thật (`docker compose --profile dev up -d --build api web`):
   - AlertDetail của một candidate raw FP (vd. `cand-20cb5635…`) ⇒ thẻ C3 ghi "không áp dụng";
   - một cảnh báo bị C3 hạ ⇒ "đã hạ verdict";
   - bảng Experiment, dòng H5 có 4 vế "Không đạt"; dòng H1 "Giữ một phần";
   - hộp chọn run tách hai nhóm;
   - **error state:** `docker compose stop api`, tải lại 4 màn hình, xem thông báo lỗi, rồi `docker compose start api`.

   Ghi kết quả từng màn hình; cái gì không mở được thì ghi "chưa kiểm".
5. `py -m pytest tests/ -q`, `py -m mypy packages services`, `py -m ruff check .` (chỉ E402 cũ), `npm run check` đều sạch.
6. Cập nhật `docs/CURRENT-MILESTONE.md` (dòng M10-C.1 → đạt, ghi chú bàn giao) và bổ sung mục M10-C.1 vào
   `docs/milestones/M10-platform.md`.

### 7.6 Prompt P4-C1 (dán vào phiên mới — Antigravity hoặc Claude Code)

```text
Làm việc tại C:\Working\Internship1. Đọc docs/prompts/M8-M12-prompts.md §0, rồi docs/prompts/M10-handoff.md §5 và toàn bộ §7.
Làm M10-C.1: sửa F1..F6 trong §7.2 theo đúng thứ tự (mức cao trước), mỗi mục kèm test như mục "Test". Mức thấp F7..F11 chỉ
làm khi F1..F6 đã xong và kiểm sạch.
Docker đang bật (kiểm bằng docker ps; nếu tắt: docker compose --profile dev up -d).
Quy tắc cứng: 0 lần gọi API LLM (cache miss = lỗi, dừng); không ghi đè eval/results/ (bảng mới vào m10_experiment_table_v2,
pipeline mới vào pipeline_val_v2 / pipeline_test_v2); không xoá hay sửa run _v1 trong DB; không sửa
docs/drafts/ch5-ket-qua-test.md, eval/configs/rca_final*.yaml, hay mục đăng ký H0–H5 trong docs/experiment-log.md; chỉ thêm
trường vào types.ts / schemas.py; không thêm thư viện; chạy Python bằng py.
Bảng H1 / H5 phải khớp ch5-ket-qua-test.md Bảng 5.18 / 5.26. Nếu §7.2 mâu thuẫn với Ch5 thì theo Ch5 và báo lại.
Không làm V48 (§7.3) — để người dùng chốt.
Kiểm theo §7.5, gồm mở trình duyệt thật và kiểm error state bằng docker compose stop api / start api.
Ghi "QĐ-047 — bổ sung (M10-C.1)" vào docs/experiment-log.md; cập nhật CURRENT-MILESTONE.md và M10-platform.md.
Commit được khi mọi lệnh kiểm sạch, chỉ add file mình sửa; không push.
Cuối phiên báo: từng mục F đã sửa (file:dòng), số parity _v2, kết quả 4 lệnh kiểm, kết quả kiểm trình duyệt, cái gì chưa kiểm.
```
