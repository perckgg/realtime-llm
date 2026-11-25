# Bàn giao Triển khai Platform bằng Kiri trên Máy Ít Dung lượng (`kiri-deploy-handoff`)

> **Ngày soạn:** 2026-11-25  
> **Mục tiêu:** Chuyển đổi môi trường dựng 4 container của nền tảng demo (`clickhouse`, `postgres`, `api`, `web`) sang **[Kiri](https://runkiri.com/)** ([docs.runkiri.com](https://docs.runkiri.com/)) để chạy mượt trên máy phụ có ổ cứng hạn chế, không phải cài Docker Desktop nặng nề, và dựng lại trọn vẹn cơ sở dữ liệu ngay sau `git clone` với **0 lần gọi API** (`0 USD`) và **0 chỉnh sửa vào `eval/results/`**.

---

## 1. Phạm vi & Ràng buộc bất biến (Scope Guard)

Trước khi sửa bất kỳ dòng code nào theo tài liệu này, agent thực thi phải giữ nguyên 5 quy tắc của `AGENTS.md` và `docs/Final_Thesis_Phase2/06-scope-guard.md`:

1. **Chỉ bổ trợ tầng đóng gói & nạp DB trình diễn**: Không đụng vào logic thuật toán (`detector`, `retrieval`, `judge`, `rca_agent` lõi), không đổi signature của 4 Protocol lõi, không thêm công nghệ bị cấm (Kubernetes, Redis, vector DB...).
2. **Tuyệt đối không ghi đè `eval/results/`**: Mọi tệp trong `eval/results/` đã khóa cho quyển luận văn. Trên máy mới, script nạp dữ liệu chỉ **đọc** từ `eval/results/` để đổ vào ClickHouse + PostgreSQL đang rỗng, không ghi lại ra `eval/results/`.
3. **Ngân sách API = `0 USD`**: Không gọi Gemini API, không yêu cầu `GEMINI_API_KEY`.

---

## 2. Tại sao cần Kiri thay cho Docker Desktop trên máy ít dung lượng?

### 2.1 Vấn đề của Docker Desktop + hiện trạng repo trên máy phụ

Nếu dựng theo cách cũ bằng Docker Desktop trên máy có SSD nhỏ (ví dụ còn trống `< 15 GB`), hệ thống vướng **4 nguồn ngốn dung lượng lớn**:

| Nguồn ngốn tài nguyên | Hiện trạng nếu dùng Docker Desktop | Với Kiri + bản vá trong handoff này |
|---|---|---|
| **Bộ cài & VM nền** | Bộ cài GUI/Electron/Scout/Extensions ~`2,0–3,0 GB`; đĩa ảo WSL2 `ext4.vhdx` phình một chiều lên `10–25+ GB` và không tự co lại khi xóa image; tiến trình `vmmemWSL` giữ `1,5–4 GB` RAM ngay cả khi rảnh | Bộ cài Kiri (viết bằng Rust) nhẹ, daemon nhàn rỗi chỉ ~`15 MB` RAM; trên **macOS** dùng `Virtualization.framework` có *memory balloon* tự trả RAM và ngủ sau 60s rảnh (thức dậy `~0,15s`); trên **Linux** chạy thẳng `systemd`/cgroups (0 đĩa ảo VM); trên **Windows** nối thẳng WSL2 qua named pipe `\\.\pipe\kiri` không kèm lớp Electron nặng |
| **Build context khi `compose build`** | Repo **chưa có `.dockerignore`**, nên `context: .` quét toàn bộ **`5,73 GB`** (`data/` `2.973 MB`, `archive/` `609 MB`, `eval/` `549 MB`, `.venv/` `546 MB`, `legacy/` `500 MB`, `.git/` `191 MB`, `node_modules/` `160 MB`) đẩy vào BuildKit **2 lần** (`api` + `web`) | Thêm `.dockerignore` ép context build từ **`5.730 MB` xuống `< 2 MB`** (giảm `99,96%`, tránh phình đĩa ảo BuildKit của Kiri) |
| **Dữ liệu thô ngoài Git** | Tưởng phải chép cả `data/Nezha/` (`2,94 GB`) + `data/llm_cache/gemini.jsonl` (`32,2 MB`) sang máy mới | **Không cần chép `data/Nezha/` (`0 MB`)** và **không bắt buộc chép `gemini.jsonl`** để chạy demo, vì toàn bộ kết quả 3 lượt chạy (`pipeline_val_v2`, `pipeline_test_v2`, `pipeline_sens_test_v1`) cùng `judged.jsonl`, `per_window.csv`, `retrieval.jsonl` và `data/graph/service_graph.json` **đã nằm sẵn trong Git** |
| **Môi trường host (`.venv` + `node_modules`)** | Cài Python `.venv` (`546 MB`) + Node `node_modules` (`160 MB`) trên máy host chỉ để chạy lệnh nạp DB | Chạy script nạp DB **ngay bên trong container `api`** (`python:3.12-slim` đã có sẵn `clickhouse-connect`, `psycopg`, `pydantic`, `pyyaml`, chỉ thêm `numpy`) → **tiết kiệm thêm `~700 MB` trên ổ cứng máy chủ** |

**Tổng dung lượng thực tế sau tối ưu với Kiri:** chỉ khoảng **`2,2–3,0 GB`** trọn gói cho cả 4 image (`clickhouse:24.3`, `postgres:16-alpine`, `api`, `web`) + toàn bộ dữ liệu ClickHouse/PostgreSQL của 3 lượt chạy.

> **Lưu ý phương án 0 Container (dự phòng cực hạn `< 100 MB`):** Nếu máy chỉ cần mở giao diện trình diễn 5 màn hình mà không cần gõ truy vấn SQL trực tiếp vào ClickHouse/PostgreSQL, repo đã có sẵn chế độ tĩnh `VITE_DATA_SOURCE=static` (`scripts/export_static_pages_api.py`, ~`25 MB`) chạy thẳng trên trình duyệt không cần Kiri hay Docker. Dùng Kiri khi cần **chạy thật đầy đủ 4 service backend + DB có healthcheck và kiểm thử API sống**.

---

## 3. Phân tích mức độ tương thích Kiri ↔ Docker với repo hiện tại

Kiri hiện thực trực tiếp **Docker Engine API** và tự đăng ký Docker context tên `kiri` (macOS: `~/.kiri/run/docker.sock`, Linux: `/run/kiri/docker.sock`, Windows: `\\.\pipe\kiri`). Do đó:

### 3.1 Những thành phần tương thích 100% (giữ nguyên, không sửa)
- `infra/Dockerfile.api` (`python:3.12-slim`) và `infra/Dockerfile.web` (`node:22-alpine`) build qua BuildKit của Kiri không cần đổi cú pháp.
- DNS nội bộ giữa các container (`CLICKHOUSE_HOST=clickhouse`, `POSTGRES_HOST=postgres`, `VITE_API_TARGET=http://api:8000`).
- Chuỗi `healthcheck` + `depends_on: { condition: service_healthy }` từ ClickHouse/PostgreSQL → FastAPI → React/Vite.
- Cổng ánh xạ về máy chủ (`8123`, `9004:9000`, `5432`, `8000`, `5173`) cộng thêm tên miền cục bộ tự động `<service>.<project>.kiri.localhost` của Kiri.

### 3.2 Bốn điểm nghẽn thực tế trên máy mới / Kiri cần thêm code xử lý

1. **Điểm nghẽn 1 — Chưa có `.dockerignore` (nguy cơ tràn đĩa khi build trên Kiri):**
   Kiri chạy BuildKit trong container (`docker-container` driver). Không có `.dockerignore`, mỗi lần `build` sẽ bơm `5,73 GB` dữ liệu vào ổ đĩa ảo của Kiri (`vm/data.img` hoặc WSL2 `.vhdx`).
2. **Điểm nghẽn 2 — ClickHouse thiếu cột CTAV trên volume mới tinh (`Unknown identifier 'raw_verdict'`):**
   Trong `docker-compose.yml` hiện tại (dòng 22), container `clickhouse` chỉ mount `infra/clickhouse/init.sql`, **chưa mount** `infra/clickhouse/migrations/001_ctav_columns.sql`. Trên máy cũ, migration `001` đã chạy tay từ mốc M1; trên máy Kiri mới với volume `clickhouse-data` rỗng, bảng `fact_alert_evaluation` sẽ thiếu 6 cột CTAV (`raw_verdict`, `routing_tier`, `evidence_origin`, `threshold_applied`, `downgraded_gating`, `downgraded_anchoring`) và `fact_retrieval_trace` thiếu `origin`, `graph_distance`, làm API `/alerts` sập lỗi 500.
3. **Điểm nghẽn 3 — DB khởi tạo rỗng nhưng `eval/results/pipeline_*` đã khóa sẵn:**
   Trên máy mới vừa `git clone`, ClickHouse và PostgreSQL hoàn toàn trống, trong khi thư mục `eval/results/pipeline_{val_v2,test_v2,sens_test_v1}` đã có sẵn trong Git. Nếu gọi lại `services/rca_agent/pipeline.py` với `run_id` cũ sẽ vi phạm quy tắc chống ghi đè `eval/results/` (hoặc đòi hỏi `data/llm_cache/gemini.jsonl` + `.venv` `546 MB` trên host).
4. **Điểm nghẽn 4 — Khác biệt nhỏ về Bind Mount & CLI giữa `docker --context kiri compose` và `kiri compose`:**
   - `postgres` đang dùng bind mount `./volumes/postgres:/var/lib/postgresql/data`. Trên macOS VirtioFS hoặc Windows WSL2 (`/mnt/c/...`), PostgreSQL `chmod 0700` trên thư mục bind mount từ host dễ báo lỗi quyền truy cập hoặc chậm I/O; nên chuyển sang named volume `postgres-data` trong file override cho Kiri (giống cách `clickhouse-data` đã làm ở dòng 21).
   - Mọi service trong `docker-compose.yml` đều khai báo `profiles: ["dev", "full"]` và `api` dùng cú pháp mới `env_file: [{path: .env, required: false}]`. Chạy qua `docker --context kiri compose --profile dev ...` hỗ trợ đầy đủ, nhưng nếu người dùng gõ trực tiếp `kiri compose up -d` mà thiếu `.env` hoặc thiếu `COMPOSE_PROFILES=dev` thì sẽ không lên đủ container.

---

## 4. Các bước thêm code để deploy trên Kiri (5 bước chi tiết)

### Bước 1: Tạo `.dockerignore` ở gốc repo
Tạo file `.dockerignore` tại gốc repo để loại toàn bộ dữ liệu lớn và thư mục ngoài image, chỉ giữ lại đúng các file mà `infra/Dockerfile.api` và `infra/Dockerfile.web` cần `COPY`:

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

# Frontend local build/deps (rebuilt cleanly inside Dockerfile.web)
services/web/node_modules/
services/web/dist/
services/web/public/static-api/

# Secrets & TeX artifacts
.env
.env.*
*.log
*.pdf
```

> **Kiểm tra bắt buộc cho Bước 1:** Không được ignore `services/web/src/data/experiment_table.json` (vì `ExperimentComparison.tsx` đóng gói tĩnh file này lúc `npm run build`), `pyproject.toml`, `packages/`, `services/api/`, `services/replayer/`.

---

### Bước 2: Tự động nạp đủ migration ClickHouse khi khởi tạo volume mới
Cập nhật phần `volumes` của service `clickhouse` trong `docker-compose.yml` để ClickHouse entrypoint chạy tuần tự cả `init.sql` lẫn `001_ctav_columns.sql` theo thứ tự tên file khi volume `clickhouse-data` mới tinh:

```yaml
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - ./infra/clickhouse/init.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
      - ./infra/clickhouse/migrations/001_ctav_columns.sql:/docker-entrypoint-initdb.d/02_ctav_columns.sql:ro
```

*(File `001_ctav_columns.sql` dùng `ALTER TABLE aiops.... ADD COLUMN IF NOT EXISTS ...` nên hoàn toàn an toàn và idempotent).*

---

### Bước 3: Tạo file override `docker-compose.kiri.yml` tối ưu cho máy ít dung lượng & đa hệ điều hành
Tạo file `docker-compose.kiri.yml` (dùng kèm `-f docker-compose.yml -f docker-compose.kiri.yml`, không phá cấu hình gốc):

1. Đổi `postgres` sang named volume `postgres-data:/var/lib/postgresql/data` để dữ liệu nằm hoàn toàn trong filesystem ext4 nội bộ của Kiri (tránh lỗi `chmod`/`chown` trên WSL2 và macOS VM).
2. Giới hạn xoay vòng log container (`max-size: "10m"`, `max-file: "2"`) để log của ClickHouse/Uvicorn không âm thầm ăn mòn ổ cứng.
3. Đặt trần RAM mềm hợp lý (`mem_limit`: ClickHouse `2g`, Postgres `512m`, API `512m`, Web `256m` — tổng `< 3,5 GB`) phù hợp máy phụ.

```yaml
services:
  clickhouse:
    mem_limit: 2g
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "2" }

  postgres:
    mem_limit: 512m
    volumes: !override
      - postgres-data:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "2" }

  api:
    mem_limit: 512m
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "2" }

  web:
    mem_limit: 256m
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "2" }

