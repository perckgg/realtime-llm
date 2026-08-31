from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib


matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


METHOD_LABELS = {
    "detector_only": "Detector-only",
    "llm_without_rag": "LLM without RAG",
    "hybrid_bm25_top6": "BM25 RAG top-6",
    "hybrid_bm25_top10": "BM25 RAG top-10",
    "topology_aware_fusion_top6": "Topology-Aware Fusion top-6",
    "phase5_context_rescue": "Context Rescue [architecture-enhanced]",
}

VIEW_A_REPORTS = {
    "operational_budget_120": (
        ROOT / "outputs/phase2/step7_rerun/operational_budget_120/step7_view_a_report.csv"
    ),
    "quality_full_budget": (
        ROOT / "outputs/phase2/step7_rerun/quality_full_budget/step7_view_a_report.csv"
    ),
}
VIEW_B_REPORT = ROOT / "outputs/phase2/step7_view_b/step7_view_b_report.json"

ARCHITECTURE_SUMMARIES = {
    "detector_only": ROOT
    / "nezha_setup/outputs/phase4_benchmark/results/detector_only_summary.csv",
    "llm_without_rag": ROOT
    / "nezha_setup/outputs/phase4_benchmark/results/llm_without_rag_summary.csv",
    "hybrid_bm25_top6": ROOT
    / "nezha_setup/outputs/phase4_benchmark/results/hybrid_bm25_top6_summary.csv",
    "hybrid_bm25_top10": ROOT
    / "nezha_setup/outputs/phase4_benchmark/results/hybrid_bm25_top10_summary.csv",
    "phase5_context_rescue": ROOT
    / "nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.csv",
}

ARCHITECTURE_AUDITS = {
    "detector_only": ROOT
    / "nezha_setup/outputs/phase4_benchmark/audit/detector_only_audit.jsonl",
    "llm_without_rag": ROOT
    / "nezha_setup/outputs/phase4_benchmark/audit/llm_without_rag_audit.jsonl",
    "hybrid_bm25_top6": ROOT
    / "nezha_setup/outputs/phase4_benchmark/audit/hybrid_bm25_top6_audit.jsonl",
    "hybrid_bm25_top10": ROOT
    / "nezha_setup/outputs/phase4_benchmark/audit/hybrid_bm25_top10_audit.jsonl",
    "phase5_context_rescue": ROOT
    / "nezha_setup/outputs/phase5_context_rescue/audit/hybrid_audit.jsonl",
}

