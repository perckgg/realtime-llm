from __future__ import annotations

import time

from src.detectors.base import BaseDetector
from src.models import DetectorResult, MetricWindow


class FeaturePressureDetector(BaseDetector):
    """Lightweight threshold detector for dependency-light feasibility experiments."""

    def __init__(self, threshold: float = 0.7) -> None:
        self.threshold = threshold

    def score(self, window: MetricWindow) -> DetectorResult:
        started = time.perf_counter()
        source = window.raw_features or window.features
        if not source:
            score = 0.0
            top_features: list[str] = []
        else:
            columns = list(zip(*source))
            feature_scores = [
                max(_feature_pressure(name, value) for value in column)
                for name, column in zip(window.feature_names, columns)
            ]
            max_score = max(feature_scores) if feature_scores else 0.0
            score = min(1.0, max_score)
            ranked = sorted(
                zip(window.feature_names, feature_scores),
                key=lambda item: item[1],
                reverse=True,
            )
            top_features = [name for name, _ in ranked[:3]]
        latency = (time.perf_counter() - started) * 1000
        return DetectorResult(
            window_id=window.window_id,
            is_candidate=score >= self.threshold,
            anomaly_score=round(score, 4),
            detector_label="anomaly" if score >= self.threshold else "normal",
            top_features=top_features,
            detector_latency_ms=latency,
        )


def _feature_pressure(name: str, value: float) -> float:
    thresholds = {
        "cpu": 90.0,
        "memory": 85.0,
        "disk_io": 70.0,
        "network": 1_000_000.0,
        "latency": 1000.0,
        "workload": 1000.0,
        "success_rate_drop": 1000.0,
        "value_z": 3.0,
        "abs_delta_z": 3.0,
        "robust_z": 3.0,
    }
    threshold = thresholds.get(name, 100.0)
    if name.endswith("_z") or name == "robust_z":
        value = abs(value)
    return max(0.0, value / threshold)
