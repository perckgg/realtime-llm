# 07 — Setup Guide

Dựng môi trường và bộ khung repo cho Giai đoạn 2. Làm xong file này là có thể bắt đầu Tuần 1.

Thời gian ước tính: nửa ngày đến một ngày.

---

## 1. Yêu cầu môi trường

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.11+ | 3.12 cũng được |
| Docker + Docker Compose | v2 | `docker compose` không phải `docker-compose` |
| ~~Ollama~~ | — | **Không cần trong GĐ2** (QĐ-013): judge là `gemini-2.5-flash-lite` qua API. Các bước Ollama bên dưới chỉ còn để tham chiếu GĐ1 |
| `GEMINI_API_KEY` | — | Bắt buộc khi chạy judge thật; không cần cho G-port (mock) và demo offline từ cache |
| Git | bất kỳ | |
| RAM | ≥ 16 GB | Profile `dev` cần ~6 GB |
| Ổ đĩa trống | ≥ 20 GB | Nezha + ClickHouse + model |

Kiểm tra nhanh:

```bash
python --version
docker compose version
ollama --version
df -h .
```

Kéo model local trước, mất khá lâu:

```bash
ollama pull llama3.2:3b
ollama run llama3.2:3b "test"   # xác nhận chạy được
```

---

## 2. Dựng bộ khung repo

```bash
mkdir aiops-rca-platform && cd aiops-rca-platform
git init

mkdir -p \
  services/{replayer,detector,retrieval,judge,rca_agent,api,web} \
  packages/{schemas,graph,llm,storage} \
  eval/{harness,configs,results} \
  data/{nezha,splits,llm_cache} \
  infra/{clickhouse,postgres,redpanda} \
  docs \
  scripts \
  tests

# __init__.py cho mọi package Python
find services packages eval -type d -not -path "*/results*" -exec touch {}/__init__.py \;
```

Copy bộ tài liệu vào `docs/`, và `AGENTS.md` vào gốc repo:

```bash
cp /đường/dẫn/docs-gd2/*.md docs/
mv docs/AGENTS.md .
```

---

## 3. `.gitignore`

```gitignore
__pycache__/
*.py[cod]
.venv/
venv/
.env
.mypy_cache/
.pytest_cache/
.ruff_cache/

# Dữ liệu và cache — không commit
data/nezha/
data/llm_cache/
*.parquet

# Splits và results — CÓ commit
!data/splits/
!eval/results/

# Docker volumes
volumes/
```

Hai dòng cuối quan trọng: `data/splits/` và `eval/results/` **phải được commit**, đó là bằng chứng tái lập của luận văn.

---

## 4. `pyproject.toml`

```toml
[project]
name = "aiops-rca-platform"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "numpy>=1.26",
    "pandas>=2.2",
    "scikit-learn>=1.4",       # Isolation Forest
    "rank-bm25>=0.2.2",        # BM25
    "networkx>=3.2",           # service dependency graph
    "clickhouse-connect>=0.7",
    "psycopg[binary]>=3.1",
    "fastapi>=0.110",
    "uvicorn>=0.29",
    "httpx>=0.27",
    "structlog>=24.1",
    "tenacity>=8.2",           # retry có giới hạn
    "pyarrow>=15.0",           # parquet cho rescue features
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "mypy>=1.9",
    "ruff>=0.3",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Chú ý:** danh sách này cố tình không có LangChain, không có vector DB, không có Kafka client. Xem `06-scope-guard.md` §4. Thêm thư viện mới phải hỏi trước.

Cài đặt:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## 5. `.env.example`

```bash
# LLM
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_MODEL=llama3.2:3b
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-lite
LLM_CACHE_DIR=./data/llm_cache

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=aiops
CLICKHOUSE_DB=aiops

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=aiops
POSTGRES_PASSWORD=aiops
POSTGRES_DB=aiops

