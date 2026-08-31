from __future__ import annotations

from typing import Any


def compute_classification(records: list[dict[str, Any]]) -> dict[str, float]:
    tp = fp = tn = fn = 0
    for record in records:
        truth = record.get("ground_truth") == "true_alert"
        predicted = record.get("final_decision") == "route_alert"
        if truth and predicted:
            tp += 1
        elif not truth and predicted:
            fp += 1
        elif not truth and not predicted:
            tn += 1
        elif truth and not predicted:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = compute_classification(records)
    summary["evaluated_windows"] = len(records)
    summary["candidate_alerts"] = sum(1 for record in records if record.get("is_candidate"))
    summary["routed_alerts"] = sum(1 for record in records if record.get("final_decision") == "route_alert")
    manual_review_records = [record for record in records if record.get("final_decision") == "manual_review"]
    automated_records = [
        record for record in records if record.get("final_decision") in {"route_alert", "suppress"}
    ]
    llm_records = [record for record in records if record.get("llm_called")]
    summary["manual_reviews"] = len(manual_review_records)
    summary["manual_review_rate"] = _fraction(len(manual_review_records), len(records))
    summary["automated_decisions"] = len(automated_records)
    summary["automation_coverage"] = _fraction(len(automated_records), len(records))
    _add_prefixed_classification(summary, "selective", automated_records)
    _add_prefixed_classification(summary, "llm_conditional", llm_records)
    summary["alerts"] = summary["candidate_alerts"]
    summary["llm_calls"] = sum(1 for record in records if record.get("llm_called"))
    summary["llm_calls_avoided"] = sum(1 for record in records if record.get("llm_call_avoided"))
    summary["llm_budget_exhausted"] = sum(1 for record in records if record.get("gate_action") == "llm_budget_exhausted")
    summary["input_tokens"] = sum(int(record.get("prompt_token_count", 0)) for record in records)
    summary["output_tokens"] = sum(int(record.get("completion_token_count", 0)) for record in records)
    summary["context_tokens"] = sum(int(record.get("context_token_count", 0)) for record in records)
    summary["avg_retrieved_context_count"] = _average(records, "retrieved_context_count")
    summary["avg_context_tokens"] = _average(records, "context_token_count")
    candidate_records = [record for record in records if record.get("is_candidate")]
    summary["candidates_with_context"] = sum(1 for record in candidate_records if int(record.get("retrieved_context_count", 0)) > 0)
    summary["context_coverage_rate"] = (
        round(summary["candidates_with_context"] / len(candidate_records), 4) if candidate_records else 0.0
    )
    retrieval_attempt_records = [
        record
        for record in records
        if record.get("retrieval_attempted")
        or (
            "retrieval_attempted" not in record
            and float(record.get("retrieval_latency_ms", 0.0) or 0.0) > 0
        )
    ]
    summary["retrieval_attempts"] = len(retrieval_attempt_records)
    summary["retrieval_successes"] = sum(
        1 for record in retrieval_attempt_records if int(record.get("retrieved_context_count", 0)) > 0
    )
    summary["retrieval_attempt_coverage_rate"] = _fraction(
        summary["retrieval_successes"],
        summary["retrieval_attempts"],
    )
    summary["context_rescue_checked"] = sum(1 for record in records if record.get("context_rescue_checked"))
    summary["context_rescue_promoted"] = sum(1 for record in records if record.get("context_rescue_promoted"))
    summary["api_fallback_calls"] = sum(1 for record in records if record.get("api_fallback_used"))
    summary["model_fallback_calls"] = sum(1 for record in records if record.get("model_fallback_used"))
    summary["local_llm_valid_json"] = sum(1 for record in records if record.get("local_result_valid_json") is True)
    summary["llm_providers"] = sorted({str(record.get("llm_provider")) for record in records if record.get("llm_provider")})
    summary["primary_local_models"] = sorted(
        {str(record.get("primary_local_model")) for record in records if record.get("primary_local_model")}
    )
    summary["fallback_models"] = sorted(
        {str(record.get("fallback_model")) for record in records if record.get("fallback_model")}
    )
    summary["llm_cache_hits"] = sum(1 for record in records if record.get("llm_cache_hit"))
    summary["actual_api_calls"] = sum(1 for record in records if record.get("actual_api_call"))
    summary["llm_retry_count"] = sum(int(record.get("llm_retry_count", 0) or 0) for record in records)
    summary["llm_backoff_sleep_ms"] = round(
        sum(float(record.get("llm_backoff_sleep_ms", 0.0) or 0.0) for record in records),
        4,
    )
    summary["cache_hit_rate"] = (
        round(summary["llm_cache_hits"] / summary["llm_calls"], 4) if summary["llm_calls"] else 0.0
    )
    summary["scheduler_deferred"] = sum(1 for record in records if record.get("scheduler_action") == "defer")
    summary["scheduler_local_only"] = sum(1 for record in records if record.get("scheduler_action") == "local_only")
    summary["scheduler_api_allowed"] = sum(1 for record in records if record.get("scheduler_action") == "call")
    summary["api_deferred"] = sum(1 for record in records if record.get("api_deferred"))
    priority_values = [
        float(record["priority_score"])
        for record in records
        if record.get("priority_score") is not None
    ]
    summary["avg_priority_score"] = round(sum(priority_values) / len(priority_values), 4) if priority_values else 0.0
    summary["json_valid_rate"] = _rate(records, "json_valid")
    summary["fallback_rate"] = sum(1 for record in records if record.get("fallback_status") == "fallback") / len(records) if records else 0.0
    summary["avg_detector_latency_ms"] = _average(records, "detector_latency_ms")
    summary["avg_retrieval_latency_ms"] = _average(records, "retrieval_latency_ms")
    summary["avg_llm_latency_ms"] = _average(records, "llm_latency_ms")
    summary["avg_end_to_end_latency_ms"] = _average(records, "end_to_end_latency_ms")
    summary["retrieval_backends"] = sorted({str(record.get("retrieval_backend")) for record in records if record.get("retrieval_backend")})
    summary["retrieval_backend_warnings"] = sorted(
        {str(record.get("retrieval_backend_warning")) for record in records if record.get("retrieval_backend_warning")}
    )
    summary["by_service"] = group_classification(records, "service_id")
    summary["by_fault_type"] = group_classification(records, "fault_type")
    return summary


