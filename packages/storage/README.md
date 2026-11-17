# packages/storage

`clickhouse.py` — thin `clickhouse_connect` wrapper, no business logic. Reads connection settings
from the `CLICKHOUSE_*` environment variables (`.env.example`), matching `docker-compose.yml`'s
`clickhouse` service. `insert_alert_evaluations` writes rows to `fact_alert_evaluation`
(`docs/Final_Thesis_Phase2/03-schemas-and-contracts.md` §3.1); `pending_alert_evaluation_row`
builds a row for a run where retrieval/judge haven't executed yet (`verdict="NONE"`), used by
`scripts/replay_smoke.py` for the Week 2 DoD.

Phần ghi PostgreSQL (`run_registry`, `incidents`, `diagnostic_reports`, `diagnostic_rejected`, §4)
nằm ở `services/rca_agent/store.py` (V42, chốt giữ nguyên theo V47 (a) ở M10 — QĐ-045); phần đọc cho
dashboard đặt riêng trong `services/api/`. `infra/postgres/init.sql` tạo sẵn các bảng.
