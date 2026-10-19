"""Run metrics (02-data-and-experiment-protocol.md SS4.1-4.2) over per-window rows.

A row is one evaluated window (`per_window.csv`). Positive prediction =
the pipeline raised an alert (`decision == "alert"`): a TRUE_ALERT verdict, or
a gate / budget rule that routes without the judge (GD1 parity only).
Recall is over **every** fault window of the evaluated set, including those
the detector never promoted (SS4.1).

Each block is computed twice (QD-017): on windows with telemetry (the main
result) and on all windows (secondary).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from eval.harness.stats import bootstrap_confusion_ci

Row = Mapping[str, Any]


def confusion(rows: Sequence[Row], positive: Callable[[Row], bool]) -> dict[str, int]:
    tp = fp = fn = tn = 0
    for row in rows:
        predicted, actual = positive(row), bool(row["label_is_fault"])
        if predicted and actual:
            tp += 1
        elif predicted:
            fp += 1
        elif actual:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _ratio(num: float, den: float) -> float:
    return num / den if den else 0.0


def scores(cm: Mapping[str, int]) -> dict[str, float]:
    precision = _ratio(cm["tp"], cm["tp"] + cm["fp"])
    recall = _ratio(cm["tp"], cm["tp"] + cm["fn"])
    return {
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * precision * recall, precision + recall),
        "fpr": _ratio(cm["fp"], cm["fp"] + cm["tn"]),
    }


def is_alert(row: Row) -> bool:
    return row["decision"] == "alert"


def is_candidate(row: Row) -> bool:
    return bool(row["is_candidate"])


def classification(
    rows: Sequence[Row], positive: Callable[[Row], bool], n_boot: int, seed: int
) -> dict[str, Any]:
    cm = confusion(rows, positive)
    out: dict[str, Any] = {**cm, **scores(cm)}
    for name, (lo, hi) in bootstrap_confusion_ci(cm, scores, n_boot, seed).items():
        out[f"{name}_ci95"] = [lo, hi]
    return out


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def operations(rows: Sequence[Row], price_in: float, price_out: float) -> dict[str, Any]:
    """Retrieval / judge cost and latency over the windows that reached each stage."""
    candidates = [r for r in rows if r["is_candidate"]]
    retrieved = [r for r in rows if r["retrieved"]]
    judged = [r for r in rows if r["judged"]]
    faults = [r for r in rows if r["label_is_fault"]]
    prompt_tokens = sum(int(r["prompt_tokens"] or 0) for r in judged)
    completion_tokens = sum(int(r["completion_tokens"] or 0) for r in judged)
    return {
        "windows": len(rows),
        "fault_windows": len(faults),
        "candidates": len(candidates),
        "retrieval_calls": len(retrieved),
        "llm_calls": len(judged),
        "api_calls": sum(1 for r in judged if r["actual_api_call"]),
        "cache_hits": sum(1 for r in judged if r["cache_hit"]),
        "cache_hit_rate": _ratio(sum(1 for r in judged if r["cache_hit"]), len(judged)),
        "manual_review": sum(1 for r in rows if r["decision"] == "manual_review"),
        # 02 SS4.2: share of fault windows with >= 1 retrieved event
        "context_coverage": _ratio(sum(1 for r in faults if int(r["context_events"]) > 0), len(faults)),
        # GD1's "context coverage": share of candidates with >= 1 event
        "candidate_context_coverage": _ratio(sum(1 for r in candidates if int(r["context_events"]) > 0), len(candidates)),
        "avg_context_events": _mean([float(r["context_events"]) for r in retrieved]),
        "avg_context_tokens": _mean([float(r["context_tokens"]) for r in retrieved]),
        "retrieval_latency_ms_avg": _mean([float(r["retrieval_latency_ms"]) for r in retrieved]),
        "retrieval_latency_ms_p95": _p95([float(r["retrieval_latency_ms"]) for r in retrieved]),
        "llm_latency_ms_avg": _mean([float(r["llm_latency_ms"]) for r in judged]),
        "llm_latency_ms_p95": _p95([float(r["llm_latency_ms"]) for r in judged]),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "estimated_cost_usd": prompt_tokens / 1e6 * price_in + completion_tokens / 1e6 * price_out,
        "downgraded_by_evidence_rule": sum(1 for r in judged if r["downgraded_by_evidence_rule"]),
        "judge_errors": sum(1 for r in judged if r["judge_status"] == "manual_review"),
    }


def summarize(
    rows: Sequence[Row], n_boot: int = 1000, seed: int = 42, price_in: float = 0.10, price_out: float = 0.40
) -> dict[str, Any]:
    subsets = {"telemetry": [r for r in rows if r["has_telemetry"]], "all": list(rows)}
    return {
        name: {
            "pipeline": classification(subset, is_alert, n_boot, seed),
            "detector_only": classification(subset, is_candidate, n_boot, seed),
            "operations": operations(subset, price_in, price_out),
        }
        for name, subset in subsets.items()
    }
