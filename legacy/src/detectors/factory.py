from __future__ import annotations

from typing import Any

from src.detectors.base import BaseDetector
from src.detectors.feature_pressure_detector import FeaturePressureDetector
from src.detectors.isolation_forest_detector import IsolationForestDetector
from src.models import MetricWindow


def build_detector(config: dict[str, Any], windows: list[MetricWindow]) -> BaseDetector:
    name = str(config.get("name", "feature_pressure")).lower()
    threshold = float(config.get("threshold", 0.7))
    if name in {"feature_pressure", "threshold", "pressure"}:
        return FeaturePressureDetector(threshold=threshold)
    if name in {"isolation_forest", "iforest"}:
        detector = IsolationForestDetector(
            threshold=threshold,
            contamination=float(config.get("contamination", 0.05)),
            n_estimators=int(config.get("n_estimators", 100)),
            random_state=int(config.get("random_state", 42)),
            max_samples=config.get("max_samples", "auto"),
            train_on_normal_only=bool(config.get("train_on_normal_only", False)),
            min_fit_windows=int(config.get("min_fit_windows", 20)),
        )
        fit_windows = _select_fit_windows(windows, config)
        detector.fit(fit_windows)
        return detector
    raise ValueError(f"Unsupported detector.name: {name}")


def _select_fit_windows(windows: list[MetricWindow], config: dict[str, Any]) -> list[MetricWindow]:
    fit_strategy = str(config.get("fit_strategy", "all")).lower()
    if fit_strategy == "warmup":
        warmup_windows = int(config.get("warmup_windows", 1000))
        return windows[:warmup_windows]
    if fit_strategy == "normal_only":
        normal_windows = [window for window in windows if window.label != "true_alert"]
        return normal_windows or windows
    return windows
