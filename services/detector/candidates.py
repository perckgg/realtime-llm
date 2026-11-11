"""Builds AlertCandidate from a Detector's verdict (01-architecture-design.md
SS6.2's flow): the metric-score branch, and the Rescue Score branch (M7,
QD-033) whose score is computed offline by scripts/build_rescue_features.py
(services/detector/rescue.py) and handed to the runner as a window list.

QD-016: the candidate also carries what retrieval and the judge prompt read
from the window -- pod, end of window, the window's metric values -- and,
from the detector, the top deviating metrics (QD-017, V9).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from packages.schemas.models import AlertCandidate, TelemetryWindow


def build_alert_candidate(
    window: TelemetryWindow,
    score: float,
    is_candidate: bool,
    top_features: Sequence[str] = (),
    source: Literal["metric", "rescue"] = "metric",
    rescue_score: float | None = None,
    rescue_components: dict[str, float] | None = None,
) -> AlertCandidate | None:
    """`source="rescue"`: a window the detector did not promote, promoted by the Rescue Score
    gate (services/detector/rescue.py, M7); the judge prompt is the same."""
    if not is_candidate:
        return None
    return AlertCandidate(
        candidate_id=f"cand-{window.window_id}",
        window_id=window.window_id,
        service=window.service,
        ts=window.start_ts,
        anomaly_score=score,
        source=source,
        rescue_score=rescue_score,
        rescue_components=rescue_components,
        pod=window.pod,
        end_ts=window.end_ts,
        metric_snapshot={point.name: point.value for point in window.metrics},
        top_features=list(top_features),
    )
