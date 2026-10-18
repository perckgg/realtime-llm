# 03 — Schema và Hợp đồng Dữ liệu

Mọi model trong tài liệu này nằm ở `packages/schemas/`. **Không service nào được định nghĩa lại** — import từ package chung.

Dùng Pydantic v2. Mọi timestamp là UTC, kiểu `datetime` có timezone.

---

## 1. Model lõi

### 1.1 TelemetryWindow

Đơn vị dữ liệu đi vào pipeline.

```python
class MetricPoint(BaseModel):
    name: str
    value: float
    ts: datetime

class LogEvent(BaseModel):
    ts: datetime
    service: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    message: str
    trace_id: str | None = None
    span_id: str | None = None

class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None
    service: str
    operation: str
    start_ts: datetime
    duration_ms: float
    status_code: int | None = None
    error: bool = False
    exception_message: str | None = None

class TelemetryWindow(BaseModel):
    window_id: str            # duy nhất, ổn định giữa các lần chạy
    service: str
    start_ts: datetime
    end_ts: datetime
    metrics: list[MetricPoint]
    logs: list[LogEvent]
    spans: list[TraceSpan]
    # ground truth, chỉ có khi chạy trên dataset có nhãn
    label: WindowLabel | None = None

class WindowLabel(BaseModel):
    is_fault: bool
    fault_type: str | None       # network_delay | cpu_contention | ...
    root_cause_service: str | None
```

**Quy tắc:** `window_id` phải deterministic — sinh từ `hash(service + start_ts)`, không dùng UUID ngẫu nhiên. Cần thiết để join kết quả giữa các run.

### 1.2 AlertCandidate

```python
class AlertCandidate(BaseModel):
    candidate_id: str
    window_id: str
    service: str
    ts: datetime
    anomaly_score: float
    source: Literal["metric", "rescue"]   # rescue = được promote bởi Rescue Score
    rescue_score: float | None = None
    rescue_components: dict[str, float] | None = None  # lambda_log, phi_topo, delta_time
```

### 1.3 ContextEvent và RetrievalResult

```python
class ContextEvent(BaseModel):
    event_id: str
    modality: Literal["log", "trace", "metric"]
    ts: datetime
    service: str
    content: str                  # dạng text đưa vào prompt
    score: float                  # điểm retrieval
    origin: Literal["local", "graph"] = "local"  # QĐ-011: graph = có được nhờ mở rộng topology
    graph_distance: int | None = None             # d_G(service, s0); None nếu không tới được
    debug: dict[str, Any] = {}    # vì sao được chọn: rank BM25, graph distance, kênh...

class RetrievalBudget(BaseModel):
    top_k: int = 6
    max_tokens: int = 4000
    timeout_ms: int = 500

class RetrievalResult(BaseModel):
    strategy: str
    events: list[ContextEvent]
    latency_ms: float
    token_estimate: int
    truncated: bool = False
    debug: dict[str, Any] = {}
```

**Trường `debug` là bắt buộc phải điền**, không được để rỗng. Nó là dữ liệu để chấm context precision và viết phần phân tích luận văn. Mỗi strategy ghi những gì đặc thù của nó:

| Strategy | `debug` chứa |
|---|---|
| `bm25_hybrid` | `bm25_score`, `time_distance_sec` |
| `temporal` | `window_size_sec` đã chọn, `score_mapping` |
| `cross_modal` | `channel`, `channel_rank`, `fusion_weight` |
| `graph` | `graph_distance`, `decay_applied`, `path` |
| `hybrid_bm25_graph` | `bm25_norm`, `time_sim`, `graph_sim`, `score_final` (nếu weighted) hoặc `bm25_rank`, `graph_rank`, `rrf_score` (nếu rrf) |

### 1.4 JudgedAlert

```python
class JudgedAlert(BaseModel):
    alert_id: str
    candidate_id: str
    window_id: str
    service: str
    ts: datetime
    verdict: Literal["TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"]
    confidence: float             # 0.0 - 1.0
    reasoning: str
    evidence_event_ids: list[str] # tham chiếu ContextEvent
    judge_backend: str            # gemini-2.5-flash-lite | mock (chỉ G-port) — QĐ-013
    llm_latency_ms: float
    cache_hit: bool
    downgraded_by_evidence_rule: bool = False
```

`downgraded_by_evidence_rule` bật khi LLM trả TRUE_ALERT nhưng không nêu evidence → hạ xuống UNCERTAIN. Phải ghi lại để báo cáo tần suất.

**Trường bổ sung cho CTAV (QĐ-011, thêm ở mốc M1):**

```python
    raw_verdict: Literal["TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"]  # trước policy C2/C3
    routing_tier: Literal[1, 2] = 1          # C4: 1 = chỉ BM25, 2 = đã mở rộng topology
    evidence_origin: Literal["local", "graph", "mixed", "none"] = "none"  # nguồn của evidence được trích
    threshold_applied: float | None = None   # θ_local hoặc θ_topo đã áp
    downgraded_by_gating: bool = False       # C2 hạ verdict
    downgraded_by_anchoring: bool = False    # C3 hạ verdict
```