volumes:
  postgres-data:
```

> **Lưu ý kỹ thuật:** Kiểm tra tag `!override` với phiên bản `docker compose` / `kiri compose` thực tế trên máy đích; nếu `kiri compose` bản riêng chưa hỗ trợ `!override`, có thể chuyển thẳng `./volumes/postgres` sang named volume `postgres-data` ngay trong `docker-compose.yml` (vì PostgreSQL trên Windows Docker Desktop cũng chạy tốt hơn với named volume).

---

### Bước 4: Viết `scripts/hydrate_db_from_results.py` & mở rộng nhẹ `infra/Dockerfile.api`
Mục tiêu: Nạp lại nguyên vẹn 3 lượt chạy demo chính thức vào ClickHouse + PostgreSQL từ các tệp đã có sẵn trong `eval/results/` **mà không cần `.venv` trên host, không cần `data/Nezha/`, không cần `data/llm_cache/gemini.jsonl` và không ghi bất kỳ file nào vào `eval/results/`**.

1. **Cập nhật `infra/Dockerfile.api`**:
   - Thêm `"numpy>=1.26"` vào `pip install` (cần cho `eval.harness.ctav` khi tái dựng biến thể `c3_rolling_baseline` của `pipeline_sens_test_v1`).
   - Copy thêm các module đọc/ghi cần thiết:
     ```dockerfile
     COPY eval ./eval
     COPY services/rca_agent/__init__.py services/rca_agent/store.py services/rca_agent/pipeline.py services/rca_agent/grouping.py services/rca_agent/propagation.py services/rca_agent/summarizer.py ./services/rca_agent/
     COPY services/judge ./services/judge
     COPY scripts/hydrate_db_from_results.py ./scripts/hydrate_db_from_results.py
     ```
     *(Lưu ý: như ở Bước 1, `.dockerignore` chỉ loại `eval/results/` và `eval/manual/` — hai thư mục này đã được mount read-only qua `./eval:/app/eval:ro` lúc chạy — trong khi giữ lại mã nguồn nhẹ `eval/*.py`, `eval/harness/`, `eval/configs/`).*

2. **Viết `scripts/hydrate_db_from_results.py`**:
   - Hỗ trợ mặc định 3 lượt chạy:
     - `pipeline_val_v2`: gọi `pipeline.load_alerts("ctav_final_val_v1", "h0_val_c1_k0_v1", "pipeline_val_v2")` + đọc `eval/results/pipeline_val_v2/{config.snapshot.yaml,git_commit.txt,incidents.jsonl,reports.jsonl,rejected.jsonl,runtime.json}`.
     - `pipeline_test_v2`: gọi `pipeline.load_alerts("ctav_final_test_v1", "h0_test_c1_k0_v1", "pipeline_test_v2")` + đọc `eval/results/pipeline_test_v2/...`.
     - `pipeline_sens_test_v1`: gọi `pipeline.load_alerts_from_ctav_variant({"ctav_config": "eval/configs/ctav_final_test.yaml", "variant": "c3_rolling_baseline"}, "test", "h0_test_c1_k0_v1", "pipeline_sens_test_v1")` + đọc `eval/results/pipeline_sens_test_v1/...`.
   - **Idempotent**: Với mỗi `run_id`, kiểm tra `clickhouse.run_exists(run_id)` và `store.run_exists(conn, run_id)`:
     - Nếu cả hai đã có dữ liệu → in `SKIP <run_id> (already hydrated)` và bỏ qua.
     - Nếu chưa có → ghi `fact_alert_evaluation`, `fact_retrieval_trace` vào ClickHouse và `run_registry`, `incidents`, `diagnostic_reports`, `diagnostic_rejected` vào PostgreSQL, sau đó đối chiếu số dòng khớp tuyệt đối:
       - `pipeline_val_v2`: `5.677` candidate / `7.716` bằng chứng / `26` incident / `26` report.
       - `pipeline_test_v2`: `13.699` candidate / `19.794` bằng chứng / `38` incident / `38` report.
       - `pipeline_sens_test_v1`: `13.699` candidate / `19.794` bằng chứng / `114` incident / `114` report.

---

### Bước 5: Tạo script khởi chạy 1 lệnh cho Kiri (`scripts/kiri_up.ps1` & `scripts/kiri_up.sh`) + Kiểm thử
Tạo hai script mỏng để người dùng trên Windows, macOS hoặc Linux chỉ cần chạy **1 lệnh duy nhất**:

1. **Logic của `scripts/kiri_up.ps1` / `scripts/kiri_up.sh`**:
   - Nếu chưa có `.env`, tự copy `.env.example` sang `.env` và thêm `COMPOSE_PROFILES=dev`, `DEMO_OFFLINE=1`.
   - Phát hiện CLI tự động:
     - Ưu tiên `docker --context kiri compose` nếu máy có `docker` CLI và context `kiri` đã đăng ký (`docker context inspect kiri`).
     - Nếu máy không cài `docker` CLI rời, fallback sang `kiri compose`.
   - Chạy:
     ```bash
     <compose_cmd> -f docker-compose.yml -f docker-compose.kiri.yml --profile dev up -d --build --wait
     ```
   - Nạp dữ liệu idempotent ngay trong container `api`:
     ```bash
     <compose_cmd> -f docker-compose.yml -f docker-compose.kiri.yml --profile dev exec -T api python scripts/hydrate_db_from_results.py
     ```
   - Probe nhanh `http://localhost:8000/health`, `http://localhost:8000/runs`, `http://localhost:5173/` và in hướng dẫn mở dashboard (kèm ghi chú: tuyệt đối không chạy `kiri share web` khi đang diễn tập bảo vệ ngoại tuyến).
2. **Viết test `tests/test_hydrate_db.py`**:
   - Kiểm tra `hydrate_db_from_results.py` chạy idempotent 2 lần liên tiếp không lỗi, số bản ghi khớp `26 / 38 / 114`, và `git status --porcelain eval/results/` hoàn toàn rỗng.

---

## 5. Quy trình thao tác trên máy phụ ít dung lượng (sau khi đã thêm code)

1. **Cài Kiri** từ [runkiri.com](https://runkiri.com/):
   - **Windows 10/11 (WSL2):** tải bộ cài `.msi`, mở Kiri để khởi tạo pipe `\\.\pipe\kiri` và context `kiri`. Giới hạn trần RAM/CPU WSL2 nếu cần qua `%USERPROFILE%\.wslconfig` (`memory=4GB`).
   - **macOS 14+:** `brew install --cask libracoder/kiri/kiri` (hoặc tải `.dmg`), mở Kiri khởi tạo `~/.kiri/run/docker.sock`.
   - **Linux:** cài gói `.deb`/`.rpm`, bật `systemctl enable --now kiri`.
2. **Clone repo (không cần chép `data/Nezha/` hay `.venv`)**:
   ```bash
   git clone https://github.com/perckgg/realtime-llm.git
   cd realtime-llm
   ```
3. **Dựng toàn bộ stack & nạp dữ liệu chỉ với 1 lệnh**:
   - Windows PowerShell: `.\scripts\kiri_up.ps1`
   - macOS / Linux: `bash scripts/kiri_up.sh`
4. **Mở trình duyệt**: `http://localhost:5173` (đủ 5 màn hình, 3 luồng dữ liệu, 8 endpoint sống, `0` kết nối Internet).
5. **Giải phóng dung lượng khi không dùng**:
   - Tắt container giữ dữ liệu: `docker --context kiri compose --profile dev stop` (trên macOS VM của Kiri sẽ tự ngủ sau 60s và thu hồi RAM về ~15 MB).
   - Xóa sạch cả volume khi cần thu hồi đĩa: `docker --context kiri compose -f docker-compose.yml -f docker-compose.kiri.yml --profile dev down -v && docker --context kiri system prune -af`.

---

## 6. Prompt bàn giao (dán thẳng vào phiên Agent tiếp theo để code)

```text
Đọc `AGENTS.md`, `docs/Final_Thesis_Phase2/06-scope-guard.md` và `docs/prompts/kiri-deploy-handoff.md`.
Triển khai đầy đủ Bước 1 đến Bước 5 trong `docs/prompts/kiri-deploy-handoff.md` để hỗ trợ deploy nền tảng demo trên Kiri cho máy ít dung lượng:
1. Tạo `.dockerignore` (nhớ loại `eval/results/` nhưng giữ `eval/*.py`, `eval/harness/`, `eval/configs/` và `services/web/src/data/experiment_table.json`).
2. Cập nhật `docker-compose.yml` mount thêm `001_ctav_columns.sql` vào `/docker-entrypoint-initdb.d/02_ctav_columns.sql:ro`.
3. Tạo `docker-compose.kiri.yml` (hoặc đồng bộ named volume `postgres-data` tương thích cả `docker compose` lẫn `kiri compose`, kèm giới hạn log/RAM).
4. Viết `scripts/hydrate_db_from_results.py` nạp idempotent 3 run (`pipeline_val_v2`, `pipeline_test_v2`, `pipeline_sens_test_v1`) từ `eval/results/` vào ClickHouse + PostgreSQL mà không chạm vào `eval/results/` và không gọi API (`0 USD`), đồng thời cập nhật `infra/Dockerfile.api` để chạy được script này ngay trong container `api`.
5. Tạo `scripts/kiri_up.ps1` và `scripts/kiri_up.sh`, viết `tests/test_hydrate_db.py`, kiểm tra lại bằng `pytest`, `mypy`, `ruff` và test build image thực tế xem dung lượng build context đã giảm xuống `< 5 MB` chưa.
```
