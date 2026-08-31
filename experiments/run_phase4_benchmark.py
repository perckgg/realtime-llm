from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.evaluation.metrics import false_positive_reduction, summarize
from src.main import run_pipeline


DEFAULT_VARIANTS = [
    {"name": "detector_only", "mode": "detector_only"},
    {"name": "llm_without_rag", "mode": "llm_without_rag"},
    {"name": "hybrid_local_top6", "mode": "hybrid", "vector_db": "local", "top_k": 6},
    {"name": "hybrid_bm25_top6", "mode": "hybrid", "vector_db": "hybrid_bm25", "top_k": 6},
    {"name": "hybrid_bm25_top10", "mode": "hybrid", "vector_db": "hybrid_bm25", "top_k": 10},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="nezha_setup/config/experiment_phase4_benchmark.yaml")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--max-windows", type=int, default=None)
    parser.add_argument("--max-llm-calls", type=int, default=None)
    args = parser.parse_args()

    base_config = load_config(args.config)
    output_root = Path(args.output_dir or base_config["evaluation"]["output_dir"])
    audit_root = Path(base_config["evaluation"]["audit_dir"])
    output_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, dict[str, Any]] = {}
    for variant in DEFAULT_VARIANTS:
        config = _variant_config(base_config, variant, output_root, audit_root, args.max_windows, args.max_llm_calls)
        records, _ = run_pipeline(config, str(variant["mode"]), output_mode=str(variant["name"]))
        summary = summarize(records)
        _add_cost_estimate(summary, config)
        summaries[str(variant["name"])] = summary

    detector_summary = summaries.get("detector_only", {})
    for summary in summaries.values():
        summary["false_positive_reduction_vs_detector"] = false_positive_reduction(detector_summary, summary)

    _write_json(output_root / "phase4_benchmark_report.json", summaries)
    _write_csv(output_root / "phase4_benchmark_summary.csv", summaries)
    _write_markdown(output_root / "phase4_benchmark_summary.md", summaries)
    print(json.dumps(summaries, indent=2))


def _variant_config(
    base_config: dict[str, Any],
    variant: dict[str, Any],
    output_root: Path,
    audit_root: Path,
    max_windows: int | None,
    max_llm_calls: int | None,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    name = str(variant["name"])
    config.setdefault("experiment", {})["name"] = name
    config.setdefault("evaluation", {})["output_dir"] = str(output_root)
    config.setdefault("evaluation", {})["audit_dir"] = str(audit_root)
    if max_windows is not None:
        config["evaluation"]["max_windows"] = max_windows
    if max_llm_calls is not None:
        config["evaluation"]["max_llm_calls"] = max_llm_calls
        config.setdefault("llm_gate", {})["max_total_calls"] = max_llm_calls
    if "vector_db" in variant:
        config.setdefault("retrieval", {})["vector_db"] = variant["vector_db"]
    if "top_k" in variant:
        config.setdefault("retrieval", {})["top_k"] = variant["top_k"]
    return config


def _write_json(path: Path, summaries: dict[str, dict[str, Any]]) -> None:
    path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def _write_csv(path: Path, summaries: dict[str, dict[str, Any]]) -> None:
    keys = [
        "variant",
        "evaluated_windows",
        "candidate_alerts",
        "routed_alerts",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "false_positive_reduction_vs_detector",
        "llm_calls",
        "llm_calls_avoided",
        "avg_retrieval_latency_ms",
        "avg_retrieved_context_count",
        "context_coverage_rate",
        "avg_context_tokens",
        "input_tokens",
        "output_tokens",
        "estimated_llm_cost_usd",
        "retrieval_backends",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        for variant, summary in summaries.items():
            row = {"variant": variant}
            row.update({key: summary.get(key, 0) for key in keys if key != "variant"})
            writer.writerow(row)


def _write_markdown(path: Path, summaries: dict[str, dict[str, Any]]) -> None:
    lines = [
        "# Phase 4 Benchmark Summary",
        "",
        "| Variant | Windows | Candidates | Precision | Recall | F1 | FPR | FP Reduction | LLM Calls | Context Coverage | Avg Ctx | Retrieval ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in summaries.items():
        lines.append(
            "| {variant} | {windows} | {candidates} | {precision} | {recall} | {f1} | {fpr} | {fp_reduction} | {llm_calls} | {coverage} | {avg_ctx} | {retrieval_ms} |".format(
                variant=variant,
                windows=summary.get("evaluated_windows", 0),
                candidates=summary.get("candidate_alerts", 0),
                precision=summary.get("precision", 0),
                recall=summary.get("recall", 0),
                f1=summary.get("f1", 0),
                fpr=summary.get("false_positive_rate", 0),
                fp_reduction=summary.get("false_positive_reduction_vs_detector", 0),
                llm_calls=summary.get("llm_calls", 0),
                coverage=summary.get("context_coverage_rate", 0),
                avg_ctx=summary.get("avg_retrieved_context_count", 0),
                retrieval_ms=summary.get("avg_retrieval_latency_ms", 0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _add_cost_estimate(summary: dict[str, Any], config: dict[str, Any]) -> None:
    llm_config = config.get("llm", {})
    input_rate = float(llm_config.get("input_cost_per_1m_tokens", 0.0) or 0.0)
    output_rate = float(llm_config.get("output_cost_per_1m_tokens", 0.0) or 0.0)
    input_tokens = float(summary.get("input_tokens", 0))
    output_tokens = float(summary.get("output_tokens", 0))
    summary["llm_cost_pricing_source"] = str(llm_config.get("cost_pricing_source", "not_configured"))
    summary["estimated_input_cost_usd"] = round((input_tokens / 1_000_000) * input_rate, 8)
    summary["estimated_output_cost_usd"] = round((output_tokens / 1_000_000) * output_rate, 8)
    summary["estimated_llm_cost_usd"] = round(
        summary["estimated_input_cost_usd"] + summary["estimated_output_cost_usd"],
        8,
    )


if __name__ == "__main__":
    main()
