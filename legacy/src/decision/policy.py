from __future__ import annotations

import hashlib
from dataclasses import dataclass

from typing import Any

from src.llm.judge_client import JudgeResult
from src.models import AlertCandidate, DetectorResult, MetricWindow
from src.preprocessing.metric_preprocessing import raw_metric_snapshot
from src.time_utils import isoformat


@dataclass
class GateDecision:
    action: str
    reason: str
    llm_call_avoided: bool


def build_alert_candidate(window: MetricWindow, result: DetectorResult) -> AlertCandidate:
    return AlertCandidate(
        alert_id=f"alert-{_stable_alert_suffix(window.window_id, result.anomaly_score)}",
        window_id=window.window_id,
        time_window={"start": isoformat(window.start_time), "end": isoformat(window.end_time)},
        node_id=window.node_id,
        service_id=window.service_id,
        anomaly_score=result.anomaly_score,
        metric_snapshot=raw_metric_snapshot(window),
        detector_label=result.detector_label,
        top_features=result.top_features,
        ground_truth=window.label,
        fault_type=window.fault_type,
    )


def _stable_alert_suffix(window_id: str, anomaly_score: float) -> str:
    key = f"{window_id}|{anomaly_score:.6f}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()[:10]


def gate_alert(score: float, config: dict) -> GateDecision:
    if not config.get("enabled", True):
        return GateDecision("call_llm", "gate disabled", False)
    low = float(config.get("low_threshold", 0.65))
    high = float(config.get("high_threshold", 0.9))
    high_action = str(config.get("high_score_action", "direct_alert"))
    if score < low:
        return GateDecision("ignore", "below low threshold", True)
    if score < high:
        return GateDecision("call_llm", "within review band", False)
    if high_action == "call_llm":
        return GateDecision("call_llm", "high score configured for LLM review", False)
    return GateDecision("direct_alert", "above high threshold", True)


def decide(
    alert: AlertCandidate,
    judge: JudgeResult | None,
    confidence_threshold: float,
    require_evidence_for_true_alert: bool = False,
) -> tuple[str, str]:
    if judge is None:
        return "route_alert", "detector_only"
    if not judge.valid_json or judge.decision is None:
        return "route_alert", "fallback"
    if judge.api_fallback_error and judge.api_fallback_reason in {
        "local_error",
        "local_invalid_json",
        "local_uncertain",
        "local_low_confidence",
    }:
        return "manual_review", "api_fallback_failed_manual_review"
    if (
        judge.api_fallback_error
        and judge.api_fallback_reason == "high_anomaly_score"
        and judge.decision.label != "true_alert"
    ):
        return "manual_review", "api_fallback_failed_manual_review"
    if judge.decision.label == "false_positive":
        return "suppress", "llm_valid"
    if judge.decision.label == "true_alert" and judge.decision.confidence >= confidence_threshold:
        if require_evidence_for_true_alert and not judge.decision.evidence:
            return "manual_review", "llm_valid_missing_evidence"
        return "route_alert", "llm_valid"
    return "manual_review", "llm_valid"


def decide_llm_budget_exhausted(decision_config: dict[str, Any] | None = None) -> tuple[str, str]:
    action = str((decision_config or {}).get("llm_budget_exhausted_action", "manual_review"))
    if action not in {"manual_review", "route_alert", "suppress"}:
        action = "manual_review"
    return action, "llm_budget_exhausted"