`verdict` là kết quả **sau** policy. Giữ cả `raw_verdict` để ablation H3 không cần gọi lại LLM.

### 1.5 Incident

```python
class Incident(BaseModel):
    incident_id: str
    run_id: str
    alert_ids: list[str]
    services: list[str]
    start_ts: datetime
    end_ts: datetime
    grouping_reason: dict[str, Any]   # temporal_window_sec, graph_edges_used
```

### 1.6 Cột ClickHouse cho CTAV

`fact_alert_evaluation` (§3.1) cần thêm `raw_verdict`, `routing_tier`, `evidence_origin`,
`threshold_applied`, `downgraded_gating`, `downgraded_anchoring`; `fact_retrieval_trace`
(§3.2) cần thêm `origin`, `graph_distance`. Bảng đã có dữ liệu smoke của M0 ⇒ thêm bằng
script `infra/clickhouse/migrations/001_ctav_columns.sql` theo §7, không sửa `init.sql` tại chỗ.

---

## 2. JSON Schema cho Diagnostic Report

Đây là đầu ra cuối cùng của Nhánh B. Schema cố định, được validate tự động.

```python
class SuggestedAction(BaseModel):
    description: str              # mô tả, KHÔNG phải câu lệnh thực thi
    priority: Literal["high", "medium", "low"]

class EvidenceItem(BaseModel):
    event_id: str
    modality: Literal["log", "trace", "metric"]
    service: str
    ts: datetime
    excerpt: str

class DiagnosticReport(BaseModel):
    incident_id: str
    run_id: str
    root_cause_service: str
    fault_type: str               # network_delay | cpu_contention | exception | unknown
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(min_length=1)   # bắt buộc ≥ 1
    propagation_path: list[str]   # danh sách service theo thứ tự lan truyền
    suggested_actions: list[SuggestedAction]
    generated_at: datetime
    llm_backend: str
    schema_version: str = "1.0"
```

### 2.1 Quy tắc validation

- `evidence` rỗng → **không phát hành report**. Ghi vào bảng `diagnostic_rejected` kèm lý do.
- `confidence` ngoài [0, 1] → reject.
- `root_cause_service` không nằm trong service dependency graph → cảnh báo, vẫn ghi nhận nhưng đánh dấu `suspicious=True`.
- `suggested_actions` chứa chuỗi giống câu lệnh shell (bắt đầu bằng `kubectl`, `sudo`, `docker`, `rm`...) → reject. Phạm vi GĐ2 chỉ sinh mô tả, không sinh lệnh thực thi.

### 2.2 Chỉ số JSON valid rate

```text
JSON valid rate = số report pass validation / tổng số lần LLM được gọi để sinh report
```

Mục tiêu ≥ 0.95, nhất quán với GĐ1.

---

## 3. ClickHouse DDL

Nguyên tắc: thiết kế kỹ trước khi code, tránh `ALTER TABLE` liên tục.

### 3.1 fact_alert_evaluation

Bảng chính, một dòng mỗi window mỗi run.

```sql
CREATE TABLE fact_alert_evaluation (
    run_id              LowCardinality(String),
    window_id           String,
    service             LowCardinality(String),
    window_ts           DateTime64(3, 'UTC'),

    anomaly_score       Float32,
    candidate_source    LowCardinality(String),   -- metric | rescue | none
    rescue_score        Nullable(Float32),
    rescue_lambda_log   Nullable(Float32),
    rescue_phi_topo     Nullable(Float32),
    rescue_delta_time   Nullable(Float32),

    retrieval_strategy  LowCardinality(String),
    retrieval_latency_ms Float32,
    context_event_count UInt16,
    context_tokens      UInt32,
    retrieval_truncated UInt8,

    verdict             LowCardinality(String),   -- TRUE_ALERT | FALSE_POSITIVE | UNCERTAIN | NONE
    confidence          Nullable(Float32),
    judge_backend       LowCardinality(String),
    llm_latency_ms      Nullable(Float32),
    cache_hit           UInt8,
    downgraded          UInt8,

    label_is_fault      UInt8,
    label_fault_type    LowCardinality(String),
    label_root_cause    LowCardinality(String),

    created_at          DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (run_id, window_ts, window_id)
PARTITION BY run_id;
```

`PARTITION BY run_id` cho phép xóa gọn một run thất bại bằng `DROP PARTITION`.

### 3.2 fact_retrieval_trace

Một dòng mỗi context event được retrieve. Dùng để chấm context precision.

