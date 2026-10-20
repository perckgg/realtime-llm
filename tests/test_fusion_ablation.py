"""Fusion-weight ablation (QD-025): grid construction and the V22 (a) metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eval.harness.fusion_ablation import GridPoint, TopK, WindowInfo, build_grid, concurrent_faults, summarize

T = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)
T2 = datetime(2022, 8, 22, 4, 1, tzinfo=UTC)


def test_build_grid_simplex_extra_points_and_k():
    points = build_grid({"grid_step": 0.25, "extra_points": [[0.35, 0.25, 0.40], [0.5, 0.25, 0.25]], "k_graph": [0, 1]})
    weights = {(p.alpha, p.beta, p.gamma) for p in points}
    assert len(points) == 2 * 16  # 15 simplex points + paper; (0.5, 0.25, 0.25) already on the grid
    assert {(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.35, 0.25, 0.40)} <= weights
    assert all(abs(p.alpha + p.beta + p.gamma - 1) < 1e-9 for p in points)
    with pytest.raises(ValueError):
        build_grid({"grid_step": 0.3})


def test_summarize_neighbour_share_and_concurrent_root():
    infos = [
        WindowInfo("w1", "cart", T, True, "cart", True),  # fault at cart
        WindowInfo("w2", "frontend", T, False, "", True),  # concurrent with the cart fault
        WindowInfo("w3", "ads", T2, False, "", True),  # nothing concurrent
        WindowInfo("w4", "redis", T, False, "", False),  # no telemetry: excluded
    ]
    point = GridPoint(0.35, 0.25, 0.40, 1)
    topk = [
        [TopK(("cart", "cart", "redis"), ("local", "local", "graph"))],
        [TopK(("frontend", "cart"), ("local", "graph"))],
        [TopK(("ads", "frontend", "frontend"), ("local", "graph", "graph"))],
        [TopK(("cart",), ("graph",))],
    ]
    entry = summarize([point], infos, topk, concurrent_faults(infos))[0]
    assert entry["fault"] == {"n": 1, "empty_retrieval": 0, "with_graph_evidence": 1, "graph_share_mean": 1 / 3}
    assert entry["nonfault"]["n"] == 2 and entry["nonfault"]["with_graph_evidence"] == 2
    assert entry["nonfault"]["graph_share_mean"] == pytest.approx((1 / 2 + 2 / 3) / 2)
    assert entry["root_hit_sanity"] == {"n": 1, "hits": 1}
    assert entry["concurrent_root"]["n"] == 1 and entry["concurrent_root"]["hits"] == 1
