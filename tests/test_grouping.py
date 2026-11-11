"""services/rca_agent/grouping.py: time clusters + service-graph components (M6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import networkx as nx

from packages.graph.service_graph import ServiceGraph
from packages.schemas.models import JudgedAlert
from services.rca_agent.grouping import group_alerts, time_clusters

T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)


def _alert(alert_id: str, service: str, seconds: float) -> JudgedAlert:
    return JudgedAlert(
        alert_id=alert_id,
        candidate_id=alert_id,
        window_id=alert_id,
        service=service,
        ts=T0 + timedelta(seconds=seconds),
        verdict="TRUE_ALERT",
        raw_verdict="TRUE_ALERT",
        confidence=0.9,
        reasoning="",
        evidence_event_ids=["e"],
        judge_backend="mock",
        llm_latency_ms=0.0,
        cache_hit=True,
    )


def _graph() -> ServiceGraph:
    directed = nx.DiGraph()
    directed.add_edge("frontend", "cart", weight=3)
    directed.add_edge("cart", "redis", weight=2)
    directed.add_node("payment")
    return ServiceGraph(directed)


def test_time_clusters_chain_within_t_group() -> None:
    alerts = [_alert("c", "x", 700), _alert("a", "x", 0), _alert("b", "x", 300)]
    assert [[a.alert_id for a in c] for c in time_clusters(alerts, 300)] == [["a", "b"], ["c"]]
    assert len(time_clusters(alerts, 400)) == 1


def test_components_of_the_induced_service_subgraph() -> None:
    alerts = [
        _alert("f", "frontend", 0),
        _alert("r", "redis", 60),  # linked to frontend only through cart
        _alert("p", "payment", 90),
        _alert("c", "cart", 120),
        _alert("u", "unknown", 130),
        _alert("late", "frontend", 2000),
    ]
    incidents = group_alerts(alerts, _graph(), "run", 300)
    groups = [(i.services, i.alert_ids) for i in incidents]
    assert groups == [
        (["cart", "frontend", "redis"], ["f", "r", "c"]),
        (["payment"], ["p"]),
        (["unknown"], ["u"]),
        (["frontend"], ["late"]),
    ]
    first = incidents[0]
    assert first.grouping_reason == {
        "temporal_window_sec": 300,
        "graph_edges_used": [["cart", "frontend"], ["cart", "redis"]],
    }
    assert (first.start_ts, first.end_ts) == (T0, T0 + timedelta(seconds=120))
    assert first.incident_id == group_alerts(list(reversed(alerts)), _graph(), "run", 300)[0].incident_id


def test_without_the_middle_service_the_chain_splits() -> None:
    alerts = [_alert("f", "frontend", 0), _alert("r", "redis", 60)]
    assert [i.services for i in group_alerts(alerts, _graph(), "run", 300)] == [["frontend"], ["redis"]]
