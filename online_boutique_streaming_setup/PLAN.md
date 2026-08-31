# Online Boutique True Streaming Sandbox Plan

## Purpose

Sandbox này tạo một dataset true streaming có ground truth rõ ràng để bổ sung cho Nezha khi viết paper về `context rescue score`, `promote candidate` và `candidate selection`.

Nezha vẫn là public benchmark chính. Online Boutique là controlled validation: telemetry được sinh theo thời gian thực, fault được inject có lịch, mỗi event có `event_time`, `ingest_time`, `service_id`, `pod_id`, `node_id`, `source` và `fault_id` để kiểm tra no-future-leakage.

Microsoft cloud-monitoring vẫn chỉ dùng cho detector-only threshold/domain analysis. Không dùng RAG/API/context-rescue claims từ dataset đó.

## Data Flow

```text
Online Boutique on kind
  -> Prometheus and OpenTelemetry Collector
  -> telemetry-bridge
  -> Redis Streams: ob:metrics, ob:logs, ob:traces, ob:faults, ob:windows
  -> PostgreSQL + pgvector
  -> online window builder / detector / context rescue / audit
```

## Phase 0 - Preflight

Goal: đảm bảo máy WSL2 có đủ runtime.

Steps:
- Verify WSL2 Ubuntu.
- Verify Docker Engine, Docker Compose plugin, `kubectl`, `kind`, `helm`, Python 3.
- Verify Docker daemon bằng `docker info`.
- Verify Docker image pull/run bằng `docker run --rm hello-world` nếu không set `SKIP_HELLO_WORLD=1`.

Acceptance:
- `scripts/00_check_prereqs.sh` chạy pass.
- `docker compose version`, `kind version`, `kubectl version --client`, `helm version` đều trả kết quả.

## Phase 1 - Local Telemetry Data Plane

Goal: dựng hot event bus và durable store.

Steps:
- Start Redis và PostgreSQL pgvector bằng `compose/telemetry-store.yml`.
- Init schema bằng `sql/001_init.sql`.
- Tạo Redis Streams và consumer groups cho:
  - `ob:metrics`
  - `ob:logs`
  - `ob:traces`
  - `ob:faults`
  - `ob:windows`

Acceptance:
- Redis `PING` trả `PONG`.
- PostgreSQL `pg_isready` pass.
- `SELECT extversion FROM pg_extension WHERE extname = 'vector';` trả version.
- Các bảng `fault_events`, `metric_samples`, `log_events`, `trace_spans`, `context_documents`, `metric_windows`, `pipeline_audit` tồn tại.

## Phase 2 - Kubernetes Sandbox

Goal: chạy workload microservice thật.

Steps:
- Tạo kind cluster `ob-streaming` từ `kind/kind-config.yaml`.
- Tạo namespace `online-boutique`.
- Deploy Online Boutique bản `v0.10.5`.
- Patch `frontend-external` sang NodePort `30080`, map ra host `http://localhost:8080`.
- Bật load generator ổn định để tạo baseline traffic.

Acceptance:
- Tất cả deployment trong namespace `online-boutique` ready.
- Frontend truy cập được tại `http://localhost:8080`.
- Load generator có pod running.

## Phase 3 - Telemetry Collection

Goal: thu telemetry theo luồng thật.

Steps:
- Deploy Prometheus stack để scrape Kubernetes/app metrics.
- Deploy OpenTelemetry Collector để nhận OTLP và Kubernetes telemetry.
- Deploy `telemetry-bridge` để chuẩn hóa telemetry, ghi Redis Streams bằng `XADD`, và persist PostgreSQL.
- Bridge ghi cả Kubernetes pod status/events và raw OTLP payload metadata. Trace/log parser chi tiết có thể bổ sung sau, nhưng event-time/ingest-time/fault-id contract được giữ ngay từ v1.