def group_classification(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        group_key = str(record.get(key) or "unknown")
        groups.setdefault(group_key, []).append(record)
    grouped: dict[str, dict[str, Any]] = {}
    for group_key, group_records in sorted(groups.items()):
        metrics = compute_classification(group_records)
        metrics["windows"] = len(group_records)
        metrics["candidate_alerts"] = sum(1 for record in group_records if record.get("is_candidate"))
        metrics["llm_calls"] = sum(1 for record in group_records if record.get("llm_called"))
        grouped[group_key] = metrics
    return grouped


def false_positive_reduction(base: dict[str, Any], candidate: dict[str, Any]) -> float:
    base_fp = float(base.get("fp", 0))
    cand_fp = float(candidate.get("fp", 0))
    if base_fp == 0:
        return 0.0
    return round((base_fp - cand_fp) / base_fp, 4)


def _average(records: list[dict[str, Any]], key: str) -> float:
    values = [float(record.get(key, 0.0)) for record in records]
    return round(sum(values) / len(values), 4) if values else 0.0


def _rate(records: list[dict[str, Any]], key: str) -> float:
    calls = [record for record in records if record.get("llm_called")]
    if not calls:
        return 0.0
    return round(sum(1 for record in calls if record.get(key)) / len(calls), 4)


def _fraction(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _add_prefixed_classification(
    summary: dict[str, Any],
    prefix: str,
    records: list[dict[str, Any]],
) -> None:
    metrics = compute_classification(records)
    summary[f"{prefix}_windows"] = len(records)
    for key, value in metrics.items():
        summary[f"{prefix}_{key}"] = value
