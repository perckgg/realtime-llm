"""Rescue Score, C5 (M7, QD-033): pure components, grid, runner rescue list, plan masks."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from services.detector.rescue import (
    Alert,
    ErrorLogRule,
    RescueParams,
    active_alerts,
    delta_time,
    eta_grid,
    is_rescued,
    lambda_log,
    phi_topo,
    rescue_score,
)

T0 = datetime(2023, 1, 1, 12, 0, 0)


def test_lambda_log_saturates_and_is_zero_without_errors():
    assert lambda_log(0, 10) == 0.0
    assert lambda_log(10, 10) == pytest.approx(1 - math.exp(-1))
    assert lambda_log(1000, 10) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        lambda_log(1, 0)


def test_error_log_rule_levels_and_patterns():
    rule = ErrorLogRule.from_config({"levels": ["error"], "patterns": [r"\b(?:status|code)\D{0,5}5\d\d\b"]})
    assert rule.matches("ERROR", "anything")
    assert rule.matches("info", "upstream returned status: 503")
    assert not rule.matches("info", "status 200 ok")


def test_active_alerts_is_causal_and_bounded():
    alerts = [Alert(T0 - timedelta(seconds=400), "a"), Alert(T0 - timedelta(seconds=100), "b"),
              Alert(T0, "c"), Alert(T0 + timedelta(seconds=1), "future")]
    assert [a.service for a in active_alerts(alerts, T0, 300)] == ["b", "c"]


def test_phi_topo_uses_nearest_reachable_alerted_service():
    distances = {("x", "a"): 2, ("x", "b"): 1}
    alerts = [Alert(T0, "a"), Alert(T0, "b"), Alert(T0, "unreachable")]
    assert phi_topo("x", alerts, lambda s, t: distances.get((s, t))) == pytest.approx(0.5)
    assert phi_topo("x", [Alert(T0, "unreachable")], lambda s, t: None) == 0.0
    assert phi_topo("x", [], lambda s, t: 0) == 0.0


def test_delta_time_takes_the_closest_alert():
    alerts = [Alert(T0 - timedelta(seconds=300), "a"), Alert(T0 - timedelta(seconds=60), "b")]
    assert delta_time(T0, alerts, 300) == pytest.approx(math.exp(-60 / 300))
    assert delta_time(T0, [], 300) == 0.0


def test_eta_grid_is_the_simplex_and_params_are_validated():
    grid = eta_grid(0.2)
    assert len(grid) == 21  # 02 SS6.1: 21 x 7 tau = 147
    assert all(math.isclose(sum(e), 1.0) and min(e) >= 0 for e in grid)
    with pytest.raises(ValueError):
        RescueParams(0.5, 0.6, 0.0, 0.5)
    with pytest.raises(ValueError):
        eta_grid(0.3)


def test_rescue_never_touches_detector_promoted_windows():
    p = RescueParams(0.0, 0.5, 0.5, 0.5)
    score = rescue_score({"lambda_log": 0.0, "phi_topo": 1.0, "delta_time": 0.2}, p)
    assert score == pytest.approx(0.6)
    assert is_rescued(False, score, p)
    assert not is_rescued(True, score, p)
    assert not is_rescued(False, 0.49, p)


def test_rescued_masks_match_the_scalar_definition():
    from eval.harness.rescue import grid_points, point_name, rescued_masks

    rng = np.random.default_rng(0)
    frame = pd.DataFrame({
        "is_candidate": rng.integers(0, 2, 50),
        "lambda_log": rng.random(50), "phi_topo": rng.random(50), "delta_time": rng.random(50),
    })
    points = grid_points({"eta_step": 0.5, "tau": [0.3, 0.7]})
    masks = rescued_masks(frame, points)
    for p in points:
        expected = [is_rescued(bool(r.is_candidate), rescue_score(r._asdict(), p), p) for r in frame.itertuples()]
        assert masks[point_name(p)].tolist() == expected


def test_runner_reads_the_rescue_window_list(tmp_path: Path):
    from eval.harness.runner import _rescue_windows

    path = tmp_path / "rescue_windows.csv"
    path.write_text("window_id,lambda_log,phi_topo,delta_time\nw1,0.0,0.5,0.9\n", encoding="utf-8")
    assert _rescue_windows({}) is None
    rescue = _rescue_windows({"rescue": {"windows": str(path)}})
    assert rescue is not None and set(rescue) == {"w1"}
    assert rescue["w1"]["phi_topo"] == pytest.approx(0.5)
