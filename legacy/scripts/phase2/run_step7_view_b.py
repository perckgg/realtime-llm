from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.phase2.run_step7_view_a import (
    _add_cost_estimate,
    _load_dotenv,
    _sha256_strings,
    _unique_ordered,
    _window_id_to_index,
)
from src.config import load_config
from src.evaluation.metrics import false_positive_reduction, summarize
from src.main import run_pipeline


_load_dotenv(ROOT / ".env")


DEFAULT_VARIANTS = [
    "detector_only",
    "llm_without_rag",
    "hybrid_bm25_top6",
    "topology_aware_fusion_top6",
    "context_rescue",
]
REUSED_VIEW_A_VARIANTS = {
    "hybrid_bm25_top6",
    "topology_aware_fusion_top6",
}
METHOD_LABELS = {
    "detector_only": "Detector-only",
    "llm_without_rag": "LLM without RAG",
    "hybrid_bm25_top6": "BM25 RAG top-6",
    "topology_aware_fusion_top6": "Topology-Aware Fusion top-6",
    "context_rescue": "Context Rescue [architecture-enhanced]",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Step 7 View B architecture-level comparison on frozen paper_500."
    )
    parser.add_argument("--split", default="paper_500")
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--window-index", default="outputs\\phase2\\window_index.csv")
    parser.add_argument("--freeze-json", default="outputs\\phase2\\input_freeze.json")
    parser.add_argument(
        "--config",
        default="nezha_setup\\config\\experiment_phase2_topology_fusion_500w.yaml",
    )
    parser.add_argument(
        "--view-a-root",
        default="outputs\\phase2\\step7_rerun\\operational_budget_120",
    )
    parser.add_argument("--output-dir", default="outputs\\phase2\\step7_view_b\\results")
    parser.add_argument("--audit-dir", default="outputs\\phase2\\step7_view_b\\audit")
    parser.add_argument(
        "--report-path",
        default="outputs\\phase2\\step7_view_b\\step7_view_b_report.json",
    )
    parser.add_argument(
        "--cache-dir",
        default="outputs\\phase2\\step7_view_b\\cache",
    )
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-2.5-flash-lite")
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--max-total-calls", type=int, default=120)
    parser.add_argument("--max-llm-calls-per-minute", type=int, default=15)
    parser.add_argument("--allow-existing-cache", action="store_true")
    parser.add_argument("--input-cost-per-1m-tokens", type=float, default=0.10)
    parser.add_argument("--output-cost-per-1m-tokens", type=float, default=0.40)
    parser.add_argument(
        "--cost-pricing-source",
        default="gemini_flash_lite_published",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    unknown = sorted(set(args.variants) - set(DEFAULT_VARIANTS))
    if unknown:
        raise ValueError(f"Unsupported View B variants: {', '.join(unknown)}")
    if args.max_total_calls <= 0:
        raise ValueError("--max-total-calls must be positive")

    output_dir = absolute(args.output_dir)
    audit_dir = absolute(args.audit_dir)
    report_path = absolute(args.report_path)
    cache_dir = absolute(args.cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    selected_window_ids, split_meta, split_rows = frozen_split(args)
    base_config = load_config(args.config)
    window_lookup = _window_id_to_index(base_config)
    missing = [window_id for window_id in selected_window_ids if window_id not in window_lookup]
    if missing:
        raise RuntimeError(
            f"Frozen split contains {len(missing)} window IDs missing from metric preprocessing"
        )
    selected_indices = [window_lookup[window_id] for window_id in selected_window_ids]

    rows: list[dict[str, Any]] = []
    variant_reports: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for variant in args.variants:
        if variant in REUSED_VIEW_A_VARIANTS:
            summary, artifacts = load_reused_view_a_variant(args, variant)
            cache_state = "reused_fresh_view_a_run"
            artifact_origin = "reused_view_a_operational_budget_120"
        else:
            cache_path, cache_state = activate_cache(args, variant)
            config, mode = view_b_config(
                base_config,
                variant,
                output_dir,
                audit_dir,
                args,
                cache_state,
            )
            output_mode = f"step7_view_b_{args.split}_{variant}"
            records, _ = run_pipeline(
                config,
                mode,
                output_mode=output_mode,
                window_indices=selected_indices,
            )
            summary = summarize(records)
            _add_cost_estimate(summary, config)
            artifacts = {
                "results_json": str(output_dir / f"{output_mode}_results.json"),
                "summary_csv": str(output_dir / f"{output_mode}_summary.csv"),
                "summary_md": str(output_dir / f"{output_mode}_summary.md"),
                "config_snapshot": str(output_dir / f"{output_mode}_config_snapshot.json"),
                "by_fault_type_csv": str(
                    output_dir / f"{output_mode}_by_fault_type.csv"
                ),
                "audit_jsonl": str(audit_dir / f"{output_mode}_audit.jsonl"),
                "cache_jsonl": str(cache_path),
            }
            artifact_origin = "view_b_run"

        summaries[variant] = summary
        row = report_row(
            args,
            variant,
            summary,
            cache_state,
            artifact_origin,
        )
        rows.append(row)
        variant_reports.append(
            {
                "variant": variant,
                "method": METHOD_LABELS[variant],
                "architecture_enhanced": variant == "context_rescue",
                "artifact_origin": artifact_origin,
                "cache_state_at_start": cache_state,
                "summary": summary,
                "artifacts": artifacts,
            }
        )
        write_report(
            report_path,
            args,
            split_meta,
            split_rows,
            variant_reports,
            rows,
            summaries,
        )

    write_report(
        report_path,
        args,
        split_meta,
        split_rows,
        variant_reports,
        rows,
        summaries,
    )
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "split": args.split,
                "window_id_sha256": split_meta["window_id_sha256"],
                "variants": args.variants,
                "max_total_calls": args.max_total_calls,
            },
            indent=2,
        )
    )
    return 0


