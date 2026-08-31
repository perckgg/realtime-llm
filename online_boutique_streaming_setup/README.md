# Online Boutique True Streaming Sandbox

Sandbox này tạo controlled true-streaming dataset cho paper về context rescue, promote candidate và candidate selection. Setup không gọi LLM; LLM chỉ dùng ở phase experiment sau khi telemetry và ground truth đã được thu ổn định.

## Prerequisites

Chạy các lệnh trong WSL2 Ubuntu tại thư mục này:

```bash
cd /mnt/c/Working/Internship1/online_boutique_streaming_setup
```

Yêu cầu:
- Docker Engine + Docker Compose plugin
- `kubectl`
- `kind`
- `helm`
- Python 3 với `PyYAML`

Nếu image `hello-world` chưa có local, preflight sẽ cần network để pull. Có thể bỏ qua bằng:

```bash
SKIP_HELLO_WORLD=1 bash scripts/00_check_prereqs.sh
```

## Quick Start

```bash
bash scripts/00_check_prereqs.sh
bash scripts/02_start_telemetry_store.sh
bash scripts/01_create_kind_cluster.sh
bash scripts/03_deploy_online_boutique.sh
bash scripts/04_deploy_collectors.sh
python3 scripts/06_verify_data_flow.py --wait-seconds 60
```

Sau khi workload ổn định, chạy fault schedule:

```bash
python3 scripts/05_run_fault_schedule.py --max-faults 3
python3 scripts/06_verify_data_flow.py --wait-seconds 30 --allow-empty
```

Frontend Online Boutique:

```text
http://localhost:8080
```

Redis:

```text
localhost:6379
```

PostgreSQL:

```text
postgresql://ob_streaming:ob_streaming@localhost:5432/ob_streaming
```

## Expected Streams

- `ob:metrics`: metric samples and pod status samples
- `ob:logs`: Kubernetes events and log-like context
- `ob:traces`: raw OTLP trace payload metadata until detailed trace parsing is added
- `ob:faults`: ground-truth fault lifecycle events
- `ob:windows`: online metric windows produced by later adapter work

## Normal Workflow

1. Collect at least 20 minutes of normal traffic for baseline.
2. Run one fault at a time with cooldown.
3. Verify `fault_events` and Redis `ob:faults`.
4. Build online windows using `event_time`, `ingest_time`, and `watermark_time`.
5. Run detector-only, detector + context rescue, and candidate selection policy.
6. Export overall and per-fault/service/pod tables.

## Teardown

Delete the Kubernetes cluster but keep Redis/Postgres data:

```bash
bash scripts/teardown.sh
```

Delete cluster and local telemetry volumes:

```bash
bash scripts/teardown.sh --volumes
```

## Notes For Paper

- Nezha remains the public benchmark.
- Online Boutique is controlled true-streaming validation.
- Microsoft cloud-monitoring remains detector-only; do not use it for RAG/API/context-rescue claims.
- Report context freshness and no-future-leakage checks with streaming results.
