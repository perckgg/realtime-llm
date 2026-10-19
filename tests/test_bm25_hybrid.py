"""services.retrieval.bm25_hybrid: GD1 parity, no fault-type leak, debug fields."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.schemas.evidence import (
    EvidenceDoc,
    InMemoryEvidenceStore,
    load_gd1_corpus,
    parse_timestamp,
)
from packages.schemas.models import (
    AlertCandidate,
    MetricPoint,
    RetrievalBudget,
    TelemetryWindow,
    WindowLabel,
)
from services.detector.candidates import build_alert_candidate
from services.retrieval.bm25_hybrid import Bm25HybridRetriever, build_query
from services.retrieval.registry import build_budget, build_strategy
from tests.gd1 import LEGACY, gd1

FIXTURE = Path(__file__).parent / "fixtures" / "gd1_prompt_cases.json"
FAULT_TYPES = ["network_delay", "cpu_contention", "cpu_consumed", "exception", "return", "normal"]
T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)
POD = "cartservice-579f59597d-wc2lz"


def _window(label: WindowLabel | None) -> TelemetryWindow:
    return TelemetryWindow(
        window_id="w1",
        service="cartservice",
        pod=POD,
        start_ts=T0,
        end_ts=T0 + timedelta(seconds=60),
        metrics=[MetricPoint(name="PodClientLatencyP90(s)", value=1.5, ts=T0)],
        label=label,
    )


def _doc(i: int, service: str, message: str, seconds: float = 10, severity: str = "INFO") -> EvidenceDoc:
    event_type, source = ("trace_span", "nezha_trace") if "duration_ms=" in message else ("application_log", "nezha_log")
    return EvidenceDoc(
        f"d{i}", T0 + timedelta(seconds=seconds), f"{service}-579f59597d-wc2lz", service, severity,
        event_type, source, message,
    )


CORPUS = [
    _doc(0, "cartservice", "GetCart failed: redis timeout", severity="ERROR"),
    _doc(1, "cartservice", "Trace span hipstershop.CartService/GetCart on x duration_ms=1520.000", seconds=20),
    _doc(2, "frontend", "request complete cartservice", seconds=5),
    _doc(3, "cartservice", "cart emptied", seconds=-400),
    _doc(4, "cartservice", "outside the margin", seconds=60 * 30),
    _doc(5, "cartservice", "network_delay injected"),  # a doc that literally contains a fault-type token
]


@pytest.mark.parametrize("fault_type", FAULT_TYPES)
def test_query_never_contains_the_fault_type(fault_type):
    label = WindowLabel(is_fault=fault_type != "normal", fault_type=fault_type, root_cause_service="cartservice")
    candidate = build_alert_candidate(_window(label), 0.9, True)
    assert candidate is not None
    query = build_query(candidate)
    assert fault_type not in query.split()
    # The label cannot reach retrieval at all: same window, no label -> same query and same ranking.
    unlabelled = build_alert_candidate(_window(None), 0.9, True)
    assert unlabelled is not None and build_query(unlabelled) == query
    retriever = Bm25HybridRetriever(InMemoryEvidenceStore(CORPUS))
    labelled_ids = [e.event_id for e in retriever.retrieve(candidate, RetrievalBudget()).events]
    assert labelled_ids == [e.event_id for e in retriever.retrieve(unlabelled, RetrievalBudget()).events]
    # Sensitivity check: GD1's leak (fault type in the query) would have pulled d5 to the top.
    leaky = Bm25HybridRetriever(InMemoryEvidenceStore(CORPUS), extra_query_terms=lambda c: ["anomaly", "network_delay"])
    if fault_type == "network_delay":
        assert leaky.retrieve(candidate, RetrievalBudget()).events[0].event_id == "d5" != labelled_ids[0]


def test_window_pool_is_local_and_debug_is_filled():
    candidate = build_alert_candidate(_window(None), 0.9, True)
    assert candidate is not None
    result = Bm25HybridRetriever(InMemoryEvidenceStore(CORPUS)).retrieve(candidate, RetrievalBudget(top_k=3))
    assert result.strategy == "bm25_hybrid"
    assert len(result.events) == 3
    assert {e.service for e in result.events} == {"cartservice"}  # s0 only: tier-1 local evidence
    assert "d4" not in [e.event_id for e in result.events]  # beyond the 8-minute margin
    for rank, event in enumerate(result.events, start=1):
        assert event.origin == "local" and event.graph_distance == 0
        assert event.debug["rank"] == rank
        assert {"bm25_score", "time_distance_sec", "severity", "event_type", "source"} <= event.debug.keys()
    assert result.events[0].score >= result.events[-1].score
    assert {"query", "pool_size", "time_margin_sec"} <= result.debug.keys()
    assert result.debug["pool_size"] == 4  # d0, d1, d3, d5; frontend excluded; d4 out of range
    assert result.token_estimate > 0


def test_max_tokens_truncates():
    candidate = build_alert_candidate(_window(None), 0.9, True)
    assert candidate is not None
    result = Bm25HybridRetriever(InMemoryEvidenceStore(CORPUS)).retrieve(
        candidate, RetrievalBudget(top_k=6, max_tokens=6)
    )
    assert result.truncated and len(result.events) < 4


def _gd1_alert(alert: dict) -> AlertCandidate:
    return AlertCandidate(
        candidate_id=alert["alert_id"], window_id=alert["window_id"], service=alert["service_id"],
        pod=alert["node_id"], ts=parse_timestamp(alert["time_window"]["start"]),
        end_ts=parse_timestamp(alert["time_window"]["end"]), anomaly_score=alert["anomaly_score"],
        source="metric", metric_snapshot=alert["metric_snapshot"], top_features=alert["top_features"],
    )


def test_global_pool_matches_gd1_hybrid_retriever_on_synthetic_corpus():
    models = gd1("src.models")
    store_mod = gd1("src.retrieval.context_store")
    retriever_mod = gd1("src.retrieval.retriever")
    events = [
        models.LogEvent(d.doc_id, d.ts, d.pod, d.service, d.pod, d.severity, d.event_type, d.message, d.source)
        for d in CORPUS
    ]
    legacy_store = store_mod.LocalContextStore(vector_db="hybrid_bm25")
    legacy_store.add_events(sorted(events, key=lambda e: e.timestamp))
    legacy = retriever_mod.HybridRetriever(legacy_store, top_k=6, time_margin_minutes=8, search_k=60)
    alert = models.AlertCandidate(
        "alert-x", "w1", {"start": "2022-08-22T04:00:00Z", "end": "2022-08-22T04:01:00Z"}, POD, "cartservice",
        0.97, {"latency": 2.5, "cpu": 0.1}, "anomaly", ["latency"], "true_alert", "network_delay",
    )
    legacy_contexts, _ = legacy.retrieve(alert)

    candidate = _gd1_alert({**alert.__dict__, "alert_id": "alert-x", "service_id": "cartservice", "node_id": POD})
    ours = Bm25HybridRetriever(
        InMemoryEvidenceStore(CORPUS), pool="global", extra_query_terms=lambda c: ["anomaly", "network_delay"]
    ).retrieve(candidate, RetrievalBudget())
    assert [e.event_id for e in ours.events] == [c["doc_id"] for c in legacy_contexts]
    assert [round(e.score, 4) for e in ours.events] == [c["score"] for c in legacy_contexts]


def test_global_pool_reproduces_gd1_paper_500_top6():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    alerts = {case["alert"]["alert_id"]: case["alert"] for case in cases}
    retriever = Bm25HybridRetriever(
        load_gd1_corpus(LEGACY / "nezha_setup" / "processed" / "logs.jsonl"),
        pool="global",
        extra_query_terms=lambda c: [alerts[c.candidate_id]["detector_label"], alerts[c.candidate_id]["fault_type"]],
    )
    for case in cases:
        result = retriever.retrieve(_gd1_alert(case["alert"]), RetrievalBudget())
        assert [e.event_id for e in result.events] == [c["doc_id"] for c in case["contexts"]]


def test_registry_builds_bm25_and_budget():
    strategy = build_strategy({"type": "bm25_hybrid", "params": {"search_k": 30}}, InMemoryEvidenceStore([]))
    assert strategy.name == "bm25_hybrid"
    assert build_budget({"type": "bm25_hybrid", "top_k": 4}) == RetrievalBudget(top_k=4)
    with pytest.raises(ValueError):
        build_strategy({"type": "cross_modal"}, InMemoryEvidenceStore([]))
