"""Regression test for the NaN-latency bug found while building Week 2's
detector (docs/experiment-log.md QD-009): PodClientLatencyP90/95/99(s) and
PodServerLatencyP90/95/99(s) hold the literal string "NaN" for windows with
zero requests (undefined percentile, not zero latency) -- affects 28.6% of
the corpus. packages.schemas.loaders must drop those values rather than
pass float("nan")/float("inf") through, which broke IsolationForestDetector
(statistics.pstdev raises ValueError on non-finite input).
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.schemas.loaders import _row_to_window
from scripts.nezha_windows import DEFAULT_TIME_SOURCE


def _row(**overrides: str) -> dict[str, str]:
    base = {
        "Time": "2022-08-22 03:51:19",
        "PodName": "checkoutservice-578fcf4766-9csqn",
        "CpuUsage(m)": "12.5",
    }
    base.update(overrides)
    return base


def test_nan_string_metric_is_dropped_not_parsed():
    window = _row_to_window(
        _row(**{"PodClientLatencyP95(s)": "NaN"}),
        day="2022-08-22",
        known={},
        day_injections=(),
        time_source=DEFAULT_TIME_SOURCE,
        metric_names=["CpuUsage(m)", "PodClientLatencyP95(s)"],
        before_after=(60, 360),
    )
    assert window is not None
    names = {point.name for point in window.metrics}
    assert "PodClientLatencyP95(s)" not in names
    assert "CpuUsage(m)" in names


def test_finite_metric_value_is_kept():
    window = _row_to_window(
        _row(),
        day="2022-08-22",
        known={},
        day_injections=(),
        time_source=DEFAULT_TIME_SOURCE,
        metric_names=["CpuUsage(m)"],
        before_after=(60, 360),
    )
    assert window is not None
    assert window.metrics[0].name == "CpuUsage(m)"
    assert window.metrics[0].value == 12.5
    assert window.start_ts == datetime(2022, 8, 22, 3, 51, 19, tzinfo=UTC)


def test_empty_metric_value_is_skipped():
    window = _row_to_window(
        _row(**{"CpuUsage(m)": ""}),
        day="2022-08-22",
        known={},
        day_injections=(),
        time_source=DEFAULT_TIME_SOURCE,
        metric_names=["CpuUsage(m)"],
        before_after=(60, 360),
    )
    assert window is not None
    assert window.metrics == []


def test_window_carries_pod_name():
    # QD-015: rolling buffers and ground truth are per pod.
    window = _row_to_window(
        _row(),
        day="2022-08-22",
        known={},
        day_injections=(),
        time_source=DEFAULT_TIME_SOURCE,
        metric_names=["CpuUsage(m)"],
        before_after=(60, 360),
    )
    assert window is not None
    assert window.pod == "checkoutservice-578fcf4766-9csqn"
