"""IsolationForestDetector -- the GD2 `Detector` (01-architecture-design.md
SS5.2, SS6.2).

Ports legacy/src/detectors/isolation_forest_detector.py's feature engineering
(mean/std/min/max/last/delta per metric) and percentile-normalized scoring,
per docs/Final_Thesis_Phase2/07-setup-guide.md SS8.1 ("boc, dung viet lai" --
wrap, don't rewrite).

Adaptations, each recorded in docs/experiment-log.md:

- QD-009: GD1's MetricWindow held several raw samples per window
  (window_size=120s over a 60s-sampled metric -> ~2 points); GD2's
  TelemetryWindow (QD-003) is exactly one 60s sample. The detector keeps a
  rolling buffer of the most recent samples and computes GD1's per-metric
  statistics over it. A key's first scored window has a single-point history,
  so `is_candidate` never promotes until the buffer reaches `buffer_size`.
- QD-015 (D1): a metric absent from a window (Nezha writes "NaN" latency
  percentiles for zero-request windows; the loader drops them) is filled
  with the key's last observed value, or the training median if the key has
  never reported it, and a per-metric missing-fraction feature is added --
  never 0.0, which would describe an idle window as a fast one.
- QD-015 (D2/D6): buffers are keyed by pod (falling back to service), and
  `fit()`/the replayer see the continuous history -- the split only decides
  which windows become training samples or get scored (`train_ids`,
  `observe()`).
- QD-015 (D3): pushing is idempotent per window_id, so calling `score()`
  twice on the same window does not corrupt the history.
- QD-017 (V9): `top_features(window)` reports the 3 metrics whose features
  deviate most from the training mean, in training standard deviations --
  GD1's `_top_contributing_features` -- so the judge prompt's
  `top_features` is not empty.

The Rescue Score gate (SS6.2's "else" branch) is NOT implemented here -- see
QD-009; it belongs to milestone M7. This detector therefore only ever emits
AlertCandidate(source="metric") (see services/detector/candidates.py).
"""

from __future__ import annotations

import statistics
from bisect import bisect_right
from collections import deque
from collections.abc import Iterable
from typing import Any

from packages.schemas.models import TelemetryWindow


class _KeyBuffer:
    """Rolling history of filled metric snapshots for one pod (or service)."""

    def __init__(self, maxlen: int) -> None:
        self._points: deque[tuple[str, dict[str, float], dict[str, bool]]] = deque(maxlen=maxlen)
        self._last_seen: dict[str, float] = {}

    def push(
        self,
        window: TelemetryWindow,
        feature_names: list[str],
        defaults: dict[str, float],
    ) -> list[tuple[dict[str, float], dict[str, bool]]]:
        """Append `window` (once per window_id) and return the history, oldest first."""
        if not self._points or self._points[-1][0] != window.window_id:
            observed = _window_metrics(window)
            values: dict[str, float] = {}
            missing: dict[str, bool] = {}
            for name in feature_names:
                if name in observed:
                    values[name] = observed[name]
                    self._last_seen[name] = observed[name]
                    missing[name] = False
                else:
                    values[name] = self._last_seen.get(name, defaults.get(name, 0.0))
                    missing[name] = True
            self._points.append((window.window_id, values, missing))
        return [(values, missing) for _, values, missing in self._points]

    def is_full(self) -> bool:
        return len(self._points) >= (self._points.maxlen or 0)

    def last_window_id(self) -> str | None:
        return self._points[-1][0] if self._points else None


def _window_metrics(window: TelemetryWindow) -> dict[str, float]:
    return {point.name: point.value for point in window.metrics}


def _buffer_key(window: TelemetryWindow) -> str:
    return window.pod or window.service


_FEATURES_PER_METRIC = 7  # mean, std, min, max, last, delta, missing_fraction


