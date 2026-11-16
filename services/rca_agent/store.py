"""PostgreSQL writer of the RCA agent (03 SS4): run_registry, incidents, diagnostic_reports,
diagnostic_rejected. Thin wrapper, no business logic; tables come from infra/postgres/init.sql.

Connection settings: the `POSTGRES_*` environment variables (.env.example), matching the
`postgres` service of docker-compose.yml. A run_id that is already registered is refused
(AGENTS.md rule 3: results are never overwritten).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from packages.schemas.models import DiagnosticReport, Incident


def connect(timeout_seconds: int = 5) -> psycopg.Connection[Any]:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "aiops"),
        password=os.environ.get("POSTGRES_PASSWORD", "aiops"),
        dbname=os.environ.get("POSTGRES_DB", "aiops"),
        connect_timeout=timeout_seconds,
    )


def run_exists(conn: psycopg.Connection[Any], run_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM run_registry WHERE run_id = %s", (run_id,)).fetchone()
    return row is not None


def register_run(
    conn: psycopg.Connection[Any],
    run_id: str,
    config_yaml: str,
    git_commit: str,
    split: str,
    seed: int,
    started_at: datetime,
    notes: str | None = None,
) -> None:
    if run_exists(conn, run_id):
        raise ValueError(f"run_id {run_id!r} is already in run_registry: use a new run_id")
    conn.execute(
        "INSERT INTO run_registry (run_id, config_yaml, git_commit, split, seed, started_at, status, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'running', %s)",
        (run_id, config_yaml, git_commit, split, seed, started_at, notes),
    )


def finish_run(conn: psycopg.Connection[Any], run_id: str, finished_at: datetime, status: str = "done") -> None:
    conn.execute(
        "UPDATE run_registry SET finished_at = %s, status = %s WHERE run_id = %s", (finished_at, status, run_id)
    )


def insert_incidents(conn: psycopg.Connection[Any], incidents: Sequence[Incident]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO incidents (incident_id, run_id, alert_ids, services, start_ts, end_ts, grouping_reason) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                (i.incident_id, i.run_id, Jsonb(i.alert_ids), Jsonb(i.services), i.start_ts, i.end_ts,
                 Jsonb(i.grouping_reason))
                for i in incidents
            ],  # fmt: skip
        )


def insert_report(
    conn: psycopg.Connection[Any],
    report: DiagnosticReport,
    suspicious: bool = False,
    e2e_latency_ms: float | None = None,
) -> None:
    """A published report (it passed 03 SS2.1). `suspicious` (root cause outside the service
    graph) is kept in `validation_error`, the only free-text column of the table."""
    conn.execute(
        "INSERT INTO diagnostic_reports (incident_id, run_id, report, schema_version, valid, validation_error, "
        "llm_backend, e2e_latency_ms) VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s)",
        (
            report.incident_id,
            report.run_id,
            Jsonb(report.model_dump(mode="json")),
            report.schema_version,
            "suspicious: root_cause_service not in the service graph" if suspicious else None,
            report.llm_backend,
            e2e_latency_ms,
        ),
    )


def insert_rejected(
    conn: psycopg.Connection[Any], incident_id: str, run_id: str, raw_output: str, reject_reason: str
) -> None:
    conn.execute(
        "INSERT INTO diagnostic_rejected (incident_id, run_id, raw_output, reject_reason) VALUES (%s, %s, %s, %s)",
        (incident_id, run_id, raw_output, reject_reason),
    )


def counts(conn: psycopg.Connection[Any], run_id: str) -> dict[str, int]:
    out = {}
    for table in ("incidents", "diagnostic_reports", "diagnostic_rejected"):
        row = conn.execute(f"SELECT count(*) FROM {table} WHERE run_id = %s", (run_id,)).fetchone()  # noqa: S608
        out[table] = int(row[0]) if row else 0
    return out


def delete_run(conn: psycopg.Connection[Any], run_id: str) -> None:
    """Tests only: remove one run's rows (children first)."""
    for table in ("diagnostic_rejected", "diagnostic_reports", "incidents", "run_registry"):
        conn.execute(f"DELETE FROM {table} WHERE run_id = %s", (run_id,))  # noqa: S608
