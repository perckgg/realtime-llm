# Bàn giao Triển khai Platform trên Máy Phụ Ít Dung lượng & Chỉ Có Sẵn Python (`kiri-deploy-handoff`)

> **Ngày cập nhật:** 2026-11-25  
> **Tiền đề phần cứng máy đích:**  
> 1. Ổ cứng còn trống rất ít (**chỉ còn vài GB** — cần ép từng trăm MB).  
> 2. Máy đích **chỉ cài sẵn Python** (và `git`), **chưa có Node.js / npm / Vite** hay bất kỳ công cụ frontend nào để build/chạy UI, và cài Docker Desktop là quá nặng.  
> **Mục tiêu:** Cung cấp lộ trình thêm code để triển khai bằng **[Kiri](https://runkiri.com/)** ([docs.runkiri.com](https://docs.runkiri.com/)) ở mức tiết kiệm đĩa tối đa (**~1,5–1,9 GB trọn gói**, bỏ hẳn nhu cầu Node.js trên máy và bỏ hẳn container `web` lúc chạy), kèm **phương án dự phòng Pure-Python `< 25 MB`** (chỉ dùng đúng Python chuẩn có sẵn nếu ổ cứng còn dưới `2 GB`). Mọi bước đảm bảo **0 lần gọi API (`0 USD`)** và **0 chỉnh sửa vào `eval/results/`**.

---

## 1. Phạm vi & Ràng buộc bất biến (Scope Guard)

Mọi thay đổi thực hiện theo tài liệu này phải tuân thủ nghiêm ngặt `AGENTS.md` và `docs/Final_Thesis_Phase2/06-scope-guard.md`:

1. **Chỉ bổ trợ tầng đóng gói, phục vụ file tĩnh & nạp DB trình diễn**: Không đụng vào logic thuật toán (`detector`, `retrieval`, `judge`, `rca_agent` lõi), không đổi signature của 4 Protocol lõi, không thêm công nghệ bị cấm.
2. **Tuyệt đối không ghi đè `eval/results/`**: Trên máy mới, script nạp dữ liệu chỉ **đọc** từ `eval/results/` để đổ vào ClickHouse + PostgreSQL đang rỗng, không ghi đè hay sinh thêm file trong `eval/results/`.
3. **Ngân sách API = `0 USD`**: Không gọi Gemini API, không cần `GEMINI_API_KEY`.
4. **Không giả định máy đích có `node`/`npm` hay `.venv`**: Mọi script chạy ngoài host trên máy đích phải dùng **100% thư viện chuẩn (stdlib) của Python** (`subprocess`, `urllib.request`, `http.server`, `json`, `pathlib`, `argparse`).

---

## 2. Bài toán dung lượng: Tại sao cần Kiri + Kiến trúc "Ép Từng MB"?

### 2.1 So sánh định lượng từng khoản chiếm đĩa trên máy đích

| Khoản chiếm đĩa | Cách cũ (Docker Desktop + full clone) | **Mức A: Kiri Ultra-Slim (DB sống + API sống)** | **Mức B: Pure-Python Static (khi đĩa `< 2 GB`)** |
|---|---|---|---|
| **Runtime nền** | Docker Desktop GUI/Electron `~2,5 GB` + đĩa ảo `ext4.vhdx` phình `10–25 GB`, RAM rảnh `1,5–4 GB` | **Kiri** (Rust, daemon rảnh `~15 MB` RAM; macOS tự trả RAM & ngủ sau 60s; Linux `0 MB` VM; Windows qua pipe `\\.\pipe\kiri`) | **`0 MB`** (không cần cài Kiri/Docker, chỉ dùng `python` sẵn có) |
| **Mã nguồn `git clone`** | Full clone: **`1,91 GB`** (`.git` `191 MB` + `archive/` `609 MB` + `legacy/` `500 MB` + `docs/` `57 MB` + `eval/` `549 MB`) | **Git Sparse + Shallow Clone:** chỉ **`~560 MB`** (bỏ `archive/`, `legacy/`, `docs/`, `thesis/` và lịch sử commit → **tiết kiệm `1,35 GB`**) | Tải gói build tĩnh `.zip` (`~5 MB` nén → giải nén **`~16 MB`**), không cần clone cả repo |
| **Dữ liệu thô ngoài Git** | `data/Nezha/` **`2,94 GB`** + `gemini.jsonl` `32 MB` | **`0 MB`** (`api` và script nạp DB chỉ đọc `eval/results/` + `data/graph/` đã có trong Git) | **`0 MB`** (đã kết xuất sẵn thành JSON cột nén) |
| **Python `.venv` trên host** | **`546 MB`** (`numpy`, `pandas`, `scikit-learn`, `pyarrow`...) | **`0 MB`** (`scripts/kiri_up.py` chỉ dùng Python stdlib; bước nạp DB chạy trong container `api`) | **`0 MB`** (`scripts/serve_static_spa.py` chỉ dùng `http.server` của Python stdlib) |
| **Node.js + Container UI** | Cài Node trên host (`~400 MB`) hoặc giữ container `web` (`node:22-alpine` + `node_modules` `~360 MB` + cache `~360 MB`) chỉ để phục vụ **`1,02 MB`** file tĩnh! | **`~1 MB` lúc chạy!** Dùng multi-stage build biên dịch `dist/` (`1,02 MB`) nhúng thẳng vào container `api`, rồi tự động `builder prune -af` xóa sạch `node:22-alpine` & `node_modules` ngay sau khi build (**chỉ chạy 3 container, tiết kiệm `~700 MB`**) | **`1,02 MB`** (thư mục `dist/` đã biên dịch sẵn) |
| **Build context `compose build`** | Không có `.dockerignore` → quét **`5,73 GB` × 2 lần** đẩy vào BuildKit | Có `.dockerignore` → build context chỉ còn **`< 2 MB`** | Không cần build |
| **Images + DB (`clickhouse`, `postgres`, `api`)** | ClickHouse Ubuntu + Postgres + API + log nền tự phình `~1,8–2,5 GB` | `clickhouse:24.3-alpine` (tắt `trace_log`/`metric_log` qua `low_disk.xml`) + `postgres:16-alpine` + `api` ≈ **`0,9–1,2 GB`** | **`0 MB`** |
| **TỔNG Ổ CỨNG CẦN TRỐNG** | **`15 – 25+ GB`** | **`~1,6 – 2,0 GB`** *(cần tạm thêm `~350 MB` lúc đang build UI trước khi auto-prune)* | **`< 25 MB`** *(chạy được ngay cả khi ổ cứng chỉ còn vài trăm MB)* |

### 2.2 Khi nào chọn Mức A vs Mức B trên máy kia?
- **Chọn Mức A (Kiri Ultra-Slim — Mặc định khuyến nghị nếu còn trống `>= 2,5 – 3 GB`):** Chạy thật 100% ClickHouse, PostgreSQL, FastAPI 8 endpoint và UI trên Kiri; truy vấn SQL/API trực tiếp sống động, không cần cài Node.js hay `.venv` trên máy.
- **Chọn Mức B (Pure-Python `< 25 MB` — Dự phòng khi ổ cứng báo đỏ `< 2 GB`):** Chỉ dùng đúng trình thông dịch `python` có sẵn trên máy kia để mở toàn bộ 5 màn hình giao diện, đồ thị 56 service và 3 lượt chạy từ gói snapshot tĩnh.

---

## 3. Năm điểm nghẽn kỹ thuật đã phát hiện khi rà repo (phải xử lý bằng code)

1. **Máy đích không có Node.js, còn `infra/Dockerfile.web` đang giữ nguyên cả `node:22-alpine` + `node_modules` lúc chạy:**
   Thư mục kết quả build `services/web/dist` thực chất chỉ nặng **`1,02 MB`**, và trình duyệt ở chế độ `http` chỉ gọi đường dẫn tương đối `/api/*` (`services/web/src/api/client.ts` dòng 69). Trong khi đó `services/api/main.py` đã mount sẵn toàn bộ router ở `/api`. Nếu nhúng thẳng `dist/` vào `api` (multi-stage build + FastAPI `StaticFiles`) rồi xóa stage builder Node đi, máy đích vừa **không cần cài Node.js**, vừa **bỏ hẳn container thứ 4 (`web`)**, tiết kiệm `~700 MB` đĩa và `~150 MB` RAM!
   - *Cạm bẫy route cần lưu ý khi gộp UI vào `api`:* Hiện `services/api/main.py` dòng 99 mount `router` ở cả `/` lẫn `/api`. Nếu mở SPA tại `/incidents` hoặc `/alerts/...` trực tiếp trên `api`, trình duyệt sẽ đụng API `GET /incidents` (lỗi `422 missing run_id`) thay vì nhận `index.html`! Do đó khi bật biến môi trường `STATIC_WEB_DIR=/app/web_dist`, `main.py` chỉ được mount API dưới `/api` (giữ riêng `GET /health` ở gốc cho healthcheck), còn khi `STATIC_WEB_DIR` rỗng thì giữ nguyên hành vi cũ để không ảnh hưởng `tests/test_api.py` và Vite dev proxy.
2. **Thiếu `.dockerignore` ở gốc repo:**
   `build: context: .` đang gom toàn bộ `data/`, `eval/results/`, `archive/`, `legacy/`, `.venv/` (`5,73 GB`) ném vào BuildKit container của Kiri.
3. **ClickHouse thiếu cột CTAV trên volume mới tinh (`Unknown identifier 'raw_verdict'`):**
   `docker-compose.yml` (dòng 22) mới mount `infra/clickhouse/init.sql`, chưa mount `infra/clickhouse/migrations/001_ctav_columns.sql`. Trên máy mới có volume `clickhouse-data` rỗng, bảng `fact_alert_evaluation` thiếu 6 cột CTAV và `fact_retrieval_trace` thiếu `origin`, `graph_distance` → sập lỗi 500. Ngoài ra ClickHouse mặc định bật `trace_log`, `metric_log`, `text_log` tự phình hàng trăm MB mỗi ngày nếu không tắt bằng file config XML.
4. **DB mới rỗng nhưng `eval/results/pipeline_*` đã khóa sẵn trong Git + máy đích không có `.venv`:**
   Trên máy mới, ClickHouse & PostgreSQL rỗng nhưng `eval/results/pipeline_{val_v2,test_v2,sens_test_v1}` đã có sẵn trên đĩa. Cần script `scripts/hydrate_db_from_results.py` chạy **bên trong container `api`** để đổ dữ liệu đã khóa vào 2 DB mà không cần cài thư viện Python lên máy host và không chạm vào `eval/results/`.
5. **Khác biệt về Bind Mount & `python -m http.server` không hỗ trợ React Router SPA:**
   - `postgres` dùng bind mount `./volumes/postgres` dễ lỗi `chmod 0700` trên WSL2 / macOS VM của Kiri → cần đổi sang named volume `postgres-data`.
   - Nếu chạy Mức B bằng `python -m http.server 5173`, người dùng nhấn F5 ở `/timeline` hay `/incidents/...` sẽ bị lỗi `404 File not found` → cần một script `scripts/serve_static_spa.py` (~40 dòng Python stdlib) tự fallback về `index.html` và trả đúng header `Content-Type`.

---

## 4. Các bước thêm code chi tiết (6 bước)

### Bước 1: Tạo `.dockerignore` chặt ở gốc repo
Tạo `.dockerignore` loại bỏ toàn bộ dữ liệu nặng, giữ build context dưới **`2 MB`**:

```dockerignore
# Version control, virtualenvs & caches
.git
.github
.venv
venv
env
__pycache__
*.py[cod]
.mypy_cache
.pytest_cache
.ruff_cache
.codegraph
.vscode
.idea
.obsidian
.agents
.claude

# Heavy datasets, frozen results & host volumes (mounted at runtime, NEVER copied into image)
data/
eval/results/
eval/manual/
volumes/
archive/
legacy/
docs/
thesis/
paper/
tests/

# Frontend local build/deps (rebuilt in multi-stage builder)
services/web/node_modules/
services/web/dist/
services/web/public/static-api/

# Secrets & TeX/archive artifacts
.env
.env.*
*.log
*.pdf
*.zip
```

> **Kiểm tra bắt buộc:** Không ignore `services/web/src/data/experiment_table.json`, `pyproject.toml`, `packages/`, `services/api/`, `services/replayer/`, `eval/*.py`, `eval/harness/`, `eval/configs/`.

---

### Bước 2: Sửa ClickHouse init migration & thêm cấu hình chống phình đĩa `infra/clickhouse/low_disk.xml`

1. Tạo file `infra/clickhouse/low_disk.xml` tắt các bảng system log nền ngốn ổ cứng của ClickHouse:
   ```xml
   <clickhouse>
       <query_log remove="remove"/>
       <trace_log remove="remove"/>
       <text_log remove="remove"/>
       <metric_log remove="remove"/>
       <asynchronous_metric_log remove="remove"/>
       <part_log remove="remove"/>
       <session_log remove="remove"/>
       <processors_profile_log remove="remove"/>
   </clickhouse>
   ```
2. Trong `docker-compose.yml`, cập nhật `volumes` của `clickhouse` để tự nạp cả `init.sql` lẫn `001_ctav_columns.sql` khi khởi tạo volume mới:
   ```yaml
       volumes:
         - clickhouse-data:/var/lib/clickhouse
         - ./infra/clickhouse/init.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
         - ./infra/clickhouse/migrations/001_ctav_columns.sql:/docker-entrypoint-initdb.d/02_ctav_columns.sql:ro
   ```

---

### Bước 3: Gộp phục vụ UI (`dist` `1,02 MB`) vào `services/api/main.py` & tạo `infra/Dockerfile.api.kiri` (Multi-stage, 0 Node lúc chạy)

1. **Cập nhật nhẹ `services/api/main.py`**:
   - Đọc biến môi trường `STATIC_WEB_DIR = os.environ.get("STATIC_WEB_DIR", "").strip()`.
   - Luôn đăng ký `app.include_router(router, prefix="/api")`.
   - Nếu `STATIC_WEB_DIR` **không bật** (mặc định): giữ nguyên `app.include_router(router)` ở gốc `/` để 100% tương thích ngược với `tests/test_api.py` và Vite proxy.
   - Nếu `STATIC_WEB_DIR` **trỏ tới thư mục tồn tại** (chế độ Kiri gộp 1 cổng):
     - Chỉ đăng ký thêm `GET /health` ở gốc `/` (cho healthcheck).
     - Mount `/assets` qua `fastapi.staticfiles.StaticFiles(directory=Path(STATIC_WEB_DIR) / "assets")` (nếu có).
     - Thêm catch-all `GET /{full_path:path}`: nếu tệp con tồn tại trong `STATIC_WEB_DIR` (như `favicon.svg`) thì trả `FileResponse` của tệp đó, ngược lại (mọi route SPA `/overview`, `/timeline`, `/incidents`, `/alerts/...`, `/compare`, `/guide`) trả `FileResponse(Path(STATIC_WEB_DIR) / "index.html")`.

2. **Tạo `infra/Dockerfile.api.kiri` (Multi-stage build)**:
   - **Stage 1 (`FROM node:22-alpine AS web-builder`):** chỉ copy `services/web/package.json`, `services/web/package-lock.json` → `npm ci --no-audit --no-fund` → copy `services/web/` → `VITE_DATA_SOURCE=http npm run build` (sinh `/web/dist` nặng `1,02 MB`).
   - **Stage 2 (`FROM python:3.12-slim`):** cài các package của `Dockerfile.api` cộng `"numpy>=1.26"` (với `--no-cache-dir`), copy `pyproject.toml`, `packages`, `eval`, `services/api`, `services/replayer`, `services/judge`, `services/rca_agent`, `scripts/hydrate_db_from_results.py`, và `COPY --from=web-builder /web/dist /app/web_dist`.
   - Đặt `ENV STATIC_WEB_DIR=/app/web_dist`.
   - *(Mẹo nâng cao tùy chọn: hỗ trợ thêm `ARG PREBUILT_WEB_DIST=""` hoặc nếu đã có sẵn bản build thì không cần kéo `node:22-alpine`; mặc định multi-stage + `builder prune -af` ở Bước 5 là hoàn toàn tự động trên máy không có Node.js).*

---

### Bước 4: Tạo `docker-compose.kiri.yml` (Chỉ chạy 3 container: `clickhouse` Alpine, `postgres` Alpine, `api` kiêm luôn cổng `5173`)

Tạo file `docker-compose.kiri.yml` độc lập (hoặc chạy trực tiếp `-f docker-compose.kiri.yml` để **không kéo và không khởi chạy service `web`**, đồng thời tránh mọi tương kỵ tag `!override` giữa các phiên bản CLI):

- **`clickhouse`**: dùng image `clickhouse/clickhouse-server:24.3-alpine` (nhẹ hơn bản gốc ~`300 MB`), mount `01_init.sql`, `02_ctav_columns.sql` và `low_disk.xml:/etc/clickhouse-server/config.d/low_disk.xml:ro`, `mem_limit: 1536m`, xoay vòng log `max-size: "5m"`, `max-file: "2"`.
- **`postgres`**: dùng `postgres:16-alpine`, named volume `postgres-data:/var/lib/postgresql/data`, `mem_limit: 384m`, xoay vòng log `5m`.
- **`api`** (kiêm luôn giao diện web!): build từ `infra/Dockerfile.api.kiri`, mở cả hai cổng `"5173:8000"` và `"8000:8000"` để mở `http://localhost:5173` giống hệt bản đầy đủ, mount read-only `./eval:/app/eval:ro` và `./data:/app/data:ro`, `STATIC_WEB_DIR: /app/web_dist`, `DEMO_OFFLINE: "1"`, `mem_limit: 512m`.

---

### Bước 5: Viết `scripts/hydrate_db_from_results.py` & trình điều khiển thuần Python `scripts/kiri_up.py`

Vì máy đích **chắc chắn có Python nhưng không có `.venv` hay Node**, viết toàn bộ công cụ điều phối ngoài host bằng **Python stdlib thuần**:

1. **`scripts/hydrate_db_from_results.py`** (chạy *bên trong* container `api`):
   - Đọc trực tiếp các tệp đã khóa trong `/app/eval/results/` để nạp idempotent 3 lượt chạy:
     - `pipeline_val_v2` (`5.677` candidate / `7.716` bằng chứng / `26` incident / `26` report)
     - `pipeline_test_v2` (`13.699` candidate / `19.794` bằng chứng / `38` incident / `38` report)
     - `pipeline_sens_test_v1` (`13.699` candidate / `19.794` bằng chứng / `114` incident / `114` report — qua `pipeline.load_alerts_from_ctav_variant`)
   - Nếu `run_id` đã có trong ClickHouse & PostgreSQL thì `SKIP`, tuyệt đối không ghi ra `/app/eval/results/` (vốn đang mount `:ro` — read-only, càng đảm bảo an toàn 100%!).

2. **`scripts/kiri_up.py`** (chạy *trên máy host* bằng `python scripts/kiri_up.py` hoặc `py scripts/kiri_up.py`, **0 thư viện ngoài**):
   - Các lệnh con:
     - `up` (mặc định):
       1. Tạo `.env` từ `.env.example` nếu chưa có.
       2. Tự dò lệnh Compose của Kiri theo thứ tự: `docker --context kiri compose` → `kiri compose` → `docker compose` (báo lỗi hướng dẫn rõ nếu daemon Kiri chưa bật).
       3. Chạy `<compose> -f docker-compose.kiri.yml up -d --build --wait`.
       4. **Tự động dọn rác tiết kiệm đĩa ngay lập tức** (có cờ `--keep-build-cache` nếu muốn giữ): gọi `builder prune -af` và `image prune -f` trên context `kiri` để xóa ngay image tạm `node:22-alpine` (~`140 MB`) cùng layer `node_modules` (~`200 MB`) vừa dùng trong multi-stage build!
       5. Gọi `<compose> -f docker-compose.kiri.yml exec -T api python scripts/hydrate_db_from_results.py`.
       6. Dùng `urllib.request` kiểm tra `http://127.0.0.1:5173/api/health`, `/api/runs`, `/api/topology?run_id=pipeline_test_v2` và `/` (`index.html`), rồi in URL sẵn sàng: `http://localhost:5173`.
     - `down`: dừng container; `nuke`: `down -v` + `system prune -af` để trả lại toàn bộ dung lượng đĩa khi demo xong.

---

### Bước 6: Thêm phương án dự phòng `< 25 MB` chỉ cần Python (`scripts/serve_static_spa.py` + script đóng gói `.zip`)

Dành cho trường hợp máy đích còn trống **dưới `2 GB`** (không muốn cài cả Kiri hay kéo image ClickHouse):

1. **Viết `scripts/serve_static_spa.py` (~45 dòng, 100% Python stdlib)**:
   - Dựa trên `http.server.ThreadingHTTPServer` + `SimpleHTTPRequestHandler`.
   - Phục vụ thư mục tĩnh (mặc định `services/web/dist` hoặc thư mục truyền qua `--dir`), đăng ký chuẩn MIME `.js`, `.css`, `.json`, `.svg`.
   - Nếu đường dẫn request không khớp tệp thật trên đĩa và không bắt đầu bằng `/static-api/`, tự động trả nội dung `index.html` với mã `200` để mọi route React Router (`/overview`, `/timeline`, `/incidents/...`, `/alerts/...`, `/compare`, `/guide`) hoạt động mượt khi F5 hoặc mở link trực tiếp.
2. **Viết lệnh đóng gói trên máy chính (`scripts/pack_portable_ui.py`)**:
   - Chạy trên máy chính (nơi có sẵn Node.js): gọi `scripts/export_static_pages_api.py` → build `VITE_DATA_SOURCE=static npm run build` → nén `services/web/dist/` + `scripts/serve_static_spa.py` thành 1 tệp duy nhất `portable-demo-ui.zip` (chỉ nặng **`~4–5 MB`**!).
   - Mang tệp `portable-demo-ui.zip` sang máy chỉ có Python (hoặc tải artifact từ GitHub Actions `deploy-pages.yml`), giải nén (`~16 MB`) và chạy đúng 1 lệnh:
     ```bash
     python serve_static_spa.py --port 5173
     ```
     → Lên trọn vẹn giao diện 5 màn hình, không tốn thêm 1 MB thư viện nào!

---

## 5. Quy trình thực chiến trên máy đích (chỉ có Python + ít dung lượng)

### Kịch bản 1 — Chạy full backend + DB sống với Kiri (tổng đĩa `~1,6–2,0 GB`)

```bash
# 1. Cài Kiri (https://runkiri.com) và mở app Kiri để khởi tạo daemon

# 2. Clone siêu gọn (bỏ archive/ 609MB, legacy/ 500MB, docs/ 57MB & lịch sử git -> tiết kiệm 1,35 GB!)
git clone --depth 1 --filter=blob:none --sparse https://github.com/perckgg/realtime-llm.git
cd realtime-llm
git sparse-checkout set packages services eval infra scripts data/splits data/graph

# 3. Dùng ngay Python sẵn có trên máy (KHÔNG tạo .venv, KHÔNG pip install, KHÔNG cần Node.js!)
python scripts/kiri_up.py up
# (Trên Windows nếu lệnh là py: py scripts/kiri_up.py up)

# 4. Mở trình duyệt tại: http://localhost:5173

# 5. Khi demo xong muốn thu hồi sạch ổ cứng:
python scripts/kiri_up.py nuke
```

> **Mẹo thêm cho Windows WSL2 nếu ổ C: quá chật:** Trước khi chạy, tạo file `%USERPROFILE%\.wslconfig` giới hạn RAM (`memory=3GB`, `swap=1GB`). Sau khi chạy `nuke`, có thể gõ `wsl --shutdown` để Windows giải phóng ngay bộ nhớ.

### Kịch bản 2 — Chạy chế độ Siêu Tối Giản `< 25 MB` (0 Kiri, 0 Docker, 0 Node, chỉ Python chuẩn)

```bash
# Giải nén gói portable-demo-ui.zip (~5 MB) đã đóng gói từ máy chính (hoặc GitHub Actions artifact)
python serve_static_spa.py --port 5173
# Mở trình duyệt tại: http://localhost:5173
```

---

## 6. Prompt bàn giao (dán thẳng vào phiên Agent tiếp theo để code)

```text
Đọc `AGENTS.md`, `docs/Final_Thesis_Phase2/06-scope-guard.md` và `docs/prompts/kiri-deploy-handoff.md`.
Triển khai đầy đủ Bước 1 đến Bước 6 trong `docs/prompts/kiri-deploy-handoff.md` cho máy phụ ít dung lượng và chỉ cài sẵn Python (chưa có Node.js/npm):
1. Tạo `.dockerignore` loại `data/`, `eval/results/`, `eval/manual/`, `archive/`, `legacy/`, `.venv/`, `services/web/node_modules/`, `services/web/dist/` (giữ `services/web/src/data/experiment_table.json` và mã nguồn Python).
2. Tạo `infra/clickhouse/low_disk.xml` tắt các bảng system log nền của ClickHouse, và cập nhật `docker-compose.yml` mount cả `01_init.sql` lẫn `02_ctav_columns.sql`.
3. Cập nhật `services/api/main.py` hỗ trợ `STATIC_WEB_DIR` phục vụ SPA + `/assets` mà không xung đột route với `/api/*` (giữ nguyên hành vi cũ khi `STATIC_WEB_DIR` trống để không ảnh hưởng `tests/test_api.py`), và tạo multi-stage `infra/Dockerfile.api.kiri` nhúng bản build UI `1 MB` vào `api` (0 Node lúc chạy).
4. Tạo `docker-compose.kiri.yml` chỉ chạy 3 container nhẹ (`clickhouse:24.3-alpine`, `postgres:16-alpine` với named volume `postgres-data`, `api` mở cả cổng `5173` và `8000` với `./eval` mount `:ro`).
5. Viết `scripts/hydrate_db_from_results.py` (nạp idempotent `pipeline_val_v2`, `pipeline_test_v2`, `pipeline_sens_test_v1` từ `eval/results/`, 0 API call, 0 ghi vào `eval/results/`) và `scripts/kiri_up.py` (100% Python stdlib, tự động `up`, auto-prune stage Node builder để tiết kiệm đĩa, hydrate DB, probe healthcheck và lệnh `nuke`).
6. Viết `scripts/serve_static_spa.py` (100% Python stdlib, fallback `index.html` cho SPA) và `scripts/pack_portable_ui.py` cho phương án dự phòng `< 25 MB` không cần container.
7. Thêm unit test (`tests/test_hydrate_db.py` và test SPA fallback cho `STATIC_WEB_DIR` / `serve_static_spa.py`), chạy kiểm tra `pytest`, `mypy`, `ruff` xanh 100%.
```