```sql
CREATE TABLE fact_retrieval_trace (
    run_id          LowCardinality(String),
    window_id       String,
    event_id        String,
    modality        LowCardinality(String),
    service         LowCardinality(String),
    event_ts        DateTime64(3, 'UTC'),
    score           Float32,
    rank            UInt16,
    debug_json      String,
    created_at      DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (run_id, window_id, rank)
PARTITION BY run_id
TTL created_at + INTERVAL 180 DAY;
```

### 3.3 Query pattern chính

```sql
-- Chỉ số phân loại của một run
SELECT
    countIf(verdict = 'TRUE_ALERT' AND label_is_fault = 1) AS tp,
    countIf(verdict = 'TRUE_ALERT' AND label_is_fault = 0) AS fp,
    countIf(verdict != 'TRUE_ALERT' AND label_is_fault = 1) AS fn,
    countIf(verdict != 'TRUE_ALERT' AND label_is_fault = 0) AS tn
FROM fact_alert_evaluation
WHERE run_id = {run_id:String};

-- Context coverage
SELECT
    countIf(context_event_count > 0) / count() AS coverage
FROM fact_alert_evaluation
WHERE run_id = {run_id:String} AND label_is_fault = 1;

-- Latency retrieval
SELECT
    avg(retrieval_latency_ms) AS avg_ms,
    quantile(0.95)(retrieval_latency_ms) AS p95_ms
FROM fact_alert_evaluation
WHERE run_id = {run_id:String} AND retrieval_strategy != '';
```

---

## 4. PostgreSQL DDL

Dùng cho dữ liệu quan hệ và ít thay đổi.

```sql
CREATE TABLE run_registry (
    run_id          TEXT PRIMARY KEY,
    config_yaml     TEXT NOT NULL,
    git_commit      TEXT NOT NULL,
    split           TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',  -- running|done|failed
    notes           TEXT
);

CREATE TABLE incidents (
    incident_id     TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES run_registry(run_id),
    alert_ids       JSONB NOT NULL,
    services        JSONB NOT NULL,
    start_ts        TIMESTAMPTZ NOT NULL,
    end_ts          TIMESTAMPTZ NOT NULL,
    grouping_reason JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_incidents_run ON incidents(run_id, start_ts);

CREATE TABLE diagnostic_reports (
    incident_id     TEXT PRIMARY KEY REFERENCES incidents(incident_id),
    run_id          TEXT NOT NULL,
    report          JSONB NOT NULL,        -- toàn bộ DiagnosticReport
    schema_version  TEXT NOT NULL,
    valid           BOOLEAN NOT NULL,
    validation_error TEXT,
    llm_backend     TEXT,
    e2e_latency_ms  REAL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE diagnostic_rejected (
    id              BIGSERIAL PRIMARY KEY,
    incident_id     TEXT,
    run_id          TEXT,
    raw_output      TEXT,
    reject_reason   TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

Bảng `diagnostic_rejected` là DLQ của Nhánh B. Không được nuốt lỗi im lặng.

---

## 5. Event schema (chỉ cần khi bật Redpanda)

Trong profile `dev`, pipeline chạy in-process, không cần broker. Khi bật profile `full` hoặc chuẩn bị GĐ3, dùng các topic sau:

```text
aiops.window.raw
aiops.alert.candidate
aiops.alert.judged
aiops.incident.created
aiops.diagnostic.report
aiops.dlq
```

Mọi event có phần bao ngoài chung:

```python
class EventEnvelope(BaseModel):
    event_id: str
    schema_version: str
    event_type: str
    run_id: str
    produced_at: datetime
    payload: dict[str, Any]
```

Quy tắc kế thừa từ dự án Gateway:
- Mọi event có `event_id` và `schema_version`
- Consumer validate trước khi ghi DB
- Event invalid đi `aiops.dlq`, không drop
- Không commit offset trước khi xử lý xong
- Consumer idempotent theo `window_id` + `run_id`

---

## 6. Cấu hình LLM cache

```python
cache_key = sha256(
    prompt_text + model_name + str(temperature) + str(max_tokens)
).hexdigest()
```

Lưu ở `data/llm_cache/` dạng file JSON hoặc SQLite. **Commit `.gitignore`, không commit cache** (dung lượng lớn), nhưng phải giữ giữa các lần chạy trên máy local.

Ghi `cache_hit` vào mọi bản ghi để báo cáo tỷ lệ cache hit trong `runtime.json`. Ablation Rescue Score chỉ khả thi về chi phí nhờ cache này.

---

## 7. Quy tắc thay đổi schema

- Thay đổi model Pydantic → cập nhật tài liệu này trong cùng commit
- Thay đổi DDL ClickHouse → viết migration script trong `infra/clickhouse/migrations/`, không sửa `init.sql` tại chỗ
- Thay đổi `DiagnosticReport` → tăng `schema_version`, giữ validator cho version cũ
- Không thêm trường "cho chắc". Chỉ thêm khi có chỗ dùng cụ thể.
