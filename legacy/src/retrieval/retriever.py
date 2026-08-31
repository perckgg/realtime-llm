from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
from typing import Any

from src.models import AlertCandidate, LogEvent
from src.retrieval.context_store import LocalContextStore, StoredContext
from src.time_utils import parse_timestamp


class HybridRetriever:
    def __init__(
        self,
        store: LocalContextStore,
        top_k: int = 5,
        time_margin_minutes: int = 5,
        search_k: int = 250,
        semantic_weight: float = 0.45,
        time_weight: float = 0.25,
        metadata_weight: float = 0.2,
        signal_weight: float = 0.1,
    ) -> None:
        self.store = store
        self.top_k = top_k
        self.time_margin = timedelta(minutes=time_margin_minutes)
        self.search_k = search_k
        self.semantic_weight = semantic_weight
        self.time_weight = time_weight
        self.metadata_weight = metadata_weight
        self.signal_weight = signal_weight

    def retrieve(self, alert: AlertCandidate) -> tuple[list[dict[str, Any]], float]:
        started = time.perf_counter()
        start = parse_timestamp(alert.time_window["start"])
        end = parse_timestamp(alert.time_window["end"])
        expanded_start = start - self.time_margin
        expanded_end = end + self.time_margin
        query = _build_query(alert)
        semantic_matches = self.store.search(query, top_n=max(self.search_k, self.top_k * 20))
        strict_candidates: list[tuple[float, dict[str, float], LogEvent]] = []
        relaxed_candidates: list[tuple[float, dict[str, float], LogEvent]] = []

        for semantic_score, item in semantic_matches:
            event = item.event
            if not (expanded_start <= event.timestamp <= expanded_end):
                continue
            component_scores = _component_scores(
                alert=alert,
                event=event,
                semantic_score=semantic_score,
                start=start,
                end=end,
                margin=self.time_margin,
            )
            score = _weighted_score(
                component_scores,
                semantic_weight=self.semantic_weight,
                time_weight=self.time_weight,
                metadata_weight=self.metadata_weight,
                signal_weight=self.signal_weight,
            )
            candidate = (score, component_scores, event)
            if component_scores["metadata_score"] > 0.0:
                strict_candidates.append(candidate)
            else:
                relaxed_candidates.append(candidate)

        ranked = sorted(strict_candidates, key=lambda item: item[0], reverse=True)
        if len(ranked) < self.top_k:
            ranked.extend(sorted(relaxed_candidates, key=lambda item: item[0], reverse=True))
        contexts = [_context_payload(score, components, event, self.store.actual_backend) for score, components, event in ranked[: self.top_k]]
        latency = (time.perf_counter() - started) * 1000
        return contexts, latency


def _build_query(alert: AlertCandidate) -> str:
    high_metrics = [
        f"{name}:{value}"
        for name, value in sorted(alert.metric_snapshot.items(), key=lambda item: abs(float(item[1])), reverse=True)[:4]
    ]
    return " ".join(
        [
            alert.service_id,
            alert.node_id,
            alert.detector_label,
            alert.fault_type,
            *alert.top_features,
            *high_metrics,
        ]
    )


def _component_scores(
    alert: AlertCandidate,
    event: LogEvent,
    semantic_score: float,
    start: datetime,
    end: datetime,
    margin: timedelta,
) -> dict[str, float]:
    metadata_score = _metadata_score(alert, event)
    time_score = _time_score(event.timestamp, start, end, margin)
    severity_score = {"CRITICAL": 1.0, "ERROR": 0.9, "WARN": 0.65, "INFO": 0.25}.get(event.severity.upper(), 0.2)
    trace_score = _trace_score(alert, event)
    signal_score = max(severity_score, trace_score)
    return {
        "semantic_score": max(0.0, min(1.0, semantic_score)),
        "time_score": time_score,
        "metadata_score": metadata_score,
        "severity_score": severity_score,
        "trace_score": trace_score,
        "signal_score": signal_score,
    }


def _weighted_score(
    scores: dict[str, float],
    semantic_weight: float,
    time_weight: float,
    metadata_weight: float,
    signal_weight: float,
) -> float:
    return (
        scores["semantic_score"] * semantic_weight
        + scores["time_score"] * time_weight
        + scores["metadata_score"] * metadata_weight
        + scores["signal_score"] * signal_weight
    )


def _metadata_score(alert: AlertCandidate, event: LogEvent) -> float:
    score = 0.0
    if event.service_id == alert.service_id:
        score += 0.65
    if event.node_id == alert.node_id:
        score += 0.35
    if alert.service_id and alert.service_id in event.message:
        score += 0.15
    return min(score, 1.0)


def _time_score(timestamp: datetime, start: datetime, end: datetime, margin: timedelta) -> float:
    if start <= timestamp <= end:
        return 1.0
    distance = min(abs((timestamp - start).total_seconds()), abs((timestamp - end).total_seconds()))
    margin_seconds = margin.total_seconds() or 1.0
    return max(0.0, 1.0 - distance / margin_seconds)


def _trace_score(alert: AlertCandidate, event: LogEvent) -> float:
    if event.event_type != "trace_span" and event.source != "nezha_trace":
        return 0.0
    score = 0.5
    if any(feature in {"latency", "network", "workload"} for feature in alert.top_features):
        score += 0.25
    duration = _duration_ms(event.message)
    if duration >= 1000:
        score += 0.25
    elif duration >= 500:
        score += 0.1
    return min(score, 1.0)


def _duration_ms(message: str) -> float:
    marker = "duration_ms="
    if marker not in message:
        return 0.0
    tail = message.split(marker, 1)[1].split()[0]
    try:
        value = float(tail)
    except ValueError:
        return 0.0
    return value if math.isfinite(value) else 0.0


def _context_payload(score: float, components: dict[str, float], event: LogEvent, backend: str) -> dict[str, Any]:
    return {
        "doc_id": event.doc_id,
        "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
        "source": event.source,
        "score": round(score, 4),
        "semantic_score": round(components["semantic_score"], 4),
        "time_score": round(components["time_score"], 4),
        "metadata_score": round(components["metadata_score"], 4),
        "severity_score": round(components["severity_score"], 4),
        "trace_score": round(components["trace_score"], 4),
        "node_id": event.node_id,
        "service_id": event.service_id,
        "severity": event.severity,
        "event_type": event.event_type,
        "message": event.message,
        "retrieval_backend": backend,
    }