# Dữ liệu
NEZHA_DATA_DIR=./data/nezha
SPLITS_DIR=./data/splits

# API
API_PORT=8000
LOG_LEVEL=INFO
```

```bash
cp .env.example .env
# điền GEMINI_API_KEY vào .env, KHÔNG commit file này
```

---

## 6. `docker-compose.yml`

```yaml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    profiles: ["dev", "full"]
    ports:
      - "8123:8123"
      - "9000:9000"
    environment:
      CLICKHOUSE_DB: aiops
      CLICKHOUSE_PASSWORD: aiops
    volumes:
      - ./volumes/clickhouse:/var/lib/clickhouse
      - ./infra/clickhouse/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ulimits:
      nofile: { soft: 262144, hard: 262144 }
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
      interval: 10s
      retries: 5

  postgres:
    image: postgres:16-alpine
    profiles: ["dev", "full"]
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: aiops
      POSTGRES_PASSWORD: aiops
      POSTGRES_DB: aiops
    volumes:
      - ./volumes/postgres:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aiops"]
      interval: 10s
      retries: 5

  api:
    build:
      context: .
      dockerfile: infra/Dockerfile.api
    profiles: ["dev", "full"]
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      CLICKHOUSE_HOST: clickhouse
      POSTGRES_HOST: postgres
    depends_on:
      clickhouse: { condition: service_healthy }
      postgres:   { condition: service_healthy }

  redpanda:
    image: redpandadata/redpanda:v24.1.1
    profiles: ["full"]
    command:
      - redpanda start
      - --smp 1
      - --overprovisioned
      - --kafka-addr PLAINTEXT://0.0.0.0:9092
      - --advertise-kafka-addr PLAINTEXT://redpanda:9092
    ports:
      - "9092:9092"

  prometheus:
    image: prom/prometheus:latest
    profiles: ["full"]
    ports: ["9090:9090"]
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro

  grafana:
    image: grafana/grafana:latest
    profiles: ["full"]
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: aiops
```

**Ollama chạy ngoài Docker.** Đưa nó vào compose sẽ tốn thêm vài GB RAM và rắc rối với GPU passthrough. Chạy `ollama serve` trên máy host là đủ.

Lệnh dùng hàng ngày:

```bash
docker compose --profile dev up -d      # thực nghiệm, phát triển
docker compose --profile full up -d     # demo đầy đủ
docker compose --profile dev down       # tắt, giữ dữ liệu
docker compose down -v                  # tắt và xóa sạch volume
```

---

## 7. Khởi tạo database

Chép DDL từ `03-schemas-and-contracts.md` §3 vào `infra/clickhouse/init.sql` và §4 vào `infra/postgres/init.sql`.

Bao ClickHouse DDL bằng:

```sql
CREATE DATABASE IF NOT EXISTS aiops;
USE aiops;
-- ... các CREATE TABLE từ tài liệu 03
```

Kiểm tra sau khi `up`:

```bash
curl "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20aiops"
docker compose exec postgres psql -U aiops -d aiops -c '\dt'
```

Phải thấy `fact_alert_evaluation`, `fact_retrieval_trace` bên ClickHouse và `run_registry`, `incidents`, `diagnostic_reports`, `diagnostic_rejected` bên Postgres.

---

## 8. Đưa code Giai đoạn 1 vào cấu trúc mới

Đây là phần quan trọng nhất của setup, vì bạn đã có code sẵn.

### 8.1 Nguyên tắc: bọc, đừng viết lại

Code GĐ1 đã được kiểm chứng bằng số liệu. Đừng refactor nó. Chỉ **bọc một lớp adapter** để nó khớp với Protocol mới.

```python
# services/detector/isolation_forest.py
from packages.schemas import TelemetryWindow, Detector
from legacy.phase1_detector import Phase1Detector   # code GĐ1, chép nguyên vẹn