FAULT_SPECS = [
    (
        "view_a_retrieval_fair",
        "paper_500",
        "quality_full_budget",
        "hybrid_bm25_top6",
        ROOT
        / "outputs/phase2/step7_rerun/quality_full_budget/results/"
        "step7_view_a_quality_full_budget_paper_500_hybrid_bm25_top6_by_fault_type.csv",
        ROOT
        / "outputs/phase2/step7_rerun/quality_full_budget/audit/"
        "step7_view_a_quality_full_budget_paper_500_hybrid_bm25_top6_audit.jsonl",
    ),
    (
        "view_a_retrieval_fair",
        "paper_500",
        "quality_full_budget",
        "topology_aware_fusion_top6",
        ROOT
        / "outputs/phase2/step7_rerun/quality_full_budget/results/"
        "step7_view_a_quality_full_budget_paper_500_topology_aware_fusion_top6_by_fault_type.csv",
        ROOT
        / "outputs/phase2/step7_rerun/quality_full_budget/audit/"
        "step7_view_a_quality_full_budget_paper_500_topology_aware_fusion_top6_audit.jsonl",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate claim-safe Phase 2 paper tables and figures."
    )
    parser.add_argument("--output-root", default="outputs\\phase2")
    parser.add_argument("--dpi", type=int, default=180)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = ROOT / args.output_root
    table_dir = output_root / "paper_tables"
    figure_dir = output_root / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    validate_baseline_reference(ROOT / "outputs/phase2/baseline_reference.csv")
    main_rows = build_main_result_rows()
    fault_rows = build_fault_type_rows()
    ablation_rows = build_ablation_rows(
        read_csv(ROOT / "outputs/phase2/ablation/alpha_beta_gamma_ablation.csv")
    )
    cost_rows = build_cost_latency_rows()

    write_csv(table_dir / "main_result_table.csv", main_rows)
    write_csv(table_dir / "fault_type_breakdown.csv", fault_rows)
    write_csv(table_dir / "ablation_table.csv", ablation_rows)
    write_csv(table_dir / "cost_latency_table.csv", cost_rows)

    full_budget_rows = [
        row
        for row in read_csv(VIEW_A_REPORTS["quality_full_budget"])
        if row["split"] == "paper_500"
    ]
    plot_f1_comparison(full_budget_rows, figure_dir / "f1_comparison.png", args.dpi)
    plot_context_coverage(
        full_budget_rows,
        figure_dir / "context_coverage_comparison.png",
        args.dpi,
    )
    plot_network_delay_recall(
        fault_rows,
        figure_dir / "network_delay_recall.png",
        args.dpi,
    )
    plot_ablation(
        ablation_rows,
        figure_dir / "alpha_beta_gamma_ablation.png",
        args.dpi,
    )
    plot_service_graph(
        ROOT / "outputs/phase2/service_graph_edges.csv",
        figure_dir / "service_graph_example.png",
        args.dpi,
    )

    expected = [
        table_dir / "main_result_table.csv",
        table_dir / "fault_type_breakdown.csv",
        table_dir / "ablation_table.csv",
        table_dir / "cost_latency_table.csv",
        figure_dir / "f1_comparison.png",
        figure_dir / "context_coverage_comparison.png",
        figure_dir / "network_delay_recall.png",
        figure_dir / "alpha_beta_gamma_ablation.png",
        figure_dir / "service_graph_example.png",
    ]
    validate_outputs(expected)
    print(json.dumps({"generated": [str(path.relative_to(ROOT)) for path in expected]}, indent=2))
    return 0


def build_main_result_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for regime, path in VIEW_A_REPORTS.items():
        for source in read_csv(path):
            if source["split"] != "paper_500":
                continue
            method = source["variant"]
            rows.append(
                {
                    "comparison_view": "view_a_retrieval_fair",
                    "split": source["split"],
                    "budget_regime": regime,
                    "method": METHOD_LABELS[method],
                    "evaluation_level": "llm_decision",
                    "architecture_enhanced": "false",
                    "precision": source["precision"],
                    "recall": source["recall"],
                    "f1": source["f1"],
                    "fpr": source["false_positive_rate"],
                    "context_coverage": source["context_coverage_rate"],
                    "avg_retrieval_latency_ms": source["avg_retrieval_latency_ms"],
                    "llm_calls": source["llm_calls"],
                    "comparability_note": (
                        "same frozen windows, top_k, LLM model, budget, and policy "
                        "within this regime"
                    ),
                    "source": relative(path),
                }
            )

    if VIEW_B_REPORT.exists():
        report = json.loads(VIEW_B_REPORT.read_text(encoding="utf-8"))
        for source in report["rows"]:
            rows.append(
                {
                    "comparison_view": "view_b_architecture_level",
                    "split": source["split"],
                    "budget_regime": source["budget_regime"],
                    "method": source["method"],
                    "evaluation_level": "llm_decision",
                    "architecture_enhanced": str(
                        bool(source["architecture_enhanced"])
                    ).lower(),
                    "precision": source["precision"],
                    "recall": source["recall"],
                    "f1": source["f1"],
                    "fpr": source["false_positive_rate"],
                    "context_coverage": source["context_coverage_rate"],
                    "avg_retrieval_latency_ms": source[
                        "avg_retrieval_latency_ms"
                    ],
                    "llm_calls": source["llm_calls"],
                    "comparability_note": (
                        "same frozen paper_500 split, Gemini model and operational "
                        "budget; architectures intentionally differ"
                    ),
                    "source": relative(VIEW_B_REPORT.with_suffix(".csv")),
                }
            )
    else:
        rows.extend(build_legacy_architecture_rows())
    return rows


def build_fault_type_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = list(FAULT_SPECS)
    if VIEW_B_REPORT.exists():
        report = json.loads(VIEW_B_REPORT.read_text(encoding="utf-8"))
        for variant in report["variants"]:
            specs.append(
                (
                    "view_b_architecture_level",
                    report["protocol"]["split"],
                    report["protocol"]["budget_regime"],
                    variant["variant"],
                    Path(variant["artifacts"]["by_fault_type_csv"]),
                    Path(variant["artifacts"]["audit_jsonl"]),
                )
            )
    for view, split, regime, method, metrics_path, audit_path in specs:
        coverage = audit_context_coverage_by_fault(audit_path)
        for source in read_csv(metrics_path):
            fault_type = source["fault_type"]
            coverage_row = coverage.get(fault_type, {})
            rows.append(
                {
                    "comparison_view": view,
                    "split": split,
                    "budget_regime": regime,
                    "method": method_label(method),
                    "architecture_enhanced": str(
                        method in {"phase5_context_rescue", "context_rescue"}
                    ).lower(),
                    "fault_type": fault_type,
                    "precision": source["precision"],
                    "recall": source["recall"],
                    "f1": source["f1"],
                    "fp": source["fp"],
                    "fn": source["fn"],
                    "candidate_alerts": source.get("candidate_alerts", ""),
                    "llm_calls": source.get("llm_calls", ""),
                    "context_coverage": coverage_row.get("coverage", ""),
                    "context_coverage_denominator": coverage_row.get("attempts", 0),
                    "source": relative(metrics_path),
                }
            )
    return rows


def build_ablation_rows(source_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for source in source_rows:
        rows.append(
            {
                "evaluation_level": "retrieval_only",
                "phase": source["phase"],
                "split": source["split"],
                "setting": source["setting"],
                "setting_description": source["setting_description"],
                "alpha": source["alpha"],
                "beta": source["beta"],
                "gamma": source["gamma"],
                "precision": "",
                "recall": "",
                "f1": "",
                "fpr": "",
                "coverage": source["service_context_coverage"],
                "coverage_definition": "all-window service-context coverage",
                "latency_ms": source["avg_retrieval_latency_ms"],
                "network_delay_recall": source["network_delay_service_context_coverage"],
                "network_delay_recall_type": "retrieval service-context recall",
                "topology_expanded_context_ratio": source["topology_expanded_context_ratio"],
                "decision_metrics_status": "not_measured_in_retrieval_only_ablation",
                "source": "outputs/phase2/ablation/alpha_beta_gamma_ablation.csv",
            }
        )
    return rows


def build_cost_latency_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for regime, path in VIEW_A_REPORTS.items():
        for source in read_csv(path):
            if source["split"] != "paper_500":
                continue
            rows.append(
                {
                    "comparison_view": "view_a_retrieval_fair",
                    "split": source["split"],
                    "budget_regime": regime,
                    "method": METHOD_LABELS[source["variant"]],
                    "architecture_enhanced": "false",
                    "llm_calls": source["llm_calls"],
                    "actual_api_calls": source["actual_api_calls"],
                    "cache_hits": source["llm_cache_hits"],
                    "cache_hit_rate": source["cache_hit_rate"],
                    "json_valid_rate": source["json_valid_rate"],
                    "avg_llm_latency_ms": source["avg_llm_latency_ms"],
                    "estimated_cost_usd": source["estimated_llm_cost_usd"],
                    "source": relative(path),
                }
            )

    if VIEW_B_REPORT.exists():
        report = json.loads(VIEW_B_REPORT.read_text(encoding="utf-8"))
        for source in report["rows"]:
            rows.append(
                {
                    "comparison_view": "view_b_architecture_level",
                    "split": source["split"],
                    "budget_regime": source["budget_regime"],
                    "method": source["method"],
                    "architecture_enhanced": str(
                        bool(source["architecture_enhanced"])
                    ).lower(),
                    "llm_calls": source["llm_calls"],
                    "actual_api_calls": source["actual_api_calls"],
                    "cache_hits": source["llm_cache_hits"],
                    "cache_hit_rate": source["cache_hit_rate"],
                    "json_valid_rate": source["json_valid_rate"],
                    "avg_llm_latency_ms": source["avg_llm_latency_ms"],
                    "estimated_cost_usd": source["estimated_llm_cost_usd"],
                    "source": relative(VIEW_B_REPORT.with_suffix(".csv")),
                }
            )
    else:
        rows.extend(build_legacy_cost_rows())
    return rows


def build_legacy_architecture_rows() -> list[dict[str, Any]]:
    rows = []
    for method, path in ARCHITECTURE_SUMMARIES.items():
        source = read_single_row(path)
        rows.append(
            {
                "comparison_view": "architecture_reference",
                "split": "phase4_300",
                "budget_regime": "legacy_reference",
                "method": METHOD_LABELS[method],
                "evaluation_level": "llm_decision",
                "architecture_enhanced": str(
                    method == "phase5_context_rescue"
                ).lower(),
                "precision": source["precision"],
                "recall": source["recall"],
                "f1": source["f1"],
                "fpr": source["false_positive_rate"],
                "context_coverage": source.get("context_coverage_rate", ""),
                "avg_retrieval_latency_ms": source.get(
                    "avg_retrieval_latency_ms", ""
                ),
                "llm_calls": source.get("llm_calls", "0"),
                "comparability_note": (
                    "architecture-level reference only; not directly comparable "
                    "with paper_500 View A"
                ),
                "source": relative(path),
            }
        )
    return rows


def build_legacy_cost_rows() -> list[dict[str, Any]]:
    rows = []
    for method, path in ARCHITECTURE_SUMMARIES.items():
        source = read_single_row(path)
        audit = summarize_audit(ARCHITECTURE_AUDITS[method])
        rows.append(
            {
                "comparison_view": "architecture_reference",
                "split": "phase4_300",
                "budget_regime": "legacy_reference",
                "method": METHOD_LABELS[method],
                "architecture_enhanced": str(
                    method == "phase5_context_rescue"
                ).lower(),
                "llm_calls": source.get("llm_calls", "0"),
                "actual_api_calls": audit["actual_api_calls"],
                "cache_hits": audit["cache_hits"],
                "cache_hit_rate": audit["cache_hit_rate"],
                "json_valid_rate": source.get(
                    "json_valid_rate", audit["json_valid_rate"]
                ),
                "avg_llm_latency_ms": source.get(
                    "avg_llm_latency_ms", audit["avg_llm_latency_ms"]
                ),
                "estimated_cost_usd": source.get(
                    "estimated_llm_cost_usd", ""
                ),
                "source": relative(path),
            }
        )
    return rows


def method_label(method: str) -> str:
    if method == "context_rescue":
        return "Context Rescue [architecture-enhanced]"
    return METHOD_LABELS[method]


def audit_context_coverage_by_fault(path: Path) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "covered": 0})
    records = list(read_jsonl(path))
    has_explicit_attempt_field = any("retrieval_attempted" in record for record in records)
    has_retrieval_activity = any(
        int(record.get("retrieved_context_count", 0)) > 0
        or float(record.get("retrieval_latency_ms", 0.0)) > 0.0
        for record in records
    )
    for record in records:
        attempted = (
            bool(record.get("retrieval_attempted", False))
            if has_explicit_attempt_field
            else bool(record.get("is_candidate", False) and has_retrieval_activity)
        )
        if not attempted:
            continue
        fault_type = str(record.get("fault_type", "unknown"))
        counts[fault_type]["attempts"] += 1
        covered = bool(
            record.get(
                "context_coverage",
                int(record.get("retrieved_context_count", 0)) > 0,
            )
        )
        counts[fault_type]["covered"] += int(covered)
    return {
        fault_type: {
            **values,
            "coverage": round(values["covered"] / values["attempts"], 4)
            if values["attempts"]
            else "",
        }
        for fault_type, values in counts.items()
    }


