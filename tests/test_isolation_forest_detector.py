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
from services.detector.isolation_forest import IsolationForestDetector, _percentile, _vectorize


def _window(service: str, ts: datetime, cpu: float, mem: float, window_id: str | None = None) -> TelemetryWindow:
    return TelemetryWindow(
        window_id=window_id or f"{service}-{ts.isoformat()}",
        service=service,
        start_ts=ts,
        end_ts=ts + timedelta(seconds=60),
        metrics=[MetricPoint(name="cpu", value=cpu, ts=ts), MetricPoint(name="mem", value=mem, ts=ts)],
    )


def _normal_windows(service: str, count: int, seed_offset: int = 0) -> list[TelemetryWindow]:
    base = datetime(2023, 1, 1, tzinfo=UTC)
    windows = []
    for i in range(count):
        ts = base + timedelta(minutes=i)
        cpu = 10.0 + (i % 3) * 0.1
        mem = 500.0 + (i % 5) * 0.5
        windows.append(_window(service, ts, cpu, mem, window_id=f"{service}-{seed_offset + i}"))
    return windows


class TestVectorize:
    def test_single_point_degenerates_to_zero_spread(self):
        vector = _vectorize([{"cpu": 5.0}], ["cpu"])
        assert vector == [5.0, 0.0, 5.0, 5.0, 5.0, 0.0]  # mean, std, min, max, last, delta

    def test_two_points_matches_hand_computed_stats(self):
        vector = _vectorize([{"cpu": 4.0}, {"cpu": 6.0}], ["cpu"])
        assert vector == pytest.approx([5.0, 1.0, 4.0, 6.0, 6.0, 2.0])

    def test_missing_metric_treated_as_zero(self):
        vector = _vectorize([{"cpu": 4.0}], ["cpu", "mem"])
        assert vector == [4.0, 0.0, 4.0, 4.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


class TestPercentile:
    def test_empty_reference_is_zero(self):
        assert _percentile(1.0, []) == 0.0

    def test_fraction_at_or_below(self):
        reference = sorted([0.0, 1.0, 2.0, 3.0, 4.0])
        assert _percentile(2.0, reference) == 3 / 5


class TestIsolationForestDetector:
    def test_fit_requires_min_windows(self):
        detector = IsolationForestDetector(min_fit_windows=20)
        with pytest.raises(ValueError):
            detector.fit(_normal_windows("checkout", 5))

    def test_score_before_fit_raises(self):
        detector = IsolationForestDetector()
        window = _normal_windows("checkout", 1)[0]
        with pytest.raises(RuntimeError):
            detector.score(window)

    def test_anomalous_window_scores_higher_than_normal(self):
        detector = IsolationForestDetector(min_fit_windows=20)
        detector.fit(_normal_windows("checkout", 40))

        # Warm the rolling buffer up to buffer_size=2 with normal data first, so
        # both scores below start from an equally full buffer -- otherwise the
        # comparison would confound "buffer just started" (see
        # test_cold_start_first_point_can_look_unusual) with an actual spike.
        base = datetime(2023, 1, 1, tzinfo=UTC) + timedelta(minutes=100)
        detector.score(_window("checkout", base, 10.0, 500.0))
        normal_score = detector.score(_window("checkout", base + timedelta(minutes=1), 10.1, 502.0))
        anomaly_score = detector.score(_window("checkout", base + timedelta(minutes=2), 500.0, 50000.0))
        assert anomaly_score > normal_score

    def test_cold_start_first_point_can_look_unusual(self):
        # Documents a real property of the buffer_size>1 design (QD-009): a
        # service's very first scored window has a single-point history, whose
        # degenerate std=0/delta=0 features can look structurally different
        # from the mostly-2-point training population, regardless of the
        # metric values themselves. Not a bug -- callers should expect the
        # first window per service after a cold start to be less reliable.
        detector = IsolationForestDetector(min_fit_windows=20)
        detector.fit(_normal_windows("checkout", 40))
        base = datetime(2023, 1, 1, tzinfo=UTC) + timedelta(minutes=100)
        score = detector.score(_window("checkout", base, 10.0, 500.0))
        assert 0.0 <= score <= 1.0

    def test_score_is_deterministic_given_fixed_random_state(self):
        training = _normal_windows("checkout", 40)
        probe = _window("checkout", datetime(2023, 1, 1, tzinfo=UTC) + timedelta(minutes=200), 300.0, 9000.0)

        first = IsolationForestDetector(min_fit_windows=20, random_state=7)
        first.fit(list(training))
        score_a = first.score(probe)

        second = IsolationForestDetector(min_fit_windows=20, random_state=7)
        second.fit(list(training))
        score_b = second.score(probe)

        assert score_a == score_b

    def test_is_candidate_applies_threshold(self):
        # buffer_size=1 sidesteps the cold-start guard below, isolating the
        # threshold comparison itself.
        detector = IsolationForestDetector(threshold=0.5, min_fit_windows=20, buffer_size=1)
        detector.fit(_normal_windows("checkout", 20))
        window = _normal_windows("checkout", 1)[0]
        detector.score(window)
        assert detector.is_candidate(window, 0.5) is True
        assert detector.is_candidate(window, 0.49) is False

    def test_is_candidate_false_during_cold_start_even_if_score_is_high(self):
        detector = IsolationForestDetector(min_fit_windows=20, threshold=0.0, buffer_size=2)
        detector.fit(_normal_windows("checkout", 40))
        base = datetime(2023, 1, 1, tzinfo=UTC) + timedelta(minutes=100)
        window = _window("checkout", base, 10.0, 500.0)
        score = detector.score(window)  # first point for this service: buffer not yet full
        assert detector.is_candidate(window, score) is False

    def test_rolling_buffer_is_per_service(self):
        detector = IsolationForestDetector(min_fit_windows=20, buffer_size=2)
        detector.fit(_normal_windows("checkout", 20) + _normal_windows("payment", 20, seed_offset=1000))
        base = datetime(2023, 1, 1, tzinfo=UTC) + timedelta(minutes=100)
        detector.score(_window("checkout", base, 999.0, 999.0))
        # payment's buffer must be independent of checkout's -- this must not raise
        detector.score(_window("payment", base, 10.0, 500.0))


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
        assert first.candidate_id == second.candidate_id
