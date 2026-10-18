"""Unit tests for services.detector.isolation_forest (rule R-E1,
docs/Final_Thesis_Phase2/05-agent-coding-rules.md: calculation code needs
unit tests). Pure synthetic TelemetryWindow objects -- no Nezha dataset
needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from packages.schemas.models import MetricPoint, TelemetryWindow
from services.detector.candidates import build_alert_candidate
from services.detector.isolation_forest import (
    IsolationForestDetector,
    _KeyBuffer,
    _percentile,
    _vectorize,
)

BASE = datetime(2023, 1, 1, tzinfo=UTC)


def _window(
    service: str,
    ts: datetime,
    cpu: float | None,
    mem: float | None,
    window_id: str | None = None,
    pod: str | None = None,
) -> TelemetryWindow:
    metrics = []
    if cpu is not None:
        metrics.append(MetricPoint(name="cpu", value=cpu, ts=ts))
    if mem is not None:
        metrics.append(MetricPoint(name="mem", value=mem, ts=ts))
    return TelemetryWindow(
        window_id=window_id or f"{pod or service}-{ts.isoformat()}",
        service=service,
        pod=pod,
        start_ts=ts,
        end_ts=ts + timedelta(seconds=60),
        metrics=metrics,
    )


def _normal_windows(service: str, count: int, seed_offset: int = 0, pod: str | None = None) -> list[TelemetryWindow]:
    windows = []
    for i in range(count):
        ts = BASE + timedelta(minutes=i)
        cpu = 10.0 + (i % 3) * 0.1
        mem = 500.0 + (i % 5) * 0.5
        windows.append(_window(service, ts, cpu, mem, window_id=f"{service}-{seed_offset + i}", pod=pod))
    return windows


def _point(values: dict[str, float], missing: dict[str, bool] | None = None) -> tuple[dict[str, float], dict[str, bool]]:
    return values, missing or dict.fromkeys(values, False)


class TestVectorize:
    def test_single_point_degenerates_to_zero_spread(self):
        vector = _vectorize([_point({"cpu": 5.0})], ["cpu"])
        assert vector == [5.0, 0.0, 5.0, 5.0, 5.0, 0.0, 0.0]  # mean, std, min, max, last, delta, missing_fraction

    def test_two_points_matches_hand_computed_stats(self):
        vector = _vectorize([_point({"cpu": 4.0}), _point({"cpu": 6.0})], ["cpu"])
        assert vector == pytest.approx([5.0, 1.0, 4.0, 6.0, 6.0, 2.0, 0.0])

    def test_missing_fraction_counts_filled_points(self):
        history = [_point({"cpu": 4.0}, {"cpu": True}), _point({"cpu": 4.0}, {"cpu": False})]
        assert _vectorize(history, ["cpu"])[-1] == 0.5


class TestKeyBufferFilling:
    """QD-015 (D1): a missing metric is never read as 0.0."""

    def test_missing_metric_is_forward_filled_from_last_observation(self):
        buffer = _KeyBuffer(maxlen=2)
        buffer.push(_window("svc", BASE, 7.0, 100.0, window_id="w1"), ["cpu", "mem"], {"cpu": 1.0, "mem": 1.0})
        history = buffer.push(
            _window("svc", BASE + timedelta(minutes=1), 8.0, None, window_id="w2"), ["cpu", "mem"], {"cpu": 1.0, "mem": 1.0}
        )
        values, missing = history[-1]
        assert values == {"cpu": 8.0, "mem": 100.0}
        assert missing == {"cpu": False, "mem": True}

    def test_never_observed_metric_uses_training_default(self):
        buffer = _KeyBuffer(maxlen=2)
        history = buffer.push(_window("svc", BASE, 7.0, None, window_id="w1"), ["cpu", "mem"], {"cpu": 1.0, "mem": 42.0})
        assert history[-1][0]["mem"] == 42.0
        assert history[-1][1]["mem"] is True

    def test_push_is_idempotent_per_window_id(self):
        buffer = _KeyBuffer(maxlen=2)
        window = _window("svc", BASE, 7.0, 100.0, window_id="w1")
        buffer.push(window, ["cpu", "mem"], {})
        history = buffer.push(window, ["cpu", "mem"], {})
        assert len(history) == 1


class TestPercentile:
    def test_empty_reference_is_zero(self):
        assert _percentile(1.0, []) == 0.0

    def test_fraction_at_or_below(self):
        reference = sorted([0.0, 1.0, 2.0, 3.0, 4.0])
        assert _percentile(2.0, reference) == 3 / 5

    def test_ties_count_as_at_or_below(self):
        assert _percentile(1.0, [1.0, 1.0, 2.0]) == 2 / 3


class TestIsolationForestDetector:
    def test_fit_requires_min_windows(self):
        detector = IsolationForestDetector(min_fit_windows=20)
        with pytest.raises(ValueError):
            detector.fit(_normal_windows("checkout", 5))

    def test_fit_counts_only_training_windows(self):
        windows = _normal_windows("checkout", 40)
        train_ids = {w.window_id for w in windows[:10]}
        with pytest.raises(ValueError):
            IsolationForestDetector(min_fit_windows=20).fit(windows, train_ids=train_ids)

    def test_score_before_fit_raises(self):
        detector = IsolationForestDetector()
        window = _normal_windows("checkout", 1)[0]
        with pytest.raises(RuntimeError):
            detector.score(window)

    def test_anomalous_window_scores_higher_than_normal(self):
        detector = IsolationForestDetector(min_fit_windows=20)
        detector.fit(_normal_windows("checkout", 40))

        # Warm the rolling buffer up to buffer_size=2 with normal data first, so
        # both scores below start from an equally full buffer.
        base = BASE + timedelta(minutes=100)
        detector.score(_window("checkout", base, 10.0, 500.0))
        normal_score = detector.score(_window("checkout", base + timedelta(minutes=1), 10.1, 502.0))
        anomaly_score = detector.score(_window("checkout", base + timedelta(minutes=2), 500.0, 50000.0))
        assert anomaly_score > normal_score

    def test_cold_start_first_point_can_look_unusual(self):
        # Documents a real property of the buffer_size>1 design (QD-009): a
        # key's very first scored window has a single-point history.
        detector = IsolationForestDetector(min_fit_windows=20)
        detector.fit(_normal_windows("checkout", 40))
        score = detector.score(_window("checkout", BASE + timedelta(minutes=100), 10.0, 500.0))
        assert 0.0 <= score <= 1.0

    def test_score_is_deterministic_given_fixed_random_state(self):
        training = _normal_windows("checkout", 40)
        probe = _window("checkout", BASE + timedelta(minutes=200), 300.0, 9000.0)

        first = IsolationForestDetector(min_fit_windows=20, random_state=7)
        first.fit(list(training))
        second = IsolationForestDetector(min_fit_windows=20, random_state=7)
        second.fit(list(training))

        assert first.score(probe) == second.score(probe)

    def test_score_twice_on_same_window_does_not_shift_history(self):
        # QD-015 (D3): scoring is idempotent per window_id.
        detector = IsolationForestDetector(min_fit_windows=20)
        detector.fit(_normal_windows("checkout", 40))
        base = BASE + timedelta(minutes=100)
        detector.score(_window("checkout", base, 10.0, 500.0, window_id="a"))
        probe = _window("checkout", base + timedelta(minutes=1), 300.0, 9000.0, window_id="b")
        assert detector.score(probe) == detector.score(probe)

    def test_is_candidate_applies_threshold(self):
        # buffer_size=1 sidesteps the cold-start guard, isolating the threshold comparison itself.
        detector = IsolationForestDetector(threshold=0.5, min_fit_windows=20, buffer_size=1)
        detector.fit(_normal_windows("checkout", 20))
        window = _normal_windows("checkout", 1)[0]
        detector.score(window)
        assert detector.is_candidate(window, 0.5) is True
        assert detector.is_candidate(window, 0.49) is False

    def test_is_candidate_false_during_cold_start_even_if_score_is_high(self):
        detector = IsolationForestDetector(min_fit_windows=20, threshold=0.0, buffer_size=2)
        detector.fit(_normal_windows("checkout", 40))
        window = _window("checkout", BASE + timedelta(minutes=100), 10.0, 500.0)
        score = detector.score(window)  # first point for this key: buffer not yet full
        assert detector.is_candidate(window, score) is False

    def test_observe_fills_history_so_next_window_is_not_cold(self):
        # QD-015 (D2): a context window outside the split warms the buffer.
        detector = IsolationForestDetector(min_fit_windows=20, threshold=0.0, buffer_size=2)
        detector.fit(_normal_windows("checkout", 40))
        base = BASE + timedelta(minutes=100)
        detector.observe(_window("checkout", base, 10.0, 500.0, window_id="context"))
        window = _window("checkout", base + timedelta(minutes=1), 10.0, 500.0, window_id="evaluated")
        assert detector.is_candidate(window, detector.score(window)) is True

    def test_is_candidate_false_for_window_that_was_not_last_pushed(self):
        detector = IsolationForestDetector(min_fit_windows=20, threshold=0.0, buffer_size=1)
        detector.fit(_normal_windows("checkout", 20))
        base = BASE + timedelta(minutes=100)
        stale = _window("checkout", base, 10.0, 500.0, window_id="stale")
        detector.score(stale)
        detector.score(_window("checkout", base + timedelta(minutes=1), 10.0, 500.0, window_id="newer"))
        assert detector.is_candidate(stale, 1.0) is False

    def test_rolling_buffer_is_per_pod(self):
        # QD-015 (D6): two pods of one service do not share a buffer.
        detector = IsolationForestDetector(min_fit_windows=20, threshold=0.0, buffer_size=2)
        detector.fit(_normal_windows("checkout", 40, pod="checkout-a"))
        base = BASE + timedelta(minutes=100)
        detector.score(_window("checkout", base, 10.0, 500.0, pod="checkout-a"))
        other_pod = _window("checkout", base, 10.0, 500.0, pod="checkout-b")
        assert detector.is_candidate(other_pod, detector.score(other_pod)) is False  # its own cold start

    def test_context_windows_shape_features_but_are_not_training_samples(self):
        windows = _normal_windows("checkout", 40)
        train_ids = {w.window_id for w in windows[::2]}
        detector = IsolationForestDetector(min_fit_windows=20)
        detector.fit(windows, train_ids=train_ids)
        assert len(detector._train_scores) == len(train_ids)


class TestBuildAlertCandidate:
    def test_returns_none_when_not_candidate(self):
        window = _normal_windows("checkout", 1)[0]
        assert build_alert_candidate(window, 0.1, False) is None

    def test_builds_metric_sourced_candidate(self):
        window = _normal_windows("checkout", 1)[0]
        candidate = build_alert_candidate(window, 0.9, True)
        assert candidate is not None
        assert candidate.source == "metric"
        assert candidate.window_id == window.window_id
        assert candidate.candidate_id == f"cand-{window.window_id}"

    def test_candidate_id_is_deterministic(self):
        window = _normal_windows("checkout", 1)[0]
        first = build_alert_candidate(window, 0.9, True)
        second = build_alert_candidate(window, 0.9, True)
        assert first is not None and second is not None
        assert first.candidate_id == second.candidate_id