def _vectorize(history: list[tuple[dict[str, float], dict[str, bool]]], feature_names: list[str]) -> list[float]:
    """GD1's per-metric mean/std/min/max/last/delta over `history` (oldest
    first, 1..buffer_size filled points), plus the fraction of those points
    in which the metric was missing and had to be filled (QD-015)."""
    vector: list[float] = []
    for name in feature_names:
        values = [point[name] for point, _ in history]
        first, last = values[0], values[-1]
        missing_fraction = sum(1 for _, missing in history if missing[name]) / len(history)
        vector.extend(
            [
                statistics.fmean(values),
                statistics.pstdev(values) if len(values) > 1 else 0.0,
                min(values),
                max(values),
                last,
                last - first,
                missing_fraction,
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
        max_samples: str | float = "auto",
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
        self._defaults: dict[str, float] = {}
        self._train_scores: list[float] = []
        self._buffers: dict[str, _KeyBuffer] = {}
        self._center: list[float] = []
        self._scale: list[float] = []
        self._last_vector: dict[str, tuple[str, list[float]]] = {}

    def fit(self, windows: Iterable[TelemetryWindow], train_ids: set[str] | None = None) -> None:
        """Fit on the windows in `train_ids` (all of `windows` if None).

        `windows` may also contain context windows outside the training set
        (QD-015, D2): every window is replayed through the per-pod buffers in
        time order, so a training window's features use its true preceding
        samples, but only training windows become IsolationForest samples.
        The live buffers used by `score()` start empty after `fit()` returns.
        """
        ordered = sorted(windows, key=lambda window: (window.start_ts, window.window_id))
        training = [w for w in ordered if train_ids is None or w.window_id in train_ids]
        if len(training) < self.min_fit_windows:
            raise ValueError(
                f"IsolationForestDetector needs at least {self.min_fit_windows} windows to fit; got {len(training)}."
            )

        self._feature_names = sorted({point.name for window in training for point in window.metrics})
        observed: dict[str, list[float]] = {name: [] for name in self._feature_names}
        for window in training:
            for point in window.metrics:
                if point.name in observed:
                    observed[point.name].append(point.value)
        self._defaults = {name: statistics.median(values) if values else 0.0 for name, values in observed.items()}

        fit_buffers: dict[str, _KeyBuffer] = {}
        vectors: list[list[float]] = []
        for window in ordered:
            buffer = fit_buffers.setdefault(_buffer_key(window), _KeyBuffer(self.buffer_size))
            history = buffer.push(window, self._feature_names, self._defaults)
            if train_ids is None or window.window_id in train_ids:
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
        columns = list(zip(*vectors, strict=True))
        self._center = [statistics.fmean(column) for column in columns]
        self._scale = [statistics.pstdev(column) or 1.0 for column in columns]
        self._buffers = {}
        self._last_vector = {}

    def observe(self, window: TelemetryWindow) -> None:
        """Push a context window into its buffer without scoring it (QD-015,
        D2): used for windows outside the evaluated split so that the next
        evaluated window of the same pod sees its real preceding sample."""
        self._require_fitted()
        self._live_buffer(window).push(window, self._feature_names, self._defaults)

    def score(self, window: TelemetryWindow) -> float:
        """Anomaly score normalized to [0, 1] (01-architecture-design.md
        SS5.2): the fraction of training scores at or below this window's
        raw score. Idempotent per window_id (QD-015, D3)."""
        self._require_fitted()
        history = self._live_buffer(window).push(window, self._feature_names, self._defaults)
        vector = _vectorize(history, self._feature_names)
        self._last_vector[_buffer_key(window)] = (window.window_id, vector)
        raw_score = -float(self._model.score_samples([vector])[0])  # type: ignore[union-attr]
        return round(_percentile(raw_score, self._train_scores), 4)

    def top_features(self, window: TelemetryWindow, k: int = 3) -> list[str]:
        """The `k` metrics of the last scored `window` that deviate most from
        the training mean (max over each metric's features of |x - mean| / std),
        as GD1's `_top_contributing_features`. [] if `window` was not the last
        window scored for its pod."""
        last = self._last_vector.get(_buffer_key(window))
        if last is None or last[0] != window.window_id:
            return []
        by_metric: dict[str, float] = {}
        for index, value in enumerate(last[1]):
            name = self._feature_names[index // _FEATURES_PER_METRIC]
            deviation = abs(value - self._center[index]) / self._scale[index]
            by_metric[name] = max(deviation, by_metric.get(name, 0.0))
        ranked = sorted(by_metric.items(), key=lambda item: item[1], reverse=True)
        return [name for name, _ in ranked[:k]]

    def is_candidate(self, window: TelemetryWindow, score: float) -> bool:
        """Never promotes during a key's cold start (its rolling buffer not
        yet at `buffer_size`) or for a window that was not the last one
        pushed for its key: the score is still logged, but a single-point
        history is structurally unlike the training vectors (see
        tests/test_isolation_forest_detector.py), so it is not a trustworthy
        anomaly signal yet.
        """
        buffer = self._buffers.get(_buffer_key(window))
        if buffer is None or not buffer.is_full() or buffer.last_window_id() != window.window_id:
            return False
        return score >= self.threshold

    def _require_fitted(self) -> None:
        if self._model is None:
            raise RuntimeError("IsolationForestDetector must be fitted before scoring.")

    def _live_buffer(self, window: TelemetryWindow) -> _KeyBuffer:
        return self._buffers.setdefault(_buffer_key(window), _KeyBuffer(self.buffer_size))


def _percentile(raw_score: float, reference: list[float]) -> float:
    """Fraction of the (sorted) reference scores at or below `raw_score`."""
    if not reference:
        return 0.0
    return bisect_right(reference, raw_score) / len(reference)
