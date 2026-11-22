"""services/rca_agent/propagation.py: backward 1-hop ranking and the anomaly-score baseline (M9)."""

from __future__ import annotations

import networkx as nx

from packages.graph.service_graph import ServiceGraph
from services.rca_agent.propagation import backward_one_hop, propagation_path, rank_by_anomaly_score


def _graph() -> ServiceGraph:
    directed = nx.DiGraph()
    directed.add_edge("frontend", "cart", weight=3)
    directed.add_edge("frontend", "checkout", weight=3)
    directed.add_edge("checkout", "cart", weight=3)
    directed.add_edge("cart", "redis", weight=2)
    directed.add_node("payment")
    return ServiceGraph(directed)


def test_single_alerted_service_blames_itself() -> None:
    ranked = backward_one_hop(["frontend"], _graph(), {"frontend": 0.7})
    assert [(r.service, r.score, r.alerted) for r in ranked] == [("frontend", 1.0, True)]


def test_blame_moves_one_hop_down_the_call_direction() -> None:
    # frontend -> cart and both alerted: cart is the deepest abnormal service
    ranked = backward_one_hop(["frontend", "cart"], _graph(), {"frontend": 0.99, "cart": 0.2})
    assert [r.service for r in ranked] == ["cart", "frontend"]
    assert ranked[0].score == 1.0 and ranked[0].blamed_by == ("cart", "frontend")
    assert ranked[1].score == 0.0  # explained by its callee, kept for Hit@3
    assert propagation_path(ranked, _graph()) == ["cart", "frontend"]


def test_chain_of_three_points_to_the_deepest() -> None:
    ranked = backward_one_hop(["frontend", "checkout", "cart"], _graph(), {})
    # frontend splits its vote between checkout and cart, checkout votes cart, cart votes itself
    assert [(r.service, round(r.score, 4)) for r in ranked] == [("cart", 0.8333), ("checkout", 0.1667), ("frontend", 0.0)]


def test_abnormal_callee_that_is_not_alerted_only_counts_when_passed_in() -> None:
    alert_only = backward_one_hop(["frontend"], _graph(), {"frontend": 0.5, "cart": 0.9})
    assert [r.service for r in alert_only] == ["frontend"]
    with_sign = backward_one_hop(["frontend"], _graph(), {"frontend": 0.5, "cart": 0.9}, abnormal=["cart"])
    assert [(r.service, r.alerted) for r in with_sign] == [("cart", False), ("frontend", True)]


def test_ranking_does_not_depend_on_alert_counts_and_ties_use_anomaly_score() -> None:
    # two unrelated alerted services: equal votes, the higher anomaly score first, then name
    ranked = backward_one_hop(["payment", "redis"], _graph(), {"payment": 0.4, "redis": 0.6})
    assert [r.service for r in ranked] == ["redis", "payment"]
    assert [r.score for r in ranked] == [0.5, 0.5]
    tied = backward_one_hop(["payment", "redis"], _graph(), {})
    assert [r.service for r in tied] == ["payment", "redis"]


def test_service_missing_from_the_graph_and_empty_incident() -> None:
    assert [r.service for r in backward_one_hop(["ghost"], _graph(), {})] == ["ghost"]
    assert backward_one_hop([], _graph(), {}) == []
    assert propagation_path([], _graph()) == []


def test_baseline_ranks_by_highest_anomaly_score() -> None:
    assert rank_by_anomaly_score({"a": 0.2, "b": 0.9, "c": 0.9}) == ["b", "c", "a"]