def summarize_audit(path: Path) -> dict[str, Any]:
    records = list(read_jsonl(path))
    llm_records = [record for record in records if record.get("llm_called", False)]
    actual_api_calls = sum(
        int(record.get("actual_api_calls", int(bool(record.get("actual_api_call", False)))))
        for record in records
    )
    cache_hits = sum(
        int(record.get("cache_hits", int(bool(record.get("llm_cache_hit", False)))))
        for record in records
    )
    llm_latencies = [
        float(record.get("llm_latency_ms", 0.0))
        for record in llm_records
        if record.get("llm_latency_ms") is not None
    ]
    return {
        "actual_api_calls": actual_api_calls,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / len(llm_records), 4) if llm_records else 0.0,
        "json_valid_rate": round(
            sum(int(bool(record.get("json_valid", False))) for record in llm_records)
            / len(llm_records),
            4,
        )
        if llm_records
        else "",
        "avg_llm_latency_ms": round(sum(llm_latencies) / len(llm_latencies), 4)
        if llm_latencies
        else 0.0,
    }


def plot_f1_comparison(rows: list[dict[str, str]], path: Path, dpi: int) -> None:
    labels = [METHOD_LABELS[row["variant"]] for row in rows]
    values = [float(row["f1"]) for row in rows]
    figure, axis = plt.subplots(figsize=(7.2, 4.6))
    bars = axis.bar(labels, values, color=["#4C78A8", "#F58518"])
    style_metric_axis(axis, "LLM decision F1", "Step 7 View A: F1 (paper_500, full budget)")
    annotate_bars(axis, bars, values)
    save_figure(figure, path, dpi)


