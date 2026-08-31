from __future__ import annotations

import json
from typing import Any

from src.models import AlertCandidate


def compose_prompt(alert: AlertCandidate, contexts: list[dict[str, Any]]) -> str:
    compact_contexts = [
        {
            "doc_id": context.get("doc_id"),
            "timestamp": context.get("timestamp"),
            "source": context.get("source"),
            "severity": context.get("severity"),
            "event_type": context.get("event_type"),
            "score": context.get("score"),
            "message": str(context.get("message", ""))[:240],
        }
        for context in contexts
    ]
    payload = {
        "role": "SRE alert validation judge",
        "task": (
            "Classify whether this candidate is a true operational alert. "
            "Return only JSON. Evidence must be selected from allowed_evidence_ids."
        ),
        "alert_candidate": {
            "alert_id": alert.alert_id,
            "time_window": alert.time_window,
            "node_id": alert.node_id,
            "service_id": alert.service_id,
            "anomaly_score": alert.anomaly_score,
            "metric_snapshot": alert.metric_snapshot,
            "top_features": alert.top_features,
            "allowed_evidence_ids": [context.get("doc_id") for context in compact_contexts],
        },
        "related_logs_events": compact_contexts,
        "output_schema": {
            "label": "true_alert | false_positive | uncertain",
            "severity": "P1 | P2 | P3 | none",
            "confidence": 0.0,
            "evidence": ["log_id_or_event_id"],
            "reason": "one short sentence, max 25 words",
            "recommended_action": "one short action, max 20 words",
        },
        "rules": [
            "Use true_alert only when metrics and context support the same incident.",
            "Use false_positive when context explains the anomaly as benign.",
            "Use uncertain when evidence is weak or unrelated.",
            "Do not invent evidence IDs.",
            "Use exactly these keys: label, severity, confidence, evidence, reason, recommended_action.",
            "Do not use alternative keys such as classification, verdict, or explanation.",
        ],
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))
