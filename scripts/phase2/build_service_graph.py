from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.phase2.retrieval.graph_builder import build_service_graph, write_graph_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Phase 2 service topology graph from Nezha traces.")
    parser.add_argument("--dataset-root", default="data\\Nezha", help="Path to the raw Nezha dataset root.")
    parser.add_argument(
        "--processed-metrics",
        default="nezha_setup\\processed\\metrics.csv",
        help="Processed metrics CSV used to include services that may not appear in trace edges.",
    )
    parser.add_argument(
        "--processed-logs",
        default="nezha_setup\\processed\\logs.jsonl",
        help="Processed context JSONL used to include services that may not appear in trace edges.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs\\phase2",
        help="Output directory for service_graph_* artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_root = ROOT / args.dataset_root
    processed_metrics = ROOT / args.processed_metrics if args.processed_metrics else None
    processed_logs = ROOT / args.processed_logs if args.processed_logs else None
    output_dir = ROOT / args.output_dir

    graph = build_service_graph(
        dataset_root=dataset_root,
        processed_metrics_path=processed_metrics,
        processed_logs_path=processed_logs,
    )
    write_graph_outputs(graph, output_dir)
    print(
        json.dumps(
            {
                "service_count": graph.summary["service_count"],
                "directed_edge_count": graph.summary["directed_edge_count"],
                "undirected_edge_count": graph.summary["undirected_edge_count"],
                "trace_files": graph.summary["trace_files"],
                "trace_rows": graph.summary["trace_rows"],
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
