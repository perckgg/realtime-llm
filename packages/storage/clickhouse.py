"""ClickHouse client for the AIOps RCA Platform (03-schemas-and-contracts.md
SS3). Thin wrapper, no business logic -- reads connection settings from the
CLICKHOUSE_* environment variables in .env.example, matching the
docker-compose.yml `clickhouse` service.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import clickhouse_connect

# Column order for fact_alert_evaluation, verbatim from infra/clickhouse/init.sql.
FACT_ALERT_EVALUATION_COLUMNS = [
    "run_id",
    "window_id",
    "service",
    "window_ts",
    "anomaly_score",
    "candidate_source",
    "rescue_score",
    "rescue_lambda_log",
    "rescue_phi_topo",
    "rescue_delta_time",
    "retrieval_strategy",
    "retrieval_latency_ms",
    "context_event_count",
    "context_tokens",
    "retrieval_truncated",
    "verdict",
    "confidence",
    "judge_backend",
    "llm_latency_ms",
    "cache_hit",
    "downgraded",
    "label_is_fault",
    "label_fault_type",
    "label_root_cause",
]


def get_client() -> Any:
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
        port=int(os.environ.get("CLICKHOUSE_PORT", "8123")),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "aiops"),
        database=os.environ.get("CLICKHOUSE_DB", "aiops"),
    )


def run_exists(run_id: str, client: Any | None = None) -> bool:
    """True if fact_alert_evaluation already holds rows for `run_id`.

    Rule 3 of AGENTS.md: results are never overwritten or appended to under
    the same run_id -- a re-run with other parameters gets a new run_id
    (QD-015, D5). MergeTree does not deduplicate, so callers must check.
    """
    owns_client = client is None
    client = client or get_client()
    try:
        result = client.query(
            "SELECT count() FROM fact_alert_evaluation WHERE run_id = {run_id:String}",
            parameters={"run_id": run_id},
        )
        return int(result.result_rows[0][0]) > 0
    finally:
        if owns_client:
            client.close()


def insert_alert_evaluations(rows: list[dict[str, Any]], client: Any | None = None) -> None:
    """Insert rows into fact_alert_evaluation. Each row must have every key
    in FACT_ALERT_EVALUATION_COLUMNS -- build one with
    `pending_alert_evaluation_row` for a run where retrieval/judge haven't
    executed yet (e.g. Week 2's detector-only smoke test)."""
    if not rows:
        return
    owns_client = client is None
    client = client or get_client()
    try:
        data = [[row[column] for column in FACT_ALERT_EVALUATION_COLUMNS] for row in rows]
        client.insert("fact_alert_evaluation", data, column_names=FACT_ALERT_EVALUATION_COLUMNS)
    finally:
        if owns_client:
            client.close()


def pending_alert_evaluation_row(
    run_id: str,
    window_id: str,
    service: str,
    window_ts: datetime,
    anomaly_score: float,
    candidate_source: str,
    label_is_fault: bool,
    label_fault_type: str,
    label_root_cause: str | None,
) -> dict[str, Any]:
    """A fact_alert_evaluation row for a window that has only been through
    the detector so far -- retrieval/judge have not run in this run
    (verdict="NONE", retrieval_strategy/judge_backend="none"). See
    docs/experiment-log.md QD-009. `fact_alert_evaluation` gets one row per
    window per run regardless of whether the detector promoted it
    (03-schemas-and-contracts.md SS3.1), so `candidate_source` is "none" for
    a window the detector did not promote.
    """
    return {
        "run_id": run_id,
        "window_id": window_id,
        "service": service,
        "window_ts": window_ts,
        "anomaly_score": anomaly_score,
        "candidate_source": candidate_source,
        "rescue_score": None,
        "rescue_lambda_log": None,
        "rescue_phi_topo": None,
        "rescue_delta_time": None,
        "retrieval_strategy": "none",
        "retrieval_latency_ms": 0.0,
        "context_event_count": 0,
        "context_tokens": 0,
        "retrieval_truncated": 0,
        "verdict": "NONE",
        "confidence": None,
        "judge_backend": "none",
        "llm_latency_ms": None,
        "cache_hit": 0,
        "downgraded": 0,
        "label_is_fault": int(label_is_fault),
        "label_fault_type": label_fault_type,
        "label_root_cause": label_root_cause or "",
    }