class IsolationForestDetector:
    """Adapter bọc quanh detector GĐ1."""
    name = "isolation_forest"

    def __init__(self, threshold: float = 0.85, **kwargs):
        self._impl = Phase1Detector(**kwargs)
        self.threshold = threshold

    def score(self, window: TelemetryWindow) -> float:
        return self._impl.compute_score(window_to_legacy(window))

    def is_candidate(self, window: TelemetryWindow, score: float) -> bool:
        return score >= self.threshold
```

Tạo thư mục `legacy/` chứa code GĐ1 nguyên trạng. Sau khi Tuần 3 tái lập được baseline và mọi thứ ổn định, có thể dần dọn nó — nhưng không phải bây giờ.

### 8.2 Bảng ánh xạ

| Code GĐ1 | Đích ở GĐ2 | Việc cần làm |
|---|---|---|
| Streaming replay + watermark | `services/replayer/nezha_source.py` | Bọc theo `SourceAdapter`, thêm `speed_multiplier` |
| Isolation Forest | `services/detector/isolation_forest.py` | Bọc theo `Detector` |
| BM25 hybrid retrieval | `services/retrieval/bm25_hybrid.py` | Bọc theo `RetrievalStrategy`, **bắt buộc điền `debug`** |
| LLM-as-a-Judge | `services/judge/llm_judge.py` | Bọc theo `Judge` |
| Local-first routing | `packages/llm/router.py` | Chép sang, giữ nguyên logic fallback |
| LLM response cache | `packages/llm/cache.py` | Chép sang, đổi cache key theo `03` §6 |
| Context Rescue heuristic | `services/detector/rescue.py` | **Viết lại** thành công thức có tham số α, β, γ, τ |
| Tiền xử lý metric/log/trace | `packages/schemas/loaders.py` | Chép sang, output ra `TelemetryWindow` |

Chỉ có Context Rescue là phải viết lại. Phần còn lại là bọc.

### 8.3 Ba điểm cần chú ý khi bọc

**`window_id` phải deterministic.** Nếu GĐ1 dùng UUID ngẫu nhiên hoặc số thứ tự, đổi sang `hash(service + start_ts)`. Cần thiết để join kết quả giữa các run.

**`bm25_hybrid` phải điền trường `debug`.** GĐ1 có thể không lưu điểm BM25 và khoảng cách thời gian. Bổ sung ngay lúc bọc — sau này cần để chấm context precision.

**Cache key có thể khác.** Nếu GĐ1 dùng key khác với `sha256(prompt + model + temperature + max_tokens)`, cache cũ sẽ không dùng lại được. Chấp nhận chạy lại một lần, hoặc viết script migrate. Đừng giữ hai định dạng cache song song.

---

## 9. Dữ liệu Nezha

```bash
# đặt dataset vào data/nezha/
ls data/nezha/
```

Viết `scripts/download_nezha.sh` ghi lại nguồn tải và cách giải nén, để người khác reproduce được. Không commit dữ liệu.

---

## 10. Config đầu tiên

`eval/configs/bm25_baseline.yaml` — dùng để tái lập baseline GĐ1 ở Tuần 3:

```yaml
run_id: bm25_baseline_v1
seed: 42
split: dev
n_windows: 300

source:
  type: nezha_replay
  speed_multiplier: 0

detector:
  type: isolation_forest
  threshold: 0.85

rescue:
  enabled: false

retrieval:
  type: bm25_hybrid
  top_k: 6
  max_tokens: 4000
  timeout_ms: 500
  params: {}

judge:
  type: llm
  backend: local_first
  local_model: llama3.2:3b
  fallback_model: gemini-flash-lite
  require_evidence: true
  cache: true

rca:
  enabled: false
