"""V18 (QD-024): root-hit criterion and k_graph choice rule."""

from __future__ import annotations

import pytest

from eval.harness.kgraph import RootHit, choose_k, root_hits


def _rows(hits: list[tuple[str, str, bool]]) -> list[RootHit]:
    return [RootHit(f"w{i}", s0, root, hit, 6, 0) for i, (s0, root, hit) in enumerate(hits)]


def test_root_hits_keeps_fault_windows_with_telemetry_and_retrieval():
    per_window = [
        {"window_id": "a", "service": "cart", "label_is_fault": "1", "has_telemetry": "1", "label_root_cause": "redis"},
        {"window_id": "b", "service": "cart", "label_is_fault": "0", "has_telemetry": "1", "label_root_cause": ""},
        {"window_id": "c", "service": "cart", "label_is_fault": "1", "has_telemetry": "0", "label_root_cause": "cart"},
        {"window_id": "d", "service": "cart", "label_is_fault": "1", "has_telemetry": "1", "label_root_cause": "cart"},
        {"window_id": "e", "service": "cart", "label_is_fault": "1", "has_telemetry": "1", "label_root_cause": "cart"},
    ]
    retrieval = [
        {"window_id": "a", "events": [{"service": "cart", "origin": "local"}, {"service": "redis", "origin": "graph"}]},
        {"window_id": "d", "events": [{"service": "frontend", "origin": "graph"}]},
        {"window_id": "c", "events": []},
    ]  # "e" never reached retrieval
    rows = root_hits(per_window, retrieval)
    assert [(r.window_id, r.hit, r.n_graph, r.s0_is_root) for r in rows] == [("a", True, 1, False), ("d", False, 1, True)]


def test_choose_k_prefers_more_hits_then_smaller_k_and_enforces_local_floor():
    k0 = _rows([("cart", "cart", True), ("cart", "cart", True), ("cart", "redis", False), ("cart", "ads", False)])
    k1 = _rows([("cart", "cart", True), ("cart", "cart", True), ("cart", "redis", True), ("cart", "ads", False)])
    k2 = _rows([("cart", "cart", True), ("cart", "cart", True), ("cart", "redis", True), ("cart", "ads", False)])
    k3 = _rows([("cart", "cart", True), ("cart", "cart", False), ("cart", "redis", True), ("cart", "ads", True)])
    result = choose_k({0: k0, 1: k1, 2: k2, 3: k3})
    assert result["local_floor_hits"] == 2
    assert result["by_k"][3]["passes_local_constraint"] is False  # more hits overall, but loses a local one
    assert result["chosen_k_graph"] == 1  # k1 and k2 tie -> smallest
    assert result["by_k"][1]["s0_not_root"] == {"n": 2, "hits": 1, "hit_rate": 0.5}


def test_choose_k_needs_reference_and_same_windows():
    rows = _rows([("cart", "cart", True)])
    with pytest.raises(ValueError):
        choose_k({1: rows})
    with pytest.raises(ValueError):
        choose_k({0: rows, 1: _rows([("cart", "cart", True), ("cart", "x", True)])})
