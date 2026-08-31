from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(ROOT / ".env")


from src.config import load_config
from src.evaluation.metrics import false_positive_reduction, summarize
from src.ingestion.metric_loader import load_metrics
from src.main import run_pipeline
from src.preprocessing.metric_preprocessing import create_metric_windows


DEFAULT_VARIANTS = ["hybrid_bm25_top6", "topology_aware_fusion_top6"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Step 7 View A on frozen Phase 2 splits: BM25 top-6 vs topology-aware fusion top-6."
    )
    parser.add_argument("--splits", nargs="+", default=["paper_300"])
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--window-index", default="outputs\\phase2\\window_index.csv")
    parser.add_argument("--freeze-json", default="outputs\\phase2\\input_freeze.json")
    parser.add_argument("--config-300", default="nezha_setup\\config\\experiment_phase2_topology_fusion_300w.yaml")
    parser.add_argument("--config-500", default="nezha_setup\\config\\experiment_phase2_topology_fusion_500w.yaml")
    parser.add_argument("--output-dir", default="outputs\\phase2\\step7_view_a\\results")
    parser.add_argument("--audit-dir", default="outputs\\phase2\\step7_view_a\\audit")
    parser.add_argument("--report-path", default="outputs\\phase2\\step7_view_a\\step7_view_a_report.json")
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-2.5-flash-lite")
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--max-llm-calls-per-minute", type=int, default=15)
    parser.add_argument("--cache-path", default=None)
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Directory for isolated per-split/per-variant cache files.",
    )
    parser.add_argument(
        "--allow-existing-cache",
        action="store_true",
        help="Allow cache replay. By default, an existing cache aborts the run.",
    )
    parser.add_argument(
        "--budget-regime",
        choices=["operational_budget_120", "quality_full_budget", "custom"],
        default="operational_budget_120",
    )
    parser.add_argument(
        "--max-total-calls",
        type=int,
        default=None,
        help="Override the regime LLM-call budget. Required for the custom regime.",
    )
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        help="Optional extra .env file. Values do not override existing environment variables.",
    )
    parser.add_argument("--input-cost-per-1m-tokens", type=float, default=0.10)
    parser.add_argument("--output-cost-per-1m-tokens", type=float, default=0.40)
    parser.add_argument("--cost-pricing-source", default="gemini_flash_lite_published")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.resolved_max_total_calls = _resolve_max_total_calls(args)
    for env_file in args.env_file:
        _load_dotenv(Path(env_file))

    output_dir = _abs_path(args.output_dir)
    audit_dir = _abs_path(args.audit_dir)
    report_path = _abs_path(args.report_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    freeze = json.loads(_abs_path(args.freeze_json).read_text(encoding="utf-8"))
    window_rows = list(csv.DictReader(_abs_path(args.window_index).open("r", encoding="utf-8", newline="")))

    split_reports: list[dict[str, Any]] = []
    variant_rows: list[dict[str, Any]] = []
    window_index_cache: dict[str, dict[str, int]] = {}

    for split in args.splits:
        split_rows = [row for row in window_rows if row.get("split") == split]
        if not split_rows:
            raise RuntimeError(f"Split '{split}' not found in {args.window_index}")
        split_meta = freeze.get("window_sets", {}).get(split)
        if not split_meta:
            raise RuntimeError(f"Split '{split}' not found in freeze metadata")

        selected_window_ids = _unique_ordered([str(row.get("window_id") or "") for row in split_rows])
        if len(selected_window_ids) != int(split_meta.get("rows", 0)):
            raise RuntimeError(
                f"Split '{split}' selected {len(selected_window_ids)} unique windows, expected {split_meta.get('rows')}"
            )
        selected_hash = _sha256_strings(selected_window_ids)
        expected_hash = str(split_meta.get("window_id_sha256") or "")
        if selected_hash != expected_hash:
            raise RuntimeError(
                f"Split '{split}' hash mismatch: selected={selected_hash} expected={expected_hash}"
            )

        base_config_path = args.config_500 if split == "paper_500" else args.config_300
        base_config = load_config(base_config_path)
        window_lookup = window_index_cache.get(base_config_path)
        if window_lookup is None:
            window_lookup = _window_id_to_index(base_config)
            window_index_cache[base_config_path] = window_lookup
        missing_window_ids = [window_id for window_id in selected_window_ids if window_id not in window_lookup]
        if missing_window_ids:
            raise RuntimeError(
                f"Split '{split}' contains {len(missing_window_ids)} window IDs missing from metric preprocessing."
            )
        selected_indices = [window_lookup[window_id] for window_id in selected_window_ids]

        split_summary = {
            "split": split,
            "rows": len(split_rows),
            "window_id_sha256": selected_hash,
            "budget_regime": args.budget_regime,
            "max_total_calls": args.resolved_max_total_calls,
            "provider": args.provider,
            "model": args.model,
            "ground_truth_counts": dict(sorted(Counter(str(row.get("ground_truth") or "unknown") for row in split_rows).items())),
            "fault_type_counts": dict(sorted(Counter(str(row.get("fault_type") or "none") for row in split_rows).items())),
            "service_count": len({str(row.get("service_id") or "") for row in split_rows}),
            "variants": [],
        }

        split_variant_summaries: dict[str, dict[str, Any]] = {}
        for variant in args.variants:
            cache_path, cache_state = _activate_variant_cache(args, split, variant)
            config = _step7_config(base_config, variant, output_dir, audit_dir, args)
            output_mode = f"step7_view_a_{args.budget_regime}_{split}_{variant}"
            records, _ = run_pipeline(config, "hybrid", output_mode=output_mode, window_indices=selected_indices)
            summary = summarize(records)
            _add_cost_estimate(summary, config)
            summary["budget_regime"] = args.budget_regime
            summary["max_total_calls"] = args.resolved_max_total_calls
            summary["cache_path"] = str(cache_path) if cache_path else None
            summary["cache_state_at_start"] = cache_state
            split_variant_summaries[variant] = summary

            result_root = output_dir
            split_summary["variants"].append(
                {
                    "variant": variant,
                    "output_mode": output_mode,
                    "cache_path": str(cache_path) if cache_path else None,
                    "cache_state_at_start": cache_state,
                    "summary": summary,
                    "artifacts": {
                        "results_json": str(result_root / f"{output_mode}_results.json"),
                        "summary_csv": str(result_root / f"{output_mode}_summary.csv"),
                        "summary_md": str(result_root / f"{output_mode}_summary.md"),
                        "audit_jsonl": str(audit_dir / f"{output_mode}_audit.jsonl"),
                    },
                }
            )
            variant_rows.append(
                {
                    "split": split,
                    "budget_regime": args.budget_regime,
                    "max_total_calls": args.resolved_max_total_calls,
                    "variant": variant,
                    "windows": summary.get("evaluated_windows", 0),
                    "candidate_alerts": summary.get("candidate_alerts", 0),
                    "precision": summary.get("precision", 0),
                    "recall": summary.get("recall", 0),
                    "f1": summary.get("f1", 0),
                    "false_positive_rate": summary.get("false_positive_rate", 0),
                    "manual_reviews": summary.get("manual_reviews", 0),
                    "manual_review_rate": summary.get("manual_review_rate", 0),
                    "automation_coverage": summary.get("automation_coverage", 0),
                    "selective_precision": summary.get("selective_precision", 0),
                    "selective_recall": summary.get("selective_recall", 0),
                    "selective_f1": summary.get("selective_f1", 0),
                    "llm_conditional_precision": summary.get("llm_conditional_precision", 0),
                    "llm_conditional_recall": summary.get("llm_conditional_recall", 0),
                    "llm_conditional_f1": summary.get("llm_conditional_f1", 0),
                    "llm_calls": summary.get("llm_calls", 0),
                    "actual_api_calls": summary.get("actual_api_calls", 0),
                    "llm_cache_hits": summary.get("llm_cache_hits", 0),
                    "cache_hit_rate": summary.get("cache_hit_rate", 0),
                    "context_coverage_rate": summary.get("context_coverage_rate", 0),
                    "retrieval_attempts": summary.get("retrieval_attempts", 0),
                    "retrieval_successes": summary.get("retrieval_successes", 0),
                    "retrieval_attempt_coverage_rate": summary.get("retrieval_attempt_coverage_rate", 0),
                    "avg_retrieved_context_count": summary.get("avg_retrieved_context_count", 0),
                    "avg_retrieval_latency_ms": summary.get("avg_retrieval_latency_ms", 0),
                    "avg_llm_latency_ms": summary.get("avg_llm_latency_ms", 0),
                    "estimated_llm_cost_usd": summary.get("estimated_llm_cost_usd", 0),
                    "json_valid_rate": summary.get("json_valid_rate", 0),
                    "cache_path": str(cache_path) if cache_path else "",
                    "cache_state_at_start": cache_state,
                }
            )

        bm25_summary = split_variant_summaries.get("hybrid_bm25_top6")
        topo_summary = split_variant_summaries.get("topology_aware_fusion_top6")
        if bm25_summary and topo_summary:
            split_summary["retrieval_fair_delta_vs_bm25"] = {
                "precision_delta": round(float(topo_summary.get("precision", 0)) - float(bm25_summary.get("precision", 0)), 4),
                "recall_delta": round(float(topo_summary.get("recall", 0)) - float(bm25_summary.get("recall", 0)), 4),
                "f1_delta": round(float(topo_summary.get("f1", 0)) - float(bm25_summary.get("f1", 0)), 4),
                "false_positive_rate_delta": round(
                    float(topo_summary.get("false_positive_rate", 0)) - float(bm25_summary.get("false_positive_rate", 0)),
                    4,
                ),
                "context_coverage_delta": round(
                    float(topo_summary.get("context_coverage_rate", 0))
                    - float(bm25_summary.get("context_coverage_rate", 0)),
                    4,
                ),
                "avg_context_count_delta": round(
                    float(topo_summary.get("avg_retrieved_context_count", 0))
                    - float(bm25_summary.get("avg_retrieved_context_count", 0)),
                    4,
                ),
                "avg_retrieval_latency_ms_delta": round(
                    float(topo_summary.get("avg_retrieval_latency_ms", 0))
                    - float(bm25_summary.get("avg_retrieval_latency_ms", 0)),
                    4,
                ),
                "false_positive_reduction_vs_bm25": false_positive_reduction(bm25_summary, topo_summary),
            }

        split_reports.append(split_summary)
        _write_report(report_path, split_reports, variant_rows)

    _write_report(report_path, split_reports, variant_rows)
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "splits": args.splits,
                "variants": args.variants,
                "budget_regime": args.budget_regime,
                "max_total_calls": args.resolved_max_total_calls,
            },
            indent=2,
        )
    )
    return 0


