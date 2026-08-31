from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContextSignal:
    should_promote: bool
    score: float
    reason: str
    matched_context_ids: list[str]


def evaluate_context_signal(
    contexts: list[dict[str, Any]],
    min_context_score: float = 0.7,
    min_trace_duration_ms: float = 1.0,
    error_severities: set[str] | None = None,
) -> ContextSignal:
    error_severities = error_severities or {"ERROR", "CRITICAL"}
    best_score = 0.0
    matched: list[str] = []
    reasons: list[str] = []
    for context in contexts:
        retrieval_score = float(context.get("score", 0.0) or 0.0)
        if retrieval_score < min_context_score:
            continue
        severity = str(context.get("severity", "")).upper()
        event_type = str(context.get("event_type", ""))
        message = str(context.get("message", ""))
        doc_id = str(context.get("doc_id", ""))
        if severity in error_severities:
            matched.append(doc_id)
            best_score = max(best_score, min(1.0, retrieval_score + 0.15))
            reasons.append(f"{severity.lower()}_context")
            continue
        duration = trace_duration_ms(message)
        if event_type == "trace_span" and duration >= min_trace_duration_ms:
            matched.append(doc_id)
            duration_boost = min(0.2, duration / 500.0)
            best_score = max(best_score, min(1.0, retrieval_score + duration_boost))
            reasons.append("slow_trace_context")
    if matched:
        return ContextSignal(True, round(best_score, 4), ",".join(sorted(set(reasons))), matched[:5])
    return ContextSignal(False, 0.0, "no_strong_context_signal", [])


def trace_duration_ms(message: str) -> float:
    marker = "duration_ms="
    if marker not in message:
        return 0.0
    raw = message.split(marker, 1)[1].split()[0]
    try:
        return float(raw)
    except ValueError:
        return 0.0