Acceptance:
- Redis stream length của `ob:metrics` tăng sau 60 giây.
- PostgreSQL `metric_samples` tăng sau 60 giây.
- Kubernetes events được ghi vào `ob:logs` khi có rollout/fault.
- `context_documents` có row từ log/event/OTLP payload.

## Phase 4 - Fault Injection

Goal: tạo ground truth cho controlled anomalies.

Steps:
- Cài Chaos Mesh bằng Helm.
- Chạy `scripts/05_run_fault_schedule.py` đọc `config/fault_schedule.yaml`.
- Với mỗi fault, scheduler:
  - ghi event `running` vào `ob:faults` và `fault_events`,
  - apply Chaos Mesh CRD,
  - đợi duration,
  - delete Chaos object,
  - ghi event `completed`,
  - đợi cooldown.

Fault types v1:
- `network_delay`
- `cpu_stress`
- `memory_stress`
- `pod_kill`
- `http_error`

Acceptance:
- Mỗi fault có `fault_id`, `fault_type`, `service_id`, `started_at`, `ended_at`, `status`.
- `ob:faults` có đủ running/completed events.
- Fault target service sinh signal rõ trong metric/log stream.

## Phase 5 - Streaming Adapter

Goal: biến metric stream thành online windows tương thích pipeline hiện tại.

Defaults:
- `window_size_seconds: 120`
- `stride_seconds: 60`
- `allowed_lag_seconds: 30`
- detector threshold baseline: `0.85`
- context rescue threshold: `min_context_score: 0.70`
- retrieval time margin: `8 minutes`

Rules:
- Label window bằng interval overlap với `fault_events`.
- Window `label=true_alert` nếu overlap với fault interval.
- Window `fault_type` lấy fault overlap chính.
- Retrieval chỉ được dùng context có `ingest_time <= window_end + allowed_lag_seconds`.
- Không dùng future context.

Acceptance:
- `metric_windows` có `window_start`, `window_end`, `label`, `fault_type`, `fault_id`, `watermark_time`.
- Query no-future-leakage trả 0 violation.

## Phase 6 - Experiments

Goal: tạo bảng paper-ready từ true streaming validation.

Runs tối thiểu:
- detector-only streaming
- detector + context rescue
- detector + candidate selection budget policy

Tables cần xuất:
- Overall: `Windows`, `Candidates`, `Precision`, `Recall`, `F1`, `FPR`, `TP`, `FP`, `FN`
- By fault type/service/pod: `Windows`, `Candidates`, `Precision`, `Recall`, `F1`, `FPR`, `FP`, `FN`
- Context rescue: promoted candidates, promoted TP/FP, rescued FN, added LLM calls
- Streaming validity: context freshness lag, time-to-detect, no-future-leakage violations

Acceptance:
- Có audit JSONL/CSV cho ít nhất 1 normal run và 3 injected faults.
- Có bảng so sánh detector-only vs context rescue.
- Có section giải thích Online Boutique là controlled streaming validation, không thay thế Nezha public benchmark.

## Implementation Defaults

- Cluster: `ob-streaming`
- Namespace: `online-boutique`
- Redis URL: `redis://localhost:6379/0`
- Postgres URL: `postgresql://ob_streaming:ob_streaming@localhost:5432/ob_streaming`
- Online Boutique ref: `v0.10.5`
- Warmup: `20 minutes`
- Fault duration: `5 minutes`
- Cooldown: `5 minutes`
- LLM: disabled during setup/collection

## References

- Docker Engine Ubuntu install: https://docs.docker.com/engine/install/ubuntu/
- kind quick start: https://kind.sigs.k8s.io/docs/user/quick-start/
- Online Boutique: https://github.com/GoogleCloudPlatform/microservices-demo
- OpenTelemetry Collector Kubernetes: https://opentelemetry.io/docs/platforms/kubernetes/collector/
- Redis Streams XADD: https://redis.io/docs/latest/commands/xadd/
- pgvector: https://github.com/pgvector/pgvector
- Chaos Mesh: https://chaos-mesh.org/docs/
