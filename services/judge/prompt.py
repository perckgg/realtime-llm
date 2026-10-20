"""GD1's judge prompt, verbatim (legacy/src/llm/prompt_composer.py).

Do not edit the payload: M3's gate G-paper replays GD1's Gemini cache, whose
keys hash this exact string (tests/test_gd1_prompt_parity.py checks it against
GD1's cache). Only the adapters from GD2 objects to GD1's dict shapes live here.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from typing import Any

from packages.schemas.evidence import isoformat
from packages.schemas.models import AlertCandidate, ContextEvent


def compose_prompt(alert: dict[str, Any], contexts: list[dict[str, Any]]) -> str:
    """`alert`: GD1 AlertCandidate fields (alert_id, time_window, node_id,
    service_id, anomaly_score, metric_snapshot, top_features); `contexts`:
    GD1 retrieval payloads (see `context_payload`)."""
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
            "alert_id": alert["alert_id"],
            "time_window": alert["time_window"],
            "node_id": alert["node_id"],
            "service_id": alert["service_id"],
            "anomaly_score": alert["anomaly_score"],
            "metric_snapshot": alert["metric_snapshot"],
            "top_features": alert["top_features"],
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


def alert_payload(candidate: AlertCandidate, drop_metrics: Collection[str] = ()) -> dict[str, Any]:
    """GD2 AlertCandidate -> GD1 alert fields. GD1 rounded the score and
    metric values to 4 decimals (legacy/src/detectors, raw_metric_snapshot).

    `drop_metrics` (QD-023, V20) leaves those metrics out of `metric_snapshot`
    and `top_features`; empty keeps GD1's prompt byte for byte (G-paper)."""
    end = candidate.end_ts
    drop = set(drop_metrics)
    return {
        "alert_id": candidate.candidate_id,
        "time_window": {
            "start": isoformat(candidate.ts),
            "end": isoformat(end) if end is not None else isoformat(candidate.ts),
        },
        "node_id": candidate.pod or candidate.service,
        "service_id": candidate.service,
        "anomaly_score": round(candidate.anomaly_score, 4),
        "metric_snapshot": {
            name: round(value, 4) for name, value in candidate.metric_snapshot.items() if name not in drop
        },
        "top_features": [name for name in candidate.top_features if name not in drop],
    }


def context_payload(event: ContextEvent) -> dict[str, Any]:
    """ContextEvent -> GD1 `_context_payload` fields the prompt and mock read."""
    return {
        "doc_id": event.event_id,
        "timestamp": isoformat(event.ts),
        "source": event.debug.get("source"),
        "severity": event.debug.get("severity"),
        "event_type": event.debug.get("event_type"),
        # GD1 rounded the prompt score per strategy: BM25 4 decimals, topology 6.
        "score": event.debug.get("prompt_score", round(event.score, 4)),
        "message": event.content,
    }
