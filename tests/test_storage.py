"""Unit tests for packages.storage.clickhouse that need no running ClickHouse:
the run_id guard (QD-015, D5; AGENTS.md rule 3) and row construction."""

from __future__ import annotations

from datetime import UTC, datetime

from packages.storage.clickhouse import (
    FACT_ALERT_EVALUATION_COLUMNS,
    pending_alert_evaluation_row,
    run_exists,
)


class _FakeResult:
    def __init__(self, count: int) -> None:
        self.result_rows = [(count,)]


class _FakeClient:
    def __init__(self, count: int) -> None:
        self.count = count
        self.queries: list[tuple[str, dict]] = []

    def query(self, sql: str, parameters: dict) -> _FakeResult:
        self.queries.append((sql, parameters))
        return _FakeResult(self.count)


def test_run_exists_true_when_rows_present():
    client = _FakeClient(50)
    assert run_exists("m1-smoke", client=client) is True
    assert client.queries[0][1] == {"run_id": "m1-smoke"}


def test_run_exists_false_for_new_run_id():
    assert run_exists("fresh", client=_FakeClient(0)) is False


def test_pending_row_has_every_column():
    row = pending_alert_evaluation_row(
        run_id="r",
        window_id="w",
        service="s",
        window_ts=datetime(2023, 1, 1, tzinfo=UTC),
        anomaly_score=0.9,
        candidate_source="metric",
        label_is_fault=True,
        label_fault_type="cpu_contention",
        label_root_cause=None,
    )
    assert set(row) == set(FACT_ALERT_EVALUATION_COLUMNS)
    assert row["label_root_cause"] == ""
