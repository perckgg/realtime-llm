from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.retrieval.embedder import tokenize


def summarize_retrieval(records: list[dict[str, Any]]) -> dict[str, Any]:
    windows = len(records)
    contexts = [context for record in records for context in record.get("contexts", [])]
    positive_records = [record for record in records if record.get("ground_truth") == "true_alert"]
    network_delay_records = [record for record in records if record.get("fault_type") == "network_delay"]
    network_delay_positive_records = [
        record
        for record in network_delay_records
        if record.get("ground_truth") == "true_alert"
    ]

    return {
        "windows": windows,
        "positive_windows": len(positive_records),
        "retrieved_context_count": len(contexts),
        "avg_retrieved_context_count": round(
            len(contexts) / windows,
            4,
        )
        if windows
        else 0.0,
        "context_coverage": coverage_rate(records, any_context),
        "positive_context_coverage": coverage_rate(positive_records, any_context),
        "service_context_coverage": coverage_rate(records, same_service_context),
        "positive_service_context_coverage": coverage_rate(positive_records, same_service_context),
        "network_delay_context_coverage": coverage_rate(network_delay_records, any_context),
        "network_delay_service_context_coverage": coverage_rate(
            network_delay_positive_records,
            same_service_context,
        ),
        "avg_context_tokens": avg_context_tokens(contexts),
        "avg_retrieval_latency_ms": avg_numeric(records, "retrieval_latency_ms"),
        "p95_retrieval_latency_ms": percentile_numeric(records, "retrieval_latency_ms", 0.95),
        "graph_coverage": coverage_rate(records, graph_reachable_context),
        "avg_graph_distance": avg_graph_distance(contexts),
        "avg_graph_candidate_count": avg_numeric(records, "graph_candidate_count"),
        "topology_expanded_context_ratio": topology_context_ratio(contexts, include_bm25_overlap=True),
        "topology_only_context_ratio": topology_context_ratio(contexts, include_bm25_overlap=False),
        "avg_candidate_pool_size": avg_numeric(records, "candidate_pool_size"),
        "avg_duplicates_removed": avg_numeric(records, "duplicates_removed"),
    }


def group_summaries(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key) or "unknown")].append(record)
    rows = []
    for group, group_records in sorted(groups.items()):
        summary = summarize_retrieval(group_records)
        rows.append({key: group, **summary})
    return rows


def coverage_rate(records: list[dict[str, Any]], predicate: Any) -> float:
    if not records:
        return 0.0
    return round(sum(1 for record in records if predicate(record)) / len(records), 4)


def any_context(record: dict[str, Any]) -> bool:
    return bool(record.get("contexts"))


def same_service_context(record: dict[str, Any]) -> bool:
    alert_service = record.get("service_id")
    return any(context.get("context_service") == alert_service for context in record.get("contexts", []))


def graph_reachable_context(record: dict[str, Any]) -> bool:
    return any(context.get("graph_distance") is not None for context in record.get("contexts", []))


def avg_context_tokens(contexts: list[dict[str, Any]]) -> float:
    if not contexts:
        return 0.0
    return round(
        sum(len(tokenize(str(context.get("content_preview") or ""))) for context in contexts)
        / len(contexts),
        4,
    )


def avg_graph_distance(contexts: list[dict[str, Any]]) -> float:
    distances = [
        float(context["graph_distance"])
        for context in contexts
        if context.get("graph_distance") is not None
    ]
    return round(sum(distances) / len(distances), 4) if distances else 0.0


def topology_context_ratio(contexts: list[dict[str, Any]], include_bm25_overlap: bool) -> float:
    if not contexts:
        return 0.0
    count = 0
    for context in contexts:
        flags = set(context.get("source_flags") or [])
        if "graph" not in flags:
            continue
        if include_bm25_overlap or "bm25" not in flags:
            count += 1
    return round(count / len(contexts), 4)


def avg_numeric(records: list[dict[str, Any]], key: str) -> float:
    values = [float(record.get(key) or 0.0) for record in records]
    return round(sum(values) / len(values), 4) if values else 0.0


def percentile_numeric(records: list[dict[str, Any]], key: str, quantile: float) -> float:
    values = sorted(float(record.get(key) or 0.0) for record in records)
    if not values:
        return 0.0
    if len(values) == 1:
        return round(values[0], 4)
    index = (len(values) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return round(values[lower], 4)
    interpolated = values[lower] + (values[upper] - values[lower]) * (index - lower)
    return round(interpolated, 4)