def frozen_split(
    args: argparse.Namespace,
) -> tuple[list[str], dict[str, Any], list[dict[str, str]]]:
    freeze = json.loads(absolute(args.freeze_json).read_text(encoding="utf-8"))
    with absolute(args.window_index).open("r", encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    rows = [row for row in all_rows if row.get("split") == args.split]
    split_meta = freeze.get("window_sets", {}).get(args.split)
    if not rows or not split_meta:
        raise RuntimeError(f"Frozen split '{args.split}' is unavailable")
    window_ids = _unique_ordered([str(row.get("window_id") or "") for row in rows])
    selected_hash = _sha256_strings(window_ids)
    if len(window_ids) != int(split_meta.get("rows", 0)):
        raise RuntimeError(
            f"Frozen split row mismatch: selected={len(window_ids)} "
            f"expected={split_meta.get('rows')}"
        )
    if selected_hash != str(split_meta.get("window_id_sha256") or ""):
        raise RuntimeError(
            f"Frozen split hash mismatch: selected={selected_hash} "
            f"expected={split_meta.get('window_id_sha256')}"
        )
    return window_ids, split_meta, rows


def view_b_config(
    base_config: dict[str, Any],
    variant: str,
    output_dir: Path,
    audit_dir: Path,
    args: argparse.Namespace,
    cache_state: str,
) -> tuple[dict[str, Any], str]:
    config = copy.deepcopy(base_config)
    config.setdefault("experiment", {})["name"] = f"step7_view_b_{variant}"
    evaluation = config.setdefault("evaluation", {})
    evaluation["output_dir"] = str(output_dir)
    evaluation["audit_dir"] = str(audit_dir)
    evaluation["max_windows"] = 0
    evaluation["max_llm_calls"] = args.max_total_calls
    gate = config.setdefault("llm_gate", {})
    gate["max_total_calls"] = args.max_total_calls
    gate["max_llm_calls_per_minute"] = (
        0 if cache_state.startswith("seeded_") else args.max_llm_calls_per_minute
    )
    llm = config.setdefault("llm", {})
    llm["provider"] = args.provider
    llm["model"] = args.model
    llm["max_output_tokens"] = args.max_output_tokens
    llm["timeout_seconds"] = args.timeout_seconds
    llm["max_retries"] = args.max_retries
    llm["input_cost_per_1m_tokens"] = args.input_cost_per_1m_tokens
    llm["output_cost_per_1m_tokens"] = args.output_cost_per_1m_tokens
    llm["cost_pricing_source"] = args.cost_pricing_source

    decision = config.setdefault("decision", {})
    decision["confidence_threshold"] = 0.80
    decision["llm_budget_exhausted_action"] = "manual_review"
    candidate_rescue = config.setdefault("candidate_rescue", {})
    candidate_rescue["enabled"] = False
    retrieval = config.setdefault("retrieval", {})

    if variant == "detector_only":
        decision["require_evidence_for_true_alert"] = False
        return config, "detector_only"
    if variant == "llm_without_rag":
        decision["require_evidence_for_true_alert"] = False
        return config, "llm_without_rag"
    if variant == "context_rescue":
        retrieval["backend"] = "hybrid_bm25"
        retrieval["vector_db"] = "hybrid_bm25"
        retrieval["top_k"] = 6
        candidate_rescue.update(
            {
                "enabled": True,
                "min_detector_score": 0.0,
                "min_context_score": 0.70,
                "min_trace_duration_ms": 1.0,
                "promoted_score": 0.85,
            }
        )
        decision["require_evidence_for_true_alert"] = True
        return config, "hybrid"
    raise ValueError(f"View B variant must be run or reused explicitly: {variant}")


def activate_cache(
    args: argparse.Namespace,
    variant: str,
) -> tuple[Path, str]:
    cache_path = absolute(args.cache_dir) / args.split / f"{variant}.jsonl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    state = "fresh"
    if cache_path.exists():
        if not args.allow_existing_cache:
            raise RuntimeError(
                f"Cache already exists for {variant}: {cache_path}. "
                "Pass --allow-existing-cache to resume or replay."
            )
        state = "existing"
    elif variant == "context_rescue":
        source = (
            absolute(args.view_a_root)
            / "cache"
            / args.split
            / "hybrid_bm25_top6.jsonl"
        )
        if not source.exists():
            raise RuntimeError(f"Context Rescue seed cache is missing: {source}")
        shutil.copyfile(source, cache_path)
        state = "seeded_from_view_a_bm25"

    os.environ["LLM_RESPONSE_CACHE"] = str(cache_path)
    from src.llm import response_cache

    response_cache.reset_global_cache_for_tests()
    return cache_path, state


def load_reused_view_a_variant(
    args: argparse.Namespace,
    variant: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    view_a_root = absolute(args.view_a_root)
    prefix = f"step7_view_a_operational_budget_120_{args.split}_{variant}"
    results_dir = view_a_root / "results"
    result_path = results_dir / f"{prefix}_results.json"
    audit_path = view_a_root / "audit" / f"{prefix}_audit.jsonl"
    if not result_path.exists() or not audit_path.exists():
        raise RuntimeError(f"Reusable View A artifact is missing for {variant}")
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    summary = dict(payload["summary"])
    return summary, {
        "results_json": str(result_path),
        "summary_csv": str(results_dir / f"{prefix}_summary.csv"),
        "summary_md": str(results_dir / f"{prefix}_summary.md"),
        "config_snapshot": str(results_dir / f"{prefix}_config_snapshot.json"),
        "by_fault_type_csv": str(results_dir / f"{prefix}_by_fault_type.csv"),
        "audit_jsonl": str(audit_path),
        "cache_jsonl": str(
            view_a_root / "cache" / args.split / f"{variant}.jsonl"
        ),
    }


def report_row(
    args: argparse.Namespace,
    variant: str,
    summary: dict[str, Any],
    cache_state: str,
    artifact_origin: str,
) -> dict[str, Any]:
    return {
        "comparison_view": "view_b_architecture_level",
        "split": args.split,
        "budget_regime": "operational_budget_120",
        "max_total_calls": args.max_total_calls,
        "variant": variant,
        "method": METHOD_LABELS[variant],
        "architecture_enhanced": variant == "context_rescue",
        "artifact_origin": artifact_origin,
        "windows": summary.get("evaluated_windows", 0),
        "candidate_alerts": summary.get("candidate_alerts", 0),
        "precision": summary.get("precision", 0),
        "recall": summary.get("recall", 0),
        "f1": summary.get("f1", 0),
        "false_positive_rate": summary.get("false_positive_rate", 0),
        "false_positive_reduction_vs_detector": "",
        "manual_reviews": summary.get("manual_reviews", 0),
        "manual_review_rate": summary.get("manual_review_rate", 0),
        "automation_coverage": summary.get("automation_coverage", 0),
        "llm_calls": summary.get("llm_calls", 0),
        "actual_api_calls": summary.get("actual_api_calls", 0),
        "llm_cache_hits": summary.get("llm_cache_hits", 0),
        "cache_hit_rate": summary.get("cache_hit_rate", 0),
        "context_coverage_rate": summary.get("context_coverage_rate", 0),
        "retrieval_attempt_coverage_rate": summary.get(
            "retrieval_attempt_coverage_rate", 0
        ),
        "avg_retrieval_latency_ms": summary.get("avg_retrieval_latency_ms", 0),
        "avg_llm_latency_ms": summary.get("avg_llm_latency_ms", 0),
        "json_valid_rate": summary.get("json_valid_rate", 0),
        "estimated_llm_cost_usd": summary.get("estimated_llm_cost_usd", 0),
        "cache_state_at_start": cache_state,
    }


def write_report(
    path: Path,
    args: argparse.Namespace,
    split_meta: dict[str, Any],
    split_rows: list[dict[str, str]],
    variant_reports: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
) -> None:
    detector = summaries.get("detector_only")
    if detector:
        for row in rows:
            summary = summaries[row["variant"]]
            row["false_positive_reduction_vs_detector"] = false_positive_reduction(
                detector, summary
            )
    report = {
        "protocol": {
            "comparison_view": "view_b_architecture_level",
            "split": args.split,
            "windows": int(split_meta["rows"]),
            "window_id_sha256": split_meta["window_id_sha256"],
            "budget_regime": "operational_budget_120",
            "max_total_calls": args.max_total_calls,
            "provider": args.provider,
            "model": args.model,
            "ground_truth_counts": dict(
                sorted(Counter(row["ground_truth"] for row in split_rows).items())
            ),
            "fault_type_counts": dict(
                sorted(Counter(row["fault_type"] for row in split_rows).items())
            ),
            "service_count": len({row["service_id"] for row in split_rows}),
            "scope_note": (
                "Architecture-level comparison. Context Rescue changes candidate "
                "promotion and is not a retrieval-only baseline."
            ),
        },
        "variants": variant_reports,
        "rows": rows,
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_csv(path.with_suffix(".csv"), rows)
    write_markdown(path.with_suffix(".md"), report, rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    path: Path,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    protocol = report["protocol"]
    lines = [
        "# Step 7 View B Architecture-level Report",
        "",
        f"- Frozen split: `{protocol['split']}` ({protocol['windows']} windows)",
        f"- Window hash: `{protocol['window_id_sha256']}`",
        f"- LLM: `{protocol['provider']}/{protocol['model']}`",
        f"- Budget: `{protocol['budget_regime']}` (`{protocol['max_total_calls']}` calls)",
        f"- Scope: {protocol['scope_note']}",
        "",
        "| Method | Architecture enhanced | Precision | Recall | F1 | FPR | FP reduction | Manual review | Context coverage | LLM calls | API calls | Cache hits | Cost USD |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {method} | {architecture_enhanced} | {precision} | {recall} | "
            "{f1} | {false_positive_rate} | {false_positive_reduction_vs_detector} | "
            "{manual_review_rate} | {context_coverage_rate} | {llm_calls} | "
            "{actual_api_calls} | {llm_cache_hits} | {estimated_llm_cost_usd} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Context Rescue is architecture-enhanced because it changes candidate promotion before LLM validation.",
            "Manual review is treated as abstention and is never counted as `route_alert`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def absolute(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


if __name__ == "__main__":
    raise SystemExit(main())
