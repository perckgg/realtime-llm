from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.models import AlertCandidate
from src.phase2.retrieval.fusion_ranker import FusionWeights
from src.phase2.retrieval.topology_aware_retriever import TopologyAwareRetriever
from src.phase2.retrieval.topology_candidate_expander import ServiceTopology
from src.preprocessing.log_preprocessing import preprocess_logs
from src.retrieval.context_store import LocalContextStore


WINDOW_TIMES_RE = re.compile(
    r"(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)-"
    r"(?P<end>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 topology-aware retrieval debug on frozen windows.")
    parser.add_argument("--window-index", default="outputs\\phase2\\window_index.csv")
    parser.add_argument("--split", default="debug_50")
    parser.add_argument("--logs", default="nezha_setup\\processed\\logs.jsonl")
    parser.add_argument("--graph", default="outputs\\phase2\\service_graph_undirected.json")
    parser.add_argument("--output-dir", default="outputs\\phase2\\retrieval")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--bm25-k", type=int, default=60)
    parser.add_argument("--graph-max-distance", type=int, default=2)
    parser.add_argument("--graph-per-service-limit", type=int, default=20)
    parser.add_argument("--alpha", type=float, default=0.4)
    parser.add_argument("--beta", type=float, default=0.3)
    parser.add_argument("--gamma", type=float, default=0.3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    store = LocalContextStore(vector_db="hybrid_bm25")
    store.add_events(preprocess_logs(read_jsonl(ROOT / args.logs)))
    topology = ServiceTopology.from_undirected_json(ROOT / args.graph)
    retriever = TopologyAwareRetriever(
        store=store,
        topology=topology,
        top_k=args.top_k,
        bm25_k=args.bm25_k,
        graph_max_distance=args.graph_max_distance,
        graph_per_service_limit=args.graph_per_service_limit,
        weights=FusionWeights(args.alpha, args.beta, args.gamma),
    )

    alerts = read_alerts(ROOT / args.window_index, args.split)
    candidate_debug_path = output_dir / "candidate_pool_debug.jsonl"
    topk_path = output_dir / "topk_contexts_debug.jsonl"

    with candidate_debug_path.open("w", encoding="utf-8") as candidate_file, topk_path.open(
        "w", encoding="utf-8"
    ) as topk_file:
        for alert in alerts:
            contexts, debug = retriever.retrieve(alert)
            candidate_file.write(json.dumps(debug.to_dict(), ensure_ascii=False) + "\n")
            for context in contexts:
                topk_file.write(json.dumps(context, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "split": args.split,
                "alerts": len(alerts),
                "contexts": line_count(topk_path),
                "candidate_pool_debug": str(candidate_debug_path),
                "topk_contexts_debug": str(topk_path),
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


def read_alerts(path: Path, split: str) -> list[AlertCandidate]:
    alerts = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("split") != split:
                continue
            window_id = str(row.get("window_id") or "")
            time_window = parse_time_window(window_id)
            alerts.append(
                AlertCandidate(
                    alert_id=str(row.get("alert_id") or ""),
                    window_id=window_id,
                    time_window=time_window,
                    node_id=str(row.get("node_id") or ""),
                    service_id=str(row.get("service_id") or ""),
                    anomaly_score=float(row.get("anomaly_score") or 0.0),
                    metric_snapshot={},
                    detector_label="phase2_debug",
                    top_features=[],
                    ground_truth=str(row.get("ground_truth") or "unknown"),
                    fault_type=str(row.get("fault_type") or "none"),
                )
            )
    return alerts


def parse_time_window(window_id: str) -> dict[str, str]:
    match = WINDOW_TIMES_RE.search(window_id)
    if not match:
        raise ValueError(f"Cannot parse start/end timestamps from window_id: {window_id}")
    return {"start": match.group("start"), "end": match.group("end")}


def line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


if __name__ == "__main__":
    raise SystemExit(main())
