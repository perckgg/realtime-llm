"""eval/harness/rca.py: labels, ARR, Hit@k, the two selection rules, PostgreSQL writer (M9)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import networkx as nx
import pytest

from eval.harness import rca
from packages.graph.service_graph import ServiceGraph
from packages.schemas.models import JudgedAlert
from services.rca_agent.grouping import group_alerts, time_clusters

T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)


def _alert(alert_id: str, service: str, seconds: float) -> JudgedAlert:
    return JudgedAlert(
        alert_id=alert_id, candidate_id=alert_id, window_id=alert_id, service=service,
        ts=T0 + timedelta(seconds=seconds), verdict="TRUE_ALERT", raw_verdict="TRUE_ALERT", confidence=0.9,
        reasoning="", evidence_event_ids=["e"], judge_backend="mock", llm_latency_ms=0.0, cache_hit=True,
    )  # fmt: skip


def _graph() -> ServiceGraph:
    directed = nx.DiGraph()
    directed.add_edge("frontend", "cart", weight=3)
    directed.add_node("payment")
    return ServiceGraph(directed)


def _injection(injection_id: str, service: str, start: float, fault_type: str = "network_delay") -> rca.Injection:
    return rca.Injection(injection_id, fault_type, service, T0 + timedelta(seconds=start),
                         T0 + timedelta(seconds=start + 420))  # fmt: skip


INJECTIONS = [_injection("i1", "cart", 0), _injection("i2", "payment", 3000, "exception")]
BY_ID = {i.injection_id: i for i in INJECTIONS}
ALERTS = [
    _alert("a1", "frontend", 60),  # i1, caller of the root cause
    _alert("a2", "cart", 120),  # i1, root cause
    _alert("a3", "cart", 400),  # i1 (window starts before the injection ends)
    _alert("a4", "payment", 1500),  # outside any injection
    _alert("a5", "payment", 3100),  # i2
]
MEMBERSHIP = {a.alert_id: rca.alert_injections(a, INJECTIONS, 60) for a in ALERTS}


def test_alert_belongs_to_the_injection_its_window_overlaps() -> None:
    assert MEMBERSHIP == {"a1": ["i1"], "a2": ["i1"], "a3": ["i1"], "a4": [], "a5": ["i2"]}
    assert rca.alert_injections(_alert("x", "s", -60), INJECTIONS, 60) == []  # ends exactly at the start
    assert rca.alert_injections(_alert("x", "s", -59), INJECTIONS, 60) == ["i1"]
    assert rca.alert_injections(_alert("x", "s", 420), INJECTIONS, 60) == []  # the injection end is exclusive


def test_labels_labelled_no_fault_and_ambiguous() -> None:
    incidents = group_alerts(ALERTS, _graph(), "run", 300)
    labelled = rca.label_incidents(incidents, MEMBERSHIP, BY_ID)
    assert [(x.status, x.root_cause, x.incident.alert_ids) for x in labelled] == [
        ("labelled", "cart", ["a1", "a2", "a3"]),
        ("no_fault", None, ["a4"]),
        ("labelled", "payment", ["a5"]),
    ]
    merged = rca.label_incidents(group_alerts(ALERTS, _graph(), "run", 5000), MEMBERSHIP, BY_ID)
    # one time cluster, two graph components: a4 (no fault) joins a5, the incident is still i2's
    assert [(x.status, x.injection_ids) for x in merged] == [("labelled", ["i1"]), ("labelled", ["i2"])]
    both = [_alert("b1", "payment", 100), _alert("b2", "payment", 3050)]
    members = {a.alert_id: rca.alert_injections(a, INJECTIONS, 60) for a in both}
    one = rca.label_incidents(group_alerts(both, _graph(), "run", 5000), members, BY_ID)
    assert [(x.status, x.injection_ids, x.root_cause) for x in one] == [("ambiguous", ["i1", "i2"], None)]


def test_alert_sets_and_reduction() -> None:
    sets = rca.alert_sets(ALERTS, MEMBERSHIP, BY_ID, cascade_min_services=2)
    assert sets["all"] == {"a1", "a2", "a3", "a4", "a5"}
    assert sets["fault"] == {"a1", "a2", "a3", "a5"}
    assert sets["cascade"] == {"a1", "a2", "a3"}  # i1 touches frontend and cart; i2 only payment
    assert sets["type:network_delay"] == {"a1", "a2", "a3"} and sets["type:exception"] == {"a5"}
    by_t = {t: group_alerts(ALERTS, _graph(), "run", t) for t in (100.0, 300.0)}
    units = time_clusters(ALERTS, 300.0)
    table = rca.reduction_table(units, by_t, sets, 300.0, n_boot=200, seed=42)
    # T=300: {a1,a2,a3} one incident, a4, a5 -> 3 incidents of 5 alerts; T=100: a3 splits off
    assert (table["all"]["300"]["incidents"], table["all"]["300"]["arr"]) == (3, pytest.approx(0.4))
    assert (table["all"]["100"]["incidents"], table["all"]["100"]["arr"]) == (4, pytest.approx(0.2))
    assert table["cascade"]["300"]["arr"] == pytest.approx(1 - 1 / 3)
    assert table["cascade"]["100"]["d_arr_vs_reference"] == pytest.approx(-1 / 3)
    assert table["type:exception"]["300"]["arr"] == 0.0
    lo, hi = table["all"]["300"]["arr_ci95"]
    assert 0.0 <= lo <= 0.4 <= hi <= 1.0


def _reduction(arr: dict[int, float], ci: dict[int, list[float]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {str(t): {"arr": v} for t, v in arr.items()}
    for t, bounds in ci.items():
        out[str(t)]["d_arr_vs_reference_ci95"] = bounds
    return out


def test_t_group_rule_keeps_the_default_inside_the_ci() -> None:
    grid = [180.0, 300.0, 600.0]
    same = {180.0: 0, 300.0: 0, 600.0: 0}
    reduction = _reduction({180: 0.3, 300: 0.4, 600: 0.5}, {180: [-0.2, 0.0], 600: [-0.01, 0.2]})
    assert rca.select_t_group(grid, 300.0, same, reduction)[0] == 300.0
    assert rca.reference_t_group(grid, 300.0, same) == 300.0


def test_t_group_rule_moves_only_on_a_clear_gain_and_never_to_more_ambiguity() -> None:
    grid = [180.0, 300.0, 600.0]
    same = {180.0: 0, 300.0: 0, 600.0: 0}
    reduction = _reduction({180: 0.3, 300: 0.4, 600: 0.5}, {180: [-0.2, -0.01], 600: [0.02, 0.2]})
    assert rca.select_t_group(grid, 300.0, same, reduction)[0] == 600.0
    # the same gain, but 600 s merges two faults: it is not even considered
    assert rca.select_t_group(grid, 300.0, {180.0: 0, 300.0: 0, 600.0: 1}, reduction)[0] == 300.0
    # the default itself merges faults: fall back to the smallest T with the fewest ambiguous
    worse = {180.0: 0, 300.0: 1, 600.0: 2}
    assert rca.reference_t_group(grid, 300.0, worse) == 180.0
    assert rca.select_t_group(grid, 300.0, worse, _reduction({180: 0.3, 300: 0.4, 600: 0.5}, {}))[0] == 180.0


def test_sign_rule() -> None:
    assert rca.select_sign("alert", {"d_hit1_ci95": [-0.1, 0.2]})[0] == "alert"
    assert rca.select_sign("alert", {"d_hit1_ci95": [0.0, 0.2]})[0] == "alert"
    assert rca.select_sign("alert", {"d_hit1_ci95": [0.01, 0.2]})[0] == "candidate"
    assert rca.select_sign("alert", {"d_hit1_ci95": None})[0] == "alert"


def _rows() -> list[dict[str, str]]:
    rows = []
    for alert, score in zip(ALERTS, [0.9, 0.6, 0.7, 0.5, 0.8], strict=True):
        rows.append({"window_id": alert.window_id, "service": alert.service, "window_ts": alert.ts.isoformat(),
                     "anomaly_score": str(score), "is_candidate": "1"})  # fmt: skip
    return rows


def test_hit_tables_level1_beats_the_baseline_on_a_cascade() -> None:
    labelled = rca.label_incidents(group_alerts(ALERTS, _graph(), "run", 300), MEMBERSHIP, BY_ID)
    series = rca.ServiceSeries(_rows())
    alerts_by_id = {a.alert_id: a for a in ALERTS}
    scores = {"a1": 0.9, "a2": 0.6, "a3": 0.7, "a4": 0.5, "a5": 0.8}
    located = [rca.locate(x, alerts_by_id, scores, _graph(), series, "alert", 60) for x in labelled]
    first = located[0]
    assert [r.service for r in first.level1] == ["cart", "frontend"]  # blame moved from frontend to cart
    assert first.baseline == ["frontend", "cart"]  # frontend has the highest anomaly score
    hits = rca.hit_table(located, n_boot=200, seed=42)
    assert hits["n"] == 2  # the no_fault incident is not scored
    assert (hits["level1_hit1"], hits["baseline_hit1"], hits["d_hit1"]) == (1.0, 0.5, 0.5)
    assert (hits["level1_hit3"], hits["baseline_hit3"]) == (1.0, 1.0)
    assert hits["discordant_hit1"] == {"level1_only": 1, "baseline_only": 0}
    per_injection = rca.injection_table(located, [*INJECTIONS, _injection("i3", "cart", 9000)], 200, 42)
    assert (per_injection["injections"], per_injection["with_labelled_incident"], per_injection["without_alert"]) == (3, 2, 1)
    assert per_injection["level1_hit1"] == pytest.approx(2 / 3)
    record = rca.incident_record(first)
    assert record["root_cause"] == "cart" and record["level1_hit1"] is True and record["baseline_hit1"] is False


def test_candidate_sign_uses_detector_flags_inside_the_span_only() -> None:
    alert = _alert("f", "frontend", 0)
    labelled = rca.label_incidents(group_alerts([alert], _graph(), "run", 300), {"f": ["i1"]}, BY_ID)[0]
    rows = [
        {"window_id": "f", "service": "frontend", "window_ts": alert.ts.isoformat(), "anomaly_score": "0.6", "is_candidate": "1"},
        {"window_id": "c", "service": "cart", "window_ts": (T0 + timedelta(seconds=30)).isoformat(), "anomaly_score": "0.4", "is_candidate": "1"},
        {"window_id": "late", "service": "cart", "window_ts": (T0 + timedelta(seconds=900)).isoformat(), "anomaly_score": "0.99", "is_candidate": "1"},
    ]  # fmt: skip
    series = rca.ServiceSeries(rows)
    assert series.span("cart", T0 - timedelta(seconds=60), T0 + timedelta(seconds=60)) == (0.4, True)
    by_alert = rca.locate(labelled, {"f": alert}, {"f": 0.6}, _graph(), series, "alert", 60)
    by_candidate = rca.locate(labelled, {"f": alert}, {"f": 0.6}, _graph(), series, "candidate", 60)
    assert [r.service for r in by_alert.level1] == ["frontend"]
    assert [r.service for r in by_candidate.level1] == ["cart", "frontend"]
    assert by_candidate.baseline == ["frontend"]


def test_config_guards(tmp_path: Path) -> None:
    base = "kind: rca\nrun_id: r\nsplit: {split}\ninput: {{alerts_run: x, evidence_run: y}}\ngrouping: {{t_group_seconds: 300}}\npropagation: {{sign: alert}}\n"
    path = tmp_path / "c.yaml"
    path.write_text(base.format(split="test"), encoding="utf-8")
    with pytest.raises(ValueError, match="M9-B"):
        rca.load_rca_config(path)
    path.write_text(base.format(split="val"), encoding="utf-8")
    config = rca.load_rca_config(path)
    assert rca.config_fingerprint(config) == rca.config_fingerprint({**config, "run_id": "other", "split": "test"})
    assert rca.config_fingerprint(config) != rca.config_fingerprint({**config, "grouping": {"t_group_seconds": 600}})


def test_postgres_roundtrip_and_run_id_guard() -> None:
    """Needs `docker compose --profile dev up -d`; skipped (not passed) without PostgreSQL."""
    psycopg = pytest.importorskip("psycopg")
    from services.rca_agent import store
    from services.rca_agent.propagation import backward_one_hop
    from services.rca_agent.summarizer import MockSummaryBackend, Summarizer
    from tests.test_rca_summarizer import EVENTS

    try:
        conn = store.connect(timeout_seconds=2)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not running")
    run_id = f"pytest-rca-{uuid.uuid4().hex[:12]}"
    incidents = group_alerts(ALERTS, _graph(), run_id, 300)
    try:
        store.register_run(conn, run_id, "kind: rca", "deadbeef", "val", 42, T0)
        with pytest.raises(ValueError, match="already in run_registry"):
            store.register_run(conn, run_id, "kind: rca", "deadbeef", "val", 42, T0)
        store.insert_incidents(conn, incidents)
        ranked = backward_one_hop(incidents[0].services, _graph(), {})
        result = Summarizer(MockSummaryBackend(), _graph()).summarize(incidents[0], ALERTS[:3], ranked, ["cart"], EVENTS)
        assert result.report is not None
        store.insert_report(conn, result.report, suspicious=False, e2e_latency_ms=1.5)
        store.insert_rejected(conn, incidents[1].incident_id, run_id, "{}", "no_evidence")
        store.finish_run(conn, run_id, T0 + timedelta(seconds=1))
        assert store.counts(conn, run_id) == {"incidents": 3, "diagnostic_reports": 1, "diagnostic_rejected": 1}
        row = conn.execute(
            "SELECT alert_ids, services, grouping_reason FROM incidents WHERE incident_id = %s", (incidents[0].incident_id,)
        ).fetchone()
        assert row is not None and row[0] == ["a1", "a2", "a3"] and row[1] == ["cart", "frontend"]
        assert row[2]["temporal_window_sec"] == 300
        stored = conn.execute(
            "SELECT report->>'root_cause_service', valid FROM diagnostic_reports WHERE run_id = %s", (run_id,)
        ).fetchone()
        assert stored == ("cart", True)
    finally:
        conn.rollback()  # nothing of the test is ever committed
        conn.close()