```

Giữ `rescue.enabled: false` cho config này. Baseline GĐ1 Phase 4 (Precision 0.32, FPR 0.046) là số liệu **không có** Context Rescue — so sánh phải cùng điều kiện.

---

## 11. Kiểm tra môi trường

Chạy tuần tự, mỗi bước phải pass mới đi tiếp:

```bash
# 1. Python và dependencies
python -c "import pydantic, sklearn, networkx, rank_bm25; print('deps ok')"

# 2. Docker
docker compose --profile dev up -d
docker compose ps          # tất cả phải healthy

# 3. ClickHouse
curl "http://localhost:8123/?query=SELECT%201"

# 4. PostgreSQL
docker compose exec postgres psql -U aiops -d aiops -c 'SELECT 1'

# 5. Ollama
curl http://localhost:11434/api/tags

# 6. Gemini fallback
python -c "
import os, httpx
from dotenv import load_dotenv
load_dotenv()
print('key set:', bool(os.getenv('GEMINI_API_KEY')))
"

# 7. Dữ liệu Nezha
ls -la data/nezha/ | head

# 8. Lint và type check chạy được
ruff check . && mypy packages services --ignore-missing-imports
```

---

## 12. Commit đầu tiên

```bash
git add .
git commit -m "chore: khởi tạo bộ khung repo GĐ2

- Cấu trúc thư mục theo docs/01-architecture-design.md
- Docker Compose profiles dev/full
- DDL ClickHouse + PostgreSQL theo docs/03
- Bộ tài liệu GĐ2 trong docs/
- AGENTS.md cho AI coding agent
- Config baseline đầu tiên"
```

---

## 13. Checklist hoàn tất setup

- [ ] `docker compose --profile dev up -d` chạy, mọi service healthy
- [ ] ClickHouse có đủ bảng theo `03` §3
- [ ] PostgreSQL có đủ bảng theo `03` §4
- [ ] Ollama chạy được `llama3.2:3b`
- [ ] `GEMINI_API_KEY` đã điền trong `.env`, `.env` không bị commit
- [ ] Dữ liệu Nezha nằm trong `data/nezha/`
- [ ] Code GĐ1 đã chép vào `legacy/`
- [ ] `AGENTS.md` ở gốc repo, bộ tài liệu ở `docs/`
- [ ] `docs/CURRENT-MILESTONE.md` đang ở mốc M0 (bản gốc: `CURRENT-WEEK.md` Tuần 1; đổi ở QĐ-014)
- [ ] `ruff` và `mypy` chạy không lỗi
- [ ] Commit đầu tiên đã xong

---

## 14. Trục trặc thường gặp

**ClickHouse không khởi động, log báo lỗi file descriptor.**
Thiếu `ulimits` trong compose. Đã có trong file mẫu ở §6. Nếu vẫn lỗi trên Linux: `sudo sysctl -w fs.file-max=262144`.

**`init.sql` không chạy.**
Script trong `docker-entrypoint-initdb.d` chỉ chạy khi volume rỗng. Đã lỡ khởi động trước đó thì `docker compose down -v` rồi `up` lại.

**Ollama trong container không gọi được từ host, hoặc ngược lại.**
Từ container gọi ra host dùng `host.docker.internal` (macOS/Windows) hoặc `172.17.0.1` (Linux). Đơn giản nhất là chạy eval harness trên host, không trong container.

**Máy chậm khi chạy profile `dev`.**
Tắt `api` và `web` khi chạy thực nghiệm — harness chỉ cần ClickHouse và Postgres:
```bash
docker compose up -d clickhouse postgres
```

**Port 5432 hoặc 8123 đã bị chiếm.**
Đổi cổng phía host trong compose, ví dụ `"15432:5432"`, và cập nhật `.env`.

---

## 15. Xong setup rồi làm gì

Mở `docs/CURRENT-MILESTONE.md`. Việc đầu tiên của M0 (Tuần 1 bản gốc) là `scripts/verify_labels.py` — kiểm tra Nezha có nhãn `root_cause_service` hay không.

Chưa viết code pipeline trong tuần này.
