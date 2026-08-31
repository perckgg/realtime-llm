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
class RetrievalMethod:
    method: str
    description: str
    weights: FusionWeights
    graph_per_service_limit: int


METHODS = [
    RetrievalMethod("M0_bm25_only", "BM25-only", FusionWeights(1.0, 0.0, 0.0), 0),
    RetrievalMethod("M1_bm25_time", "BM25 + TimeSim", FusionWeights(0.5, 0.5, 0.0), 0),
    RetrievalMethod("M2_bm25_graph", "BM25 + GraphSim", FusionWeights(0.5, 0.0, 0.5), 20),
    RetrievalMethod("M3_full_fusion", "BM25 + TimeSim + GraphSim", FusionWeights(0.4, 0.3, 0.3), 20),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 Level A retrieval-only evaluation.")
    parser.add_argument("--window-index", default="outputs\\phase2\\window_index.csv")
    parser.add_argument("--splits", nargs="+", default=["debug_50", "paper_300", "paper_500"])
    parser.add_argument("--logs", default="nezha_setup\\processed\\logs.jsonl")
    parser.add_argument("--graph", default="outputs\\phase2\\service_graph_undirected.json")
    parser.add_argument("--output-dir", default="outputs\\phase2\\retrieval")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--bm25-k", type=int, default=60)
    parser.add_argument("--graph-max-distance", type=int, default=2)
    parser.add_argument("--tau-seconds", type=float, default=300.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    alerts_by_split = read_alerts_by_split(ROOT / args.window_index, set(args.splits))
    store = LocalContextStore(vector_db="hybrid_bm25")
    store.add_events(preprocess_logs(read_jsonl(ROOT / args.logs)))
    topology = ServiceTopology.from_undirected_json(ROOT / args.graph)

    all_records: list[dict[str, Any]] = []
    for split in args.splits:
        alerts = alerts_by_split.get(split, [])
        for method in METHODS:
            retriever = TopologyAwareRetriever(
                store=store,
                topology=topology,
                top_k=args.top_k,
                bm25_k=args.bm25_k,
                graph_max_distance=args.graph_max_distance,
                graph_per_service_limit=method.graph_per_service_limit,
                tau_seconds=args.tau_seconds,
                weights=method.weights,
            )
            for alert in alerts:
                contexts, debug = retriever.retrieve(alert)
                all_records.append(
                    {
                        "split": split,
                        "method": method.method,
                        "method_description": method.description,
                        "top_k": args.top_k,
                        "alpha": method.weights.alpha,
                        "beta": method.weights.beta,
                        "gamma": method.weights.gamma,
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

    write_topk_contexts(output_dir / "topk_contexts.jsonl", all_records)
    write_summary_csv(output_dir / "phase2_retrieval_summary.csv", all_records)
    write_breakdown_csv(output_dir / "phase2_retrieval_by_fault_type.csv", all_records, "fault_type")
    write_breakdown_csv(output_dir / "phase2_retrieval_by_service.csv", all_records, "service_id")
    write_breakdown_csv(output_dir / "phase2_retrieval_network_delay_breakdown.csv", all_records, "fault_group")
    write_metadata(output_dir / "phase2_retrieval_run_config.json", args)

    print(
        json.dumps(
            {
                "splits": args.splits,
                "methods": [method.method for method in METHODS],
                "window_method_records": len(all_records),
                "topk_contexts": sum(len(record["contexts"]) for record in all_records),
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )
    return 0


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
                    detector_label="phase2_retrieval_only",
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


def write_topk_contexts(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            base = {
                key: record[key]
                for key in [
                    "split",
                    "method",
                    "method_description",
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


def write_summary_csv(path: Path, records: list[dict[str, Any]]) -> None:
    rows = []
    for split in sorted({record["split"] for record in records}):
        for method in [method.method for method in METHODS]:
            group = [record for record in records if record["split"] == split and record["method"] == method]
            if not group:
                continue
            first = group[0]
            rows.append(
                {
                    "split": split,
                    "method": method,
                    "method_description": first["method_description"],
                    "top_k": first["top_k"],
                    "alpha": first["alpha"],
                    "beta": first["beta"],
                    "gamma": first["gamma"],
                    **summarize_retrieval(group),
                }
            )
    write_rows(path, rows)


def write_breakdown_csv(path: Path, records: list[dict[str, Any]], group_key: str) -> None:
    rows = []
    for split in sorted({record["split"] for record in records}):
        for method in [method.method for method in METHODS]:
            group = [record for record in records if record["split"] == split and record["method"] == method]
            for summary in group_summaries(group, group_key):
                rows.append({"split": split, "method": method, **summary})
    write_rows(path, rows)


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metadata(path: Path, args: argparse.Namespace) -> None:
    data = {
        "level": "A",
        "description": "Phase 2 retrieval-only evaluation; no LLM/API calls.",
        "methods": [
            {
                "method": method.method,
                "description": method.description,
                "alpha": method.weights.alpha,
                "beta": method.weights.beta,
                "gamma": method.weights.gamma,
                "graph_per_service_limit": method.graph_per_service_limit,
            }
            for method in METHODS
        ],
        "splits": args.splits,
        "top_k": args.top_k,
        "bm25_k": args.bm25_k,
        "graph_max_distance": args.graph_max_distance,
        "tau_seconds": args.tau_seconds,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
