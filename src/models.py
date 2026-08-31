from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricWindow:
    window_id: str
    start_time: datetime
    end_time: datetime
    node_id: str
    service_id: str
    features: list[list[float]]
    feature_names: list[str]
    label: str = "normal"
    fault_type: str = "none"
    raw_features: list[list[float]] = field(default_factory=list)


@dataclass
class DetectorResult:
    window_id: str
    is_candidate: bool
    anomaly_score: float
    detector_label: str
    top_features: list[str]
    detector_latency_ms: float = 0.0


@dataclass
class AlertCandidate:
    alert_id: str
    window_id: str
    time_window: dict[str, str]
    node_id: str
    service_id: str
    anomaly_score: float
    metric_snapshot: dict[str, float]
    detector_label: str
    top_features: list[str]
    ground_truth: str = "normal"
    fault_type: str = "none"


@dataclass
class LogEvent:
    doc_id: str
    timestamp: datetime
    node_id: str
    service_id: str
    pod_id: str | None
    severity: str
    event_type: str
    message: str
    source: str = "log"
    metadata: dict[str, Any] = field(default_factory=dict)
