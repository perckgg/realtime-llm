from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.models import AlertCandidate
from src.phase2.evaluation.retrieval_metrics import group_summaries, summarize_retrieval
from src.phase2.retrieval.fusion_ranker import FusionWeights
from src.phase2.retrieval.topology_aware_retriever import TopologyAwareRetriever
from src.phase2.retrieval.topology_candidate_expander import ServiceTopology
from src.preprocessing.log_preprocessing import preprocess_logs
from src.retrieval.context_store import LocalContextStore


WINDOW_TIMES_RE = re.compile(
    r"(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)-"
    r"(?P<end>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$"
)


@dataclass(frozen=True)
class AblationSetting:
    setting: str
    description: str
    weights: FusionWeights
    graph_per_service_limit: int


ABLATION_SETTINGS = [
    AblationSetting("A0_bm25_only", "BM25 only", FusionWeights(1.0, 0.0, 0.0), 0),
    AblationSetting("A1_bm25_time", "BM25 + Time", FusionWeights(0.5, 0.5, 0.0), 0),
    AblationSetting("A2_bm25_graph", "BM25 + Graph", FusionWeights(0.5, 0.0, 0.5), 20),
    AblationSetting("A3_balanced", "Balanced", FusionWeights(0.4, 0.3, 0.3), 20),
    AblationSetting("A4_topology_heavy", "Topology-heavy", FusionWeights(0.35, 0.25, 0.4), 20),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 Level C alpha/beta/gamma retrieval ablation.")
    parser.add_argument("--window-index", default="outputs\\phase2\\window_index.csv")
    parser.add_argument("--logs", default="nezha_setup\\processed\\logs.jsonl")
    parser.add_argument("--graph", default="outputs\\phase2\\service_graph_undirected.json")
    parser.add_argument("--output-dir", default="outputs\\phase2\\ablation")
    parser.add_argument("--tuning-split", default="paper_300")
    parser.add_argument("--confirmation-split", default="paper_500")
    parser.add_argument("--confirm-count", type=int, default=2)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--bm25-k", type=int, default=60)
    parser.add_argument("--graph-max-distance", type=int, default=2)
    parser.add_argument("--tau-seconds", type=float, default=300.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    alerts_by_split = read_alerts_by_split(
        ROOT / args.window_index,
        {args.tuning_split, args.confirmation_split},
    )
    store = LocalContextStore(vector_db="hybrid_bm25")
    store.add_events(preprocess_logs(read_jsonl(ROOT / args.logs)))
    topology = ServiceTopology.from_undirected_json(ROOT / args.graph)

    tuning_records = run_settings(
        split=args.tuning_split,
        alerts=alerts_by_split.get(args.tuning_split, []),
        settings=ABLATION_SETTINGS,
        store=store,
        topology=topology,
        args=args,
        phase="tuning",
    )
    tuning_summary = summarize_by_setting(tuning_records)
    selected_setting_names = select_confirmation_settings(tuning_summary, args.confirm_count)
    selected_settings = [setting for setting in ABLATION_SETTINGS if setting.setting in selected_setting_names]
    confirmation_records = run_settings(
        split=args.confirmation_split,
        alerts=alerts_by_split.get(args.confirmation_split, []),
        settings=selected_settings,
        store=store,
        topology=topology,
        args=args,
        phase="confirmation",
    )

    all_records = tuning_records + confirmation_records
    summary_rows = summarize_by_setting(all_records)
    write_rows(output_dir / "alpha_beta_gamma_ablation.csv", summary_rows)
    write_breakdown_csv(output_dir / "ablation_by_fault_type.csv", all_records, "fault_type")
    write_breakdown_csv(output_dir / "ablation_network_delay_breakdown.csv", all_records, "fault_group")
    write_topk_contexts(output_dir / "ablation_topk_contexts.jsonl", all_records)
    write_metadata(output_dir / "ablation_selected_settings.json", args, selected_setting_names)
    write_summary_markdown(output_dir / "ablation_summary.md", summary_rows, selected_setting_names, args)

    print(
        json.dumps(
            {
                "tuning_split": args.tuning_split,
                "confirmation_split": args.confirmation_split,
                "tuning_settings": [setting.setting for setting in ABLATION_SETTINGS],
                "selected_confirmation_settings": selected_setting_names,
                "window_setting_records": len(all_records),
                "topk_contexts": sum(len(record["contexts"]) for record in all_records),
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )
    return 0


def run_settings(
    split: str,
    alerts: list[AlertCandidate],
    settings: list[AblationSetting],
    store: LocalContextStore,
    topology: ServiceTopology,
    args: argparse.Namespace,
    phase: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for setting in settings:
        retriever = TopologyAwareRetriever(
            store=store,
            topology=topology,
            top_k=args.top_k,
            bm25_k=args.bm25_k,
            graph_max_distance=args.graph_max_distance,
            graph_per_service_limit=setting.graph_per_service_limit,
            tau_seconds=args.tau_seconds,
            weights=setting.weights,
        )
        for alert in alerts:
            contexts, debug = retriever.retrieve(alert)
            records.append(
                {
                    "phase": phase,
                    "split": split,
                    "setting": setting.setting,
                    "setting_description": setting.description,
                    "top_k": args.top_k,
                    "alpha": setting.weights.alpha,
                    "beta": setting.weights.beta,
                    "gamma": setting.weights.gamma,
                    "window_id": alert.window_id,
                    "alert_id": alert.alert_id,
                    "service_id": alert.service_id,
                    "node_id": alert.node_id,
                    "fault_type": alert.fault_type,
                    "fault_group": "network_delay" if alert.fault_type == "network_delay" else "non_network_delay",
                    "ground_truth": alert.ground_truth,
                    "contexts": contexts,
                    **debug.to_dict(),
                }
            )
    return records


def summarize_by_setting(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    phases = ["tuning", "confirmation"]
    for phase in phases:
        phase_records = [record for record in records if record["phase"] == phase]
        for split in sorted({record["split"] for record in phase_records}):
            for setting in [setting.setting for setting in ABLATION_SETTINGS]:
                group = [
                    record
                    for record in phase_records
                    if record["split"] == split and record["setting"] == setting
                ]
                if not group:
                    continue
                first = group[0]
                rows.append(
                    {
                        "phase": phase,
                        "split": split,
                        "setting": setting,
                        "setting_description": first["setting_description"],
                        "top_k": first["top_k"],
                        "alpha": first["alpha"],
                        "beta": first["beta"],
                        "gamma": first["gamma"],
                        **summarize_retrieval(group),
                    }
                )
    return rows


def select_confirmation_settings(summary_rows: list[dict[str, Any]], confirm_count: int) -> list[str]:
    eligible = [
        row
        for row in summary_rows
        if row["phase"] == "tuning" and float(row["gamma"]) > 0.0
    ]
    ranked = sorted(
        eligible,
        key=lambda row: (
            -float(row.get("positive_service_context_coverage", 0.0)),
            -float(row.get("network_delay_service_context_coverage", 0.0)),
            -float(row.get("topology_expanded_context_ratio", 0.0)),
            -float(row.get("gamma", 0.0)),
            float(row.get("avg_retrieval_latency_ms", 0.0)),
            str(row.get("setting")),
        ),
    )
    return [str(row["setting"]) for row in ranked[: max(0, confirm_count)]]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_alerts_by_split(path: Path, splits: set[str]) -> dict[str, list[AlertCandidate]]:
    alerts_by_split: dict[str, list[AlertCandidate]] = {split: [] for split in splits}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            split = str(row.get("split") or "")
            if split not in splits:
                continue
            window_id = str(row.get("window_id") or "")
            alerts_by_split[split].append(
                AlertCandidate(
                    alert_id=str(row.get("alert_id") or ""),
                    window_id=window_id,
                    time_window=parse_time_window(window_id),
                    node_id=str(row.get("node_id") or ""),
                    service_id=str(row.get("service_id") or ""),
                    anomaly_score=float(row.get("anomaly_score") or 0.0),
                    metric_snapshot={},
                    detector_label="phase2_ablation",
                    top_features=[],
                    ground_truth=str(row.get("ground_truth") or "unknown"),
                    fault_type=str(row.get("fault_type") or "none"),
                )
            )
    return alerts_by_split


def parse_time_window(window_id: str) -> dict[str, str]:
    match = WINDOW_TIMES_RE.search(window_id)
    if not match:
        raise ValueError(f"Cannot parse start/end timestamps from window_id: {window_id}")
    return {"start": match.group("start"), "end": match.group("end")}


def write_breakdown_csv(path: Path, records: list[dict[str, Any]], group_key: str) -> None:
    rows = []
    for phase in ["tuning", "confirmation"]:
        phase_records = [record for record in records if record["phase"] == phase]
        for split in sorted({record["split"] for record in phase_records}):
            for setting in [setting.setting for setting in ABLATION_SETTINGS]:
                group = [
                    record
                    for record in phase_records
                    if record["split"] == split and record["setting"] == setting
                ]
                for summary in group_summaries(group, group_key):
                    rows.append({"phase": phase, "split": split, "setting": setting, **summary})
    write_rows(path, rows)


def write_topk_contexts(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            base = {
                key: record[key]
                for key in [
                    "phase",
                    "split",
                    "setting",
                    "setting_description",
                    "top_k",
                    "alpha",
                    "beta",
                    "gamma",
                    "window_id",
                    "alert_id",
                    "service_id",
                    "node_id",
                    "fault_type",
                    "fault_group",
                    "ground_truth",
                ]
            }
            for context in record["contexts"]:
                f.write(json.dumps({**base, **context}, ensure_ascii=False) + "\n")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metadata(path: Path, args: argparse.Namespace, selected_settings: list[str]) -> None:
    data = {
        "level": "C",
        "description": "Phase 2 alpha/beta/gamma retrieval-only ablation; no LLM/API calls.",
        "tuning_split": args.tuning_split,
        "confirmation_split": args.confirmation_split,
        "selected_confirmation_settings": selected_settings,
        "selection_rule": (
            "Select graph-enabled tuning settings by positive service coverage, network-delay service coverage, "
            "topology context ratio, gamma, and lower latency. Confirmation split is not used for tuning."
        ),
        "settings": [
            {
                "setting": setting.setting,
                "description": setting.description,
                "alpha": setting.weights.alpha,
                "beta": setting.weights.beta,
                "gamma": setting.weights.gamma,
                "graph_per_service_limit": setting.graph_per_service_limit,
            }
            for setting in ABLATION_SETTINGS
        ],
        "top_k": args.top_k,
        "bm25_k": args.bm25_k,
        "graph_max_distance": args.graph_max_distance,
        "tau_seconds": args.tau_seconds,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary_markdown(
    path: Path,
    summary_rows: list[dict[str, Any]],
    selected_settings: list[str],
    args: argparse.Namespace,
) -> None:
    lines = [
        "# Phase 2 Level C Alpha/Beta/Gamma Ablation",
        "",
        "Generated by:",
        "",
        "```powershell",
        "py scripts\\phase2\\run_alpha_beta_gamma_ablation.py",
        "```",
        "",
        "This run is retrieval-only and does not call an LLM or external API.",
        "",
        f"Tuning split: `{args.tuning_split}`. Confirmation split: `{args.confirmation_split}`.",
        f"Selected confirmation settings: `{', '.join(selected_settings)}`.",
        "",
        "## Summary",
        "",
        "| Phase | Split | Setting | alpha | beta | gamma | Windows | Service coverage | Network-delay service coverage | Topology ratio | Avg latency ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {phase} | {split} | {setting} | {alpha} | {beta} | {gamma} | {windows} | "
            "{positive_service_context_coverage:.4f} | {network_delay_service_context_coverage:.4f} | "
            "{topology_expanded_context_ratio:.4f} | {avg_retrieval_latency_ms:.4f} |".format(
                phase=row["phase"],
                split=row["split"],
                setting=row["setting"],
                alpha=row["alpha"],
                beta=row["beta"],
                gamma=row["gamma"],
                windows=row["windows"],
                positive_service_context_coverage=float(row["positive_service_context_coverage"]),
                network_delay_service_context_coverage=float(row["network_delay_service_context_coverage"]),
                topology_expanded_context_ratio=float(row["topology_expanded_context_ratio"]),
                avg_retrieval_latency_ms=float(row["avg_retrieval_latency_ms"]),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A0 and A1 are non-graph retrieval settings and act as lexical/time baselines.",
            "- A2, A3, and A4 are graph-enabled settings; confirmation uses only settings selected from the tuning split.",
            "- The confirmation split is reported as a held-out check and is not used to tune weights.",
            "",
            "Detailed outputs:",
            "",
            "```text",
            "outputs/phase2/ablation/alpha_beta_gamma_ablation.csv",
            "outputs/phase2/ablation/ablation_by_fault_type.csv",
            "outputs/phase2/ablation/ablation_network_delay_breakdown.csv",
            "outputs/phase2/ablation/ablation_topk_contexts.jsonl",
            "outputs/phase2/ablation/ablation_selected_settings.json",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
