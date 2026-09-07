# packages/storage

`clickhouse.py` — thin `clickhouse_connect` wrapper, no business logic. Reads connection settings
from the `CLICKHOUSE_*` environment variables (`.env.example`), matching `docker-compose.yml`'s
`clickhouse` service. `insert_alert_evaluations` writes rows to `fact_alert_evaluation`
(`docs/Final_Thesis_Phase2/03-schemas-and-contracts.md` §3.1); `pending_alert_evaluation_row`
builds a row for a run where retrieval/judge haven't executed yet (`verdict="NONE"`), used by
`scripts/replay_smoke.py` for the Week 2 DoD.

PostgreSQL client (for `run_registry`/`incidents`/`diagnostic_reports`, §4) is not implemented yet
— no Week 2 service writes to Postgres. `infra/postgres/init.sql` already creates the tables.
