# services/api

Read-only FastAPI service (`main.py`, `readers.py`, `schemas.py`) implementing the 7 dashboard endpoints of `docs/Final_Thesis_Phase2/01-architecture-design.md` §6.6 (M10-B, QĐ-046):

- `GET /health`
- `GET /runs`
- `GET /runs/{run_id}/metrics`
- `GET /alerts?run_id=&verdict=&limit=&offset=`
- `GET /alerts/{alert_id}`
- `GET /incidents?run_id=`
- `GET /incidents/{incident_id}`

No authentication and no business logic (R-B5). Reads ClickHouse (`fact_alert_evaluation`, `fact_retrieval_trace`), PostgreSQL (`run_registry`, `incidents`, `diagnostic_reports`, `diagnostic_rejected`), `eval/results/`, and `data/graph/service_graph.json` (with `NezhaReplaySource` fallback for single-window metrics).
