"""Builds AlertCandidate from a Detector's verdict (01-architecture-design.md
SS6.2's flow). Only the metric-score branch is implemented -- see
services/detector/isolation_forest.py's module docstring and
docs/experiment-log.md QD-009 for why the Rescue Score gate (that section's
"else" branch) is deferred to Month 2.
"""

from __future__ import annotations

from packages.schemas.models import AlertCandidate, TelemetryWindow


def build_alert_candidate(window: TelemetryWindow, score: float, is_candidate: bool) -> AlertCandidate | None:
    if not is_candidate:
        return None
    return AlertCandidate(
        candidate_id=f"cand-{window.window_id}",
        window_id=window.window_id,
        service=window.service,
        ts=window.start_ts,
        anomaly_score=score,
        source="metric",
    )