def plot_context_coverage(rows: list[dict[str, str]], path: Path, dpi: int) -> None:
    labels = [METHOD_LABELS[row["variant"]] for row in rows]
    values = [float(row["context_coverage_rate"]) for row in rows]
    figure, axis = plt.subplots(figsize=(7.2, 4.6))
    bars = axis.bar(labels, values, color=["#4C78A8", "#F58518"])
    style_metric_axis(
        axis,
        "Context coverage",
        "Step 7 View A: Candidate context coverage (paper_500, full budget)",
    )
    annotate_bars(axis, bars, values)
    save_figure(figure, path, dpi)


def plot_network_delay_recall(
    rows: list[dict[str, Any]], path: Path, dpi: int
) -> None:
    selected = [
        row
        for row in rows
        if row["comparison_view"] == "view_a_retrieval_fair"
        and row["fault_type"] == "network_delay"
    ]
    labels = [row["method"] for row in selected]
    values = [float(row["recall"]) for row in selected]
    figure, axis = plt.subplots(figsize=(7.2, 4.6))
    bars = axis.bar(labels, values, color=["#4C78A8", "#F58518"])
    style_metric_axis(
        axis,
        "Network-delay recall",
        "Fault-specific downstream recall (paper_500, full budget)",
    )
    annotate_bars(axis, bars, values)
    save_figure(figure, path, dpi)


