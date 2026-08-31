from __future__ import annotations

import statistics
import time
from typing import Any

from src.detectors.base import BaseDetector
from src.models import DetectorResult, MetricWindow


class IsolationForestDetector(BaseDetector):
    """Sklearn Isolation Forest detector over aggregated metric-window features."""

    def __init__(
        self,
        threshold: float = 0.95,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
        max_samples: str | int | float = "auto",
        train_on_normal_only: bool = False,
        min_fit_windows: int = 20,
    ) -> None:
        self.threshold = threshold
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.max_samples = max_samples
        self.train_on_normal_only = train_on_normal_only
        self.min_fit_windows = min_fit_windows
        self.model: Any | None = None
        self.feature_names: list[str] = []
        self.center: list[float] = []
        self.scale: list[float] = []
        self.train_scores: list[float] = []

    def fit(self, windows: list[MetricWindow]) -> None:
        training_windows = windows
        if self.train_on_normal_only:
            normal_windows = [window for window in windows if window.label != "true_alert"]
            if len(normal_windows) >= self.min_fit_windows:
                training_windows = normal_windows
        if len(training_windows) < self.min_fit_windows:
            raise ValueError(
                f"IsolationForestDetector needs at least {self.min_fit_windows} windows to fit; "
                f"got {len(training_windows)}."
            )

        from sklearn.ensemble import IsolationForest

        x_train, self.feature_names = _window_matrix(training_windows)
        self.center = [statistics.fmean(column) for column in zip(*x_train)]
        self.scale = [statistics.pstdev(column) or 1.0 for column in zip(*x_train)]
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            max_samples=self.max_samples,
        )
        self.model.fit(x_train)
        self.train_scores = _percentile_reference(self.model, x_train)

    def score(self, window: MetricWindow) -> DetectorResult:
        if self.model is None:
            raise RuntimeError("IsolationForestDetector must be fitted before scoring.")
        started = time.perf_counter()
        vector, vector_names = _window_vector(window)
        raw_score = -float(self.model.score_samples([vector])[0])
        anomaly_score = _percentile_score(raw_score, self.train_scores)
        contribution_names = self._top_contributing_features(vector, vector_names)
        latency = (time.perf_counter() - started) * 1000
        return DetectorResult(
            window_id=window.window_id,
            is_candidate=anomaly_score >= self.threshold,
            anomaly_score=round(anomaly_score, 4),
            detector_label="anomaly" if anomaly_score >= self.threshold else "normal",
            top_features=contribution_names,
            detector_latency_ms=latency,
        )

    def _top_contributing_features(self, vector: list[float], vector_names: list[str]) -> list[str]:
        if not self.center or not self.scale:
            return [name.split("__", 1)[0] for name in vector_names[:3]]
        contributions = []
        for name, value, center, scale in zip(vector_names, vector, self.center, self.scale):
            base_feature = name.split("__", 1)[0]
            contributions.append((base_feature, abs(value - center) / scale))
        by_feature: dict[str, float] = {}
        for name, score in contributions:
            by_feature[name] = max(score, by_feature.get(name, 0.0))
        ranked = sorted(by_feature.items(), key=lambda item: item[1], reverse=True)
        return [name for name, _ in ranked[:3]]


def _window_matrix(windows: list[MetricWindow]) -> tuple[list[list[float]], list[str]]:
    vectors = []
    names: list[str] = []
    for index, window in enumerate(windows):
        vector, vector_names = _window_vector(window)
        if index == 0:
            names = vector_names
        vectors.append(vector)
    return vectors, names


def _window_vector(window: MetricWindow) -> tuple[list[float], list[str]]:
    source = window.raw_features or window.features
    if not source:
        return [], []
    columns = list(zip(*source))
    vector: list[float] = []
    names: list[str] = []
    for name, column in zip(window.feature_names, columns):
        values = [float(value) for value in column]
        first = values[0]
        last = values[-1]
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
        names.extend(
            [
                f"{name}__mean",
                f"{name}__std",
                f"{name}__min",
                f"{name}__max",
                f"{name}__last",
                f"{name}__delta",
            ]
        )
    return vector, names


def _percentile_reference(model: Any, x_train: list[list[float]]) -> list[float]:
    scores = sorted(-float(score) for score in model.score_samples(x_train))
    return scores or [0.0]


def _percentile_score(raw_score: float, reference: list[float]) -> float:
    if not reference:
        return 0.0
    lower_or_equal = 0
    for score in reference:
        if score <= raw_score:
            lower_or_equal += 1
        else:
            break
    return lower_or_equal / len(reference)
