"""C1 `hybrid_bm25_graph` and packages.graph: Fusion Score, origin (V14), time
bounding (V13), parity with GD1's TopologyAwareRetriever and the paper's prompts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import networkx as nx
import pytest

from packages.graph.service_graph import ServiceGraph, load_gd1_graph, load_graph
from packages.schemas.evidence import (
    EvidenceDoc,
    InMemoryEvidenceStore,
    load_gd1_corpus,
    parse_timestamp,
)
from packages.schemas.models import AlertCandidate, RetrievalBudget
from services.judge.backends import PAPER_MODEL, GeminiBackend
from services.judge.cache import ResponseCache
from services.judge.prompt import alert_payload, compose_prompt, context_payload
from services.retrieval.hybrid_bm25_graph import HybridBm25GraphRetriever
from services.retrieval.registry import build_strategy
from tests.gd1 import LEGACY, gd1

FIXTURE = Path(__file__).parent / "fixtures" / "gd1_topology_cases.json"
GD1_GRAPH = LEGACY / "outputs/phase2/service_graph_directed.json"
GD1_CACHE = LEGACY / "outputs/phase2/step7_rerun/quality_full_budget/cache/paper_500/topology_aware_fusion_top6.jsonl"
T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)


def _graph() -> ServiceGraph:
    g = nx.DiGraph()
    g.add_edges_from([("frontend", "cart"), ("cart", "redis"), ("redis", "disk"), ("frontend", "ads")])
    g.add_node("lonely")
    return ServiceGraph(g)


def _doc(i: int, service: str, message: str, seconds: float) -> EvidenceDoc:
    return EvidenceDoc(f"d{i:02d}", T0 + timedelta(seconds=seconds), f"{service}-abc-x1", service, "INFO",
                       "application_log", "nezha_log", message)


CORPUS = [
    _doc(0, "cart", "cart GetCart timeout error", 10),
    _doc(1, "redis", "redis slow command", 20),
    _doc(2, "frontend", "request to cart failed", 30),
    _doc(3, "disk", "disk latency high", 15),  # 2 hops from cart
    _doc(4, "ads", "ads served", 25),  # 2 hops via frontend
    _doc(5, "cart", "cart GetCart timeout error", 3 * 3600),  # same text, 3 hours later
    _doc(6, "lonely", "cart cart cart", 12),  # unreachable service
]


def _candidate(service: str = "cart") -> AlertCandidate:
    return AlertCandidate(candidate_id="c1", window_id="w1", service=service, pod=f"{service}-abc-x1", ts=T0,
                          end_ts=T0 + timedelta(seconds=60), anomaly_score=0.9, source="metric")


def test_graph_distances_undirected_and_directed():
    graph = _graph()
    assert graph.distances("cart") == {"cart": 0, "frontend": 1, "redis": 1, "ads": 2, "disk": 2}
    assert graph.distances("cart", max_distance=1) == {"cart": 0, "frontend": 1, "redis": 1}
    assert graph.distances("cart", directed=True) == {"cart": 0, "redis": 1, "disk": 2}
    assert graph.distances("unknown") == {}


def test_committed_graph_equals_gd1_graph():
    ours, theirs = load_graph(), load_gd1_graph(GD1_GRAPH)
    assert set(ours.directed.nodes) == set(theirs.directed.nodes)
    edges = {(a, b): d["weight"] for a, b, d in ours.directed.edges(data=True)}
    assert edges == {(a, b): d["weight"] for a, b, d in theirs.directed.edges(data=True)}


def test_window_pool_is_time_bounded_and_origin_follows_distance():
    retriever = HybridBm25GraphRetriever(InMemoryEvidenceStore(CORPUS), graph=_graph())
    result = retriever.retrieve(_candidate(), RetrievalBudget(top_k=10))
    ids = [e.event_id for e in result.events]
    assert "d05" not in ids  # 3 hours away: outside +-8 min (V13)
    assert "d06" not in ids  # service outside 2 hops
    assert set(ids) == {"d00", "d01", "d02", "d03", "d04"}
    for event in result.events:
        assert event.origin == ("local" if event.service == "cart" else "graph")  # V14
        assert event.graph_distance == {"cart": 0, "redis": 1, "frontend": 1, "disk": 2, "ads": 2}[event.service]
        for key in ("bm25_norm", "time_sim", "graph_sim", "score_final", "source_flags", "prompt_score"):
            assert key in event.debug
    scores = [e.score for e in result.events]
    assert scores == sorted(scores, reverse=True)
    top = result.events[0].debug
    expected = 0.35 * top["bm25_norm"] + 0.25 * top["time_sim"] + 0.40 * top["graph_sim"]
    assert top["score_final"] == pytest.approx(expected)


def test_global_pool_reaches_any_time_like_the_paper():
    retriever = HybridBm25GraphRetriever(InMemoryEvidenceStore(CORPUS), graph=_graph(), bm25_pool="global")
    ids = [e.event_id for e in retriever.retrieve(_candidate(), RetrievalBudget(top_k=10)).events]
    assert "d05" in ids  # QD-020: the paper's lexical matches have no time limit
    assert "d06" in ids  # and may come from unreachable services (GraphSim 0)


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        HybridBm25GraphRetriever(InMemoryEvidenceStore([]), graph=_graph(), alpha=0.5, beta=0.5, gamma=0.5)


def test_global_pool_matches_gd1_topology_retriever_on_synthetic_corpus():
    models = gd1("src.models")
    store_mod = gd1("src.retrieval.context_store")
    topo = gd1("src.phase2.retrieval.topology_aware_retriever")
    expander = gd1("src.phase2.retrieval.topology_candidate_expander")
    events = [models.LogEvent(d.doc_id, d.ts, d.pod, d.service, d.pod, d.severity, d.event_type, d.message, d.source)
              for d in CORPUS]
    legacy_store = store_mod.LocalContextStore(vector_db="hybrid_bm25")
    legacy_store.add_events(sorted(events, key=lambda e: e.timestamp))
    adjacency: dict[str, dict[str, float]] = {n: {} for n in _graph().directed.nodes}
    for a, b in _graph().directed.edges:
        adjacency[a][b] = adjacency[b][a] = 1.0
    fusion = gd1("src.phase2.retrieval.fusion_ranker")
    # Paper configuration A4, as legacy/src/phase2/retrieval/pipeline_adapter.py passes it
    # (TopologyAwareRetriever's own default is 0.4 / 0.3 / 0.3).
    legacy = topo.TopologyAwareRetriever(legacy_store, expander.ServiceTopology(adjacency), top_k=6, bm25_k=60,
                                         time_margin_minutes=8, weights=fusion.FusionWeights(0.35, 0.25, 0.40))
    alert = models.AlertCandidate("alert-x", "w1", {"start": "2022-08-22T04:00:00Z", "end": "2022-08-22T04:01:00Z"},
                                  "cart-abc-x1", "cart", 0.97, {"latency": 2.5}, "anomaly", ["latency"], "true_alert",
                                  "network_delay")
    legacy_contexts, _ = legacy.retrieve(alert)
    ours = HybridBm25GraphRetriever(
        InMemoryEvidenceStore(CORPUS), graph=_graph(), bm25_pool="global",
        extra_query_terms=lambda c: ["anomaly", "network_delay"],
    ).retrieve(
        AlertCandidate(candidate_id="alert-x", window_id="w1", service="cart", pod="cart-abc-x1", ts=T0,
                       end_ts=T0 + timedelta(seconds=60), anomaly_score=0.97, source="metric",
                       metric_snapshot={"latency": 2.5}, top_features=["latency"]),
        RetrievalBudget(),
    )
    assert [e.event_id for e in ours.events] == [c["doc_id"] for c in legacy_contexts]
    assert [e.debug["prompt_score"] for e in ours.events] == [c["score"] for c in legacy_contexts]


def test_global_pool_reproduces_paper_topology_prompts_and_cache_keys():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    alerts = {case["alert"]["alert_id"]: case["alert"] for case in cases}
    retriever = HybridBm25GraphRetriever(
        load_gd1_corpus(LEGACY / "nezha_setup/processed/logs.jsonl"), graph=load_gd1_graph(GD1_GRAPH),
        bm25_pool="global",
        extra_query_terms=lambda c: [alerts[c.candidate_id]["detector_label"], alerts[c.candidate_id]["fault_type"]],
    )
    backend = GeminiBackend(ResponseCache(None, [GD1_CACHE]), model=PAPER_MODEL)
    for case in cases:
        a = case["alert"]
        candidate = AlertCandidate(
            candidate_id=a["alert_id"], window_id=a["window_id"], service=a["service_id"], pod=a["node_id"],
            ts=parse_timestamp(a["time_window"]["start"]), end_ts=parse_timestamp(a["time_window"]["end"]),
            anomaly_score=a["anomaly_score"], source="metric", metric_snapshot=a["metric_snapshot"],
            top_features=a["top_features"],
        )
        result = retriever.retrieve(candidate, RetrievalBudget())
        assert [e.event_id for e in result.events] == [c["doc_id"] for c in case["contexts"]]
        prompt = compose_prompt(alert_payload(candidate), [context_payload(e) for e in result.events])
        assert backend.cache_key(prompt) == case["cache_key"]
        assert backend.cache.get(case["cache_key"]) is not None


def test_registry_builds_c1():
    strategy = build_strategy({"type": "hybrid_bm25_graph", "params": {"bm25_pool": "window"}},
                              InMemoryEvidenceStore([]))
    assert strategy.name == "hybrid_bm25_graph"