def plot_ablation(rows: list[dict[str, Any]], path: Path, dpi: int) -> None:
    selected = [row for row in rows if row["phase"] == "tuning"]
    labels = [
        f"{row['setting']}\n({row['alpha']}, {row['beta']}, {row['gamma']})"
        for row in selected
    ]
    topology_ratio = [float(row["topology_expanded_context_ratio"]) for row in selected]
    latency = [float(row["latency_ms"]) for row in selected]

    figure, axis = plt.subplots(figsize=(9.0, 4.8))
    positions = list(range(len(selected)))
    bars = axis.bar(positions, topology_ratio, color="#59A14F", alpha=0.85)
    axis.set_ylabel("Topology-expanded context ratio")
    axis.set_ylim(0.0, max(0.1, max(topology_ratio) * 1.35))
    axis.set_xticks(positions, labels)
    axis.grid(axis="y", alpha=0.25)
    axis.set_title("Retrieval-only α/β/γ ablation (paper_300 tuning split)")

    latency_axis = axis.twinx()
    latency_axis.plot(positions, latency, color="#E15759", marker="o", linewidth=2)
    latency_axis.set_ylabel("Average retrieval latency (ms)")
    annotate_bars(axis, bars, topology_ratio)
    figure.tight_layout()
    save_figure(figure, path, dpi)