def _step7_config(
    base_config: dict[str, Any],
    variant: str,
    output_dir: Path,
    audit_dir: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config.setdefault("experiment", {})["name"] = f"step7_view_a_{variant}"
    config.setdefault("evaluation", {})["output_dir"] = str(output_dir)
    config.setdefault("evaluation", {})["audit_dir"] = str(audit_dir)
    config.setdefault("evaluation", {})["max_llm_calls"] = args.resolved_max_total_calls
    llm_gate = config.setdefault("llm_gate", {})
    llm_gate["max_llm_calls_per_minute"] = args.max_llm_calls_per_minute
    llm_gate["max_total_calls"] = args.resolved_max_total_calls
    llm = config.setdefault("llm", {})
    llm["provider"] = args.provider
    llm["model"] = args.model
    llm["max_output_tokens"] = args.max_output_tokens
    llm["timeout_seconds"] = args.timeout_seconds
    llm["max_retries"] = args.max_retries
    llm["input_cost_per_1m_tokens"] = args.input_cost_per_1m_tokens
    llm["output_cost_per_1m_tokens"] = args.output_cost_per_1m_tokens
    llm["cost_pricing_source"] = args.cost_pricing_source
    retrieval = config.setdefault("retrieval", {})
    if variant == "hybrid_bm25_top6":
        retrieval["backend"] = "hybrid_bm25"
        retrieval["vector_db"] = "hybrid_bm25"
        retrieval["top_k"] = 6
    elif variant == "topology_aware_fusion_top6":
        retrieval["backend"] = "topology_aware_fusion"
        retrieval["vector_db"] = "topology_aware_fusion"
        retrieval["lexical_backend"] = "hybrid_bm25"
        retrieval["top_k"] = 6
    else:
        raise ValueError(f"Unsupported variant: {variant}")
    return config


def _resolve_max_total_calls(args: argparse.Namespace) -> int:
    if args.max_total_calls is not None:
        if args.max_total_calls <= 0:
            raise ValueError("--max-total-calls must be positive")
        return args.max_total_calls
    if args.budget_regime == "operational_budget_120":
        return 120
    if args.budget_regime == "quality_full_budget":
        return 500
    raise ValueError("--max-total-calls is required when --budget-regime=custom")


def _activate_variant_cache(
    args: argparse.Namespace,
    split: str,
    variant: str,
) -> tuple[Path | None, str]:
    cache_path: Path | None = None
    if args.cache_dir:
        cache_path = _abs_path(args.cache_dir) / split / f"{variant}.jsonl"
    elif args.cache_path:
        base_path = _abs_path(args.cache_path)
        if len(args.splits) == 1 and len(args.variants) == 1:
            cache_path = base_path
        else:
            cache_path = base_path.with_name(
                f"{base_path.stem}_{split}_{variant}{base_path.suffix or '.jsonl'}"
            )

    cache_state = "disabled"
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_state = "existing" if cache_path.exists() else "fresh"
        if cache_path.exists() and not args.allow_existing_cache:
            raise RuntimeError(
                f"Cache already exists for {split}/{variant}: {cache_path}. "
                "Use a new --cache-dir or pass --allow-existing-cache for replay."
            )
        os.environ["LLM_RESPONSE_CACHE"] = str(cache_path)
    else:
        os.environ["LLM_RESPONSE_CACHE"] = "off"

    from src.llm import response_cache

    response_cache.reset_global_cache_for_tests()
    return cache_path, cache_state


def _window_id_to_index(config: dict[str, Any]) -> dict[str, int]:
    metrics = load_metrics(config["data"]["metric_path"])
    windows = create_metric_windows(
        metrics,
        int(config["preprocessing"]["window_size"]),
        int(config["preprocessing"]["stride"]),
        str(config["preprocessing"]["normalization"]),
    )
    window_lookup: dict[str, int] = {}
    for index, window in enumerate(windows):
        window_lookup[window.window_id] = index
    return window_lookup


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


def _write_report(path: Path, split_reports: list[dict[str, Any]], variant_rows: list[dict[str, Any]]) -> None:
    report = {"split_reports": split_reports, "rows": variant_rows}
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_report_csv(path.with_suffix(".csv"), variant_rows)
    _write_report_markdown(path.with_suffix(".md"), split_reports, variant_rows)


def _write_report_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "split",
        "budget_regime",
        "max_total_calls",
        "variant",
        "windows",
        "candidate_alerts",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "manual_reviews",
        "manual_review_rate",
        "automation_coverage",
        "selective_precision",
        "selective_recall",
        "selective_f1",
        "llm_conditional_precision",
        "llm_conditional_recall",
        "llm_conditional_f1",
        "llm_calls",
        "actual_api_calls",
        "llm_cache_hits",
        "cache_hit_rate",
        "context_coverage_rate",
        "retrieval_attempts",
        "retrieval_successes",
        "retrieval_attempt_coverage_rate",
        "avg_retrieved_context_count",
        "avg_retrieval_latency_ms",
        "avg_llm_latency_ms",
        "estimated_llm_cost_usd",
        "json_valid_rate",
        "cache_path",
        "cache_state_at_start",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_report_markdown(path: Path, split_reports: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Step 7 View A Report",
        "",
        "| Split | Regime | Variant | Windows | Precision | Recall | F1 | FPR | Manual Review | Auto Coverage | Selective F1 | LLM F1 | LLM Calls | API Calls | Cache Hits | Candidate Ctx Coverage | Retrieval Attempt Coverage | Est. Cost USD |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {split} | {budget_regime} | {variant} | {windows} | {precision} | {recall} | {f1} | {false_positive_rate} | {manual_review_rate} | {automation_coverage} | {selective_f1} | {llm_conditional_f1} | {llm_calls} | {actual_api_calls} | {llm_cache_hits} | {context_coverage_rate} | {retrieval_attempt_coverage_rate} | {estimated_llm_cost_usd} |".format(
                **row
            )
        )
    lines.append("")
    for split_report in split_reports:
        lines.append(f"## {split_report['split']}")
        lines.append("")
        lines.append(f"- Window rows: {split_report['rows']}")
        lines.append(f"- Window hash: `{split_report['window_id_sha256']}`")
        lines.append(
            f"- Budget regime: `{split_report['budget_regime']}` "
            f"(`max_total_calls={split_report['max_total_calls']}`)"
        )
        lines.append(f"- LLM: `{split_report['provider']}/{split_report['model']}`")
        lines.append(f"- Service count: {split_report['service_count']}")
        lines.append(f"- Ground truth counts: `{json.dumps(split_report['ground_truth_counts'], ensure_ascii=False)}`")
        lines.append(f"- Fault type counts: `{json.dumps(split_report['fault_type_counts'], ensure_ascii=False)}`")
        delta = split_report.get("retrieval_fair_delta_vs_bm25")
        if delta:
            lines.append(
                "- Topology delta vs BM25: "
                f"precision {delta['precision_delta']}, recall {delta['recall_delta']}, "
                f"f1 {delta['f1_delta']}, fpr {delta['false_positive_rate_delta']}, "
                f"context coverage {delta['context_coverage_delta']}, avg ctx {delta['avg_context_count_delta']}, "
                f"retrieval ms {delta['avg_retrieval_latency_ms_delta']}."
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _sha256_strings(values: list[str]) -> str:
    hasher = hashlib.sha256()
    for value in values:
        hasher.update(value.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def _abs_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return ROOT / candidate


if __name__ == "__main__":
    raise SystemExit(main())
