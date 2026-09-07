"""IsolationForestDetector -- the GD2 `Detector` (01-architecture-design.md
SS5.2, SS6.2).

Ports legacy/src/detectors/isolation_forest_detector.py's feature engineering
(mean/std/min/max/last/delta per metric) and percentile-normalized scoring,
per docs/Final_Thesis_Phase2/07-setup-guide.md SS8.1 ("boc, dung viet lai" --
wrap, don't rewrite).

One adaptation was required and is recorded in docs/experiment-log.md QD-009:
GD1's MetricWindow held several raw samples per window (window_size=120s over
a 60s-sampled metric -> ~2 points); GD2's TelemetryWindow (QD-003) is exactly
one 60s sample. To keep GD1's multi-point feature formulas meaningful without
rewriting them, this detector keeps a small rolling buffer of the most recent
samples per service and computes GD1's per-metric statistics over that
buffer instead of over a single window. A side effect: a service's very
first scored window has a single-point (degenerate std=0/delta=0) history
that looks structurally unlike the fitted population regardless of its
actual metric values, so `is_candidate` never promotes during that cold
start -- only once the buffer reaches `buffer_size` is a score trusted.

The Rescue Score gate (SS6.2's "else" branch) is NOT implemented here -- see
QD-009. It needs log data that packages.schemas.loaders does not populate yet
(TelemetryWindow.logs/spans are still empty lists there, by that module's own
design), and the roadmap places the Rescue Score ablation in Month 2 (Week
8), not Week 2. This detector therefore only ever emits
AlertCandidate(source="metric") (see services/detector/candidates.py).
"""

from __future__ import annotations

import statistics
from collections import deque
from collections.abc import Iterable
from typing import Any

from packages.schemas.models import TelemetryWindow


class _ServiceBuffer:
    """Rolling window of the most recent metric snapshots for one service."""

    def __init__(self, maxlen: int) -> None:
        self._points: deque[dict[str, float]] = deque(maxlen=maxlen)

    def push(self, metrics: dict[str, float]) -> list[dict[str, float]]:
        self._points.append(metrics)
        return list(self._points)

    def is_full(self) -> bool:
        return len(self._points) >= (self._points.maxlen or 0)


def _window_metrics(window: TelemetryWindow) -> dict[str, float]:
    return {point.name: point.value for point in window.metrics}


def _vectorize(history: list[dict[str, float]], feature_names: list[str]) -> list[float]:
    """GD1's per-metric mean/std/min/max/last/delta, over `history` (oldest
    first, 1..buffer_size points), restricted to `feature_names` (a metric
    missing from a snapshot -- e.g. a service whose metric set differs --
    is treated as 0.0)."""
    vector: list[float] = []
    for name in feature_names:
        values = [point.get(name, 0.0) for point in history]
        first, last = values[0], values[-1]
        vector.extend(
            [
                statistics.fmean(values),
                statistics.pstdev(values) if len(values) > 1 else 0.0,
                min(values),
                max(values),
                last,
                last - first,
            ]
        )
    return vector


class IsolationForestDetector:
    """Detector protocol (01-architecture-design.md SS5.2): threshold 0.85."""

    name = "isolation_forest"

    def __init__(
        self,
        threshold: float = 0.85,
        buffer_size: int = 2,  # ~120s of history at Nezha's 60s sampling, matching GD1's window_size=120s
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
        max_samples: str | int | float = "auto",
        min_fit_windows: int = 20,
    ) -> None:
        self.threshold = threshold
        self.buffer_size = buffer_size
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.max_samples = max_samples
        self.min_fit_windows = min_fit_windows

        self._model: Any | None = None
        self._feature_names: list[str] = []
        self._train_scores: list[float] = []
        self._buffers: dict[str, _ServiceBuffer] = {}

    def fit(self, windows: Iterable[TelemetryWindow]) -> None:
        """Fit on `windows`, replaying each service's rolling buffer in time
        order (QD-009) so the training feature distribution matches what
        `score()` sees at serve time. Does not affect the live buffers used
        by `score()` -- those start fresh and empty after `fit()` returns,
        matching the no-future-leakage discipline the streaming replayer
        already follows.
        """
        ordered = sorted(windows, key=lambda window: (window.start_ts, window.window_id))
        if len(ordered) < self.min_fit_windows:
            raise ValueError(
                f"IsolationForestDetector needs at least {self.min_fit_windows} windows to fit; got {len(ordered)}."
            )

        self._feature_names = sorted({point.name for window in ordered for point in window.metrics})

        fit_buffers: dict[str, _ServiceBuffer] = {}
        vectors: list[list[float]] = []
        for window in ordered:
            buffer = fit_buffers.setdefault(window.service, _ServiceBuffer(self.buffer_size))
            history = buffer.push(_window_metrics(window))
            vectors.append(_vectorize(history, self._feature_names))

        from sklearn.ensemble import IsolationForest

        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            max_samples=self.max_samples,
        )
        self._model.fit(vectors)
        self._train_scores = sorted(-float(s) for s in self._model.score_samples(vectors))
        self._buffers = {}

    def score(self, window: TelemetryWindow) -> float:
        """Anomaly score normalized to [0, 1] (01-architecture-design.md
        SS5.2): the fraction of training scores at or below this window's
        raw score."""
        if self._model is None:
            raise RuntimeError("IsolationForestDetector must be fitted before scoring.")
        buffer = self._buffers.setdefault(window.service, _ServiceBuffer(self.buffer_size))
        history = buffer.push(_window_metrics(window))
        vector = _vectorize(history, self._feature_names)
        raw_score = -float(self._model.score_samples([vector])[0])
        return round(_percentile(raw_score, self._train_scores), 4)

    def is_candidate(self, window: TelemetryWindow, score: float) -> bool:
        """Never promotes during a service's cold start (its rolling buffer
        not yet at `buffer_size`): the score is still logged for that window,
        but its single-point history is structurally unlike the mostly-full
        training vectors (see tests/test_isolation_forest_detector.py's
        test_cold_start_first_point_can_look_unusual), so it is not a
        trustworthy anomaly signal yet.
        """
        buffer = self._buffers.get(window.service)
        if buffer is None or not buffer.is_full():
            return False
        return score >= self.threshold


def _percentile(raw_score: float, reference: list[float]) -> float:
    if not reference:
        return 0.0
    lower_or_equal = 0
    for value in reference:
        if value <= raw_score:
            lower_or_equal += 1
        else:
            break
    return lower_or_equal / len(reference)