def plot_service_graph(edge_path: Path, path: Path, dpi: int) -> None:
    edges = [
        row
        for row in read_csv(edge_path)
        if not row["source_service"].startswith("ts-")
        and not row["target_service"].startswith("ts-")
    ][:14]
    nodes = sorted(
        {row["source_service"] for row in edges}
        | {row["target_service"] for row in edges}
    )
    angle_step = 2 * math.pi / max(1, len(nodes))
    positions = {
        node: (
            math.cos(index * angle_step),
            math.sin(index * angle_step),
        )
        for index, node in enumerate(nodes)
    }

    figure, axis = plt.subplots(figsize=(9.0, 7.0))
    axis.set_title("Service graph example: Online Boutique trace dependencies")
    axis.axis("off")
    for edge in edges:
        source = positions[edge["source_service"]]
        target = positions[edge["target_service"]]
        weight = max(1.0, float(edge["trace_count"]))
        arrow = FancyArrowPatch(
            source,
            target,
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=0.6 + math.log10(weight) * 0.25,
            color="#6B7280",
            alpha=0.58,
            connectionstyle="arc3,rad=0.06",
            shrinkA=15,
            shrinkB=15,
        )
        axis.add_patch(arrow)
    for node, (x, y) in positions.items():
        axis.scatter([x], [y], s=720, color="#4C78A8", edgecolor="white", linewidth=1.5, zorder=3)
        axis.text(x, y, node, ha="center", va="center", color="white", fontsize=7.5, zorder=4)
    axis.set_xlim(-1.25, 1.25)
    axis.set_ylim(-1.2, 1.2)
    figure.tight_layout()
    save_figure(figure, path, dpi)


def style_metric_axis(axis: Any, ylabel: str, title: str) -> None:
    axis.set_ylim(0.0, 1.0)
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.25)
    axis.tick_params(axis="x", rotation=8)


def annotate_bars(axis: Any, bars: Iterable[Any], values: list[float]) -> None:
    for bar, value in zip(bars, values):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(0.012, axis.get_ylim()[1] * 0.012),
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )


def save_figure(figure: Any, path: Path, dpi: int) -> None:
    figure.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def validate_outputs(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError(f"Missing or empty paper outputs: {missing}")


def validate_baseline_reference(path: Path) -> None:
    references = {row["baseline"]: row for row in read_csv(path)}
    for method, summary_path in ARCHITECTURE_SUMMARIES.items():
        if method not in references:
            raise ValueError(f"Missing {method} in {path}")
        reference = references[method]
        if Path(reference["summary_csv"]).as_posix() != relative(summary_path):
            raise ValueError(f"Summary path mismatch for {method} in {path}")
        if Path(reference["audit_path"]).as_posix() != relative(ARCHITECTURE_AUDITS[method]):
            raise ValueError(f"Audit path mismatch for {method} in {path}")


def read_single_row(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    if len(rows) != 1:
        raise ValueError(f"Expected one data row in {path}, found {len(rows)}")
    return rows[0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty table: {path}")
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
