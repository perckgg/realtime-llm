from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.phase2.retrieval.graph_builder import build_service_graph, service_from_pod, write_graph_outputs


class Phase2GraphBuilderTest(unittest.TestCase):
    def test_service_from_pod_strips_replica_suffix(self) -> None:
        self.assertEqual(service_from_pod("ts-gateway-service-6f6cfc45b-d9pnv"), "ts-gateway-service")
        self.assertEqual(service_from_pod("frontend-579b9bff58-t2dbm"), "frontend")
        self.assertEqual(service_from_pod("service-without-pod"), "service-without-pod")

    def test_builds_cross_service_edges_from_trace_parent_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_dir = root / "rca_data" / "2023-01-30" / "trace"
            trace_dir.mkdir(parents=True)
            trace_path = trace_dir / "14_10_trace.csv"
            with trace_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "TraceID",
                        "SpanID",
                        "ParentID",
                        "PodName",
                        "OperationName",
                        "StartTimeUnixNano",
                        "EndTimeUnixNano",
                        "Duration",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "TraceID": "trace-1",
                        "SpanID": "root-span",
                        "ParentID": "root",
                        "PodName": "frontend-abcde-12345",
                        "OperationName": "GET /",
                        "StartTimeUnixNano": "1000000000",
                        "EndTimeUnixNano": "1200000000",
                        "Duration": "200000",
                    }
                )
                writer.writerow(
                    {
                        "TraceID": "trace-1",
                        "SpanID": "child-span",
                        "ParentID": "root-span",
                        "PodName": "cartservice-fghij-67890",
                        "OperationName": "POST /cart",
                        "StartTimeUnixNano": "1050000000",
                        "EndTimeUnixNano": "1150000000",
                        "Duration": "100000",
                    }
                )

            metrics_path = root / "metrics.csv"
            metrics_path.write_text(
                "timestamp,node_id,service_id,cpu,memory,network,latency,workload,success_rate_drop,inject_type,label\n"
                "2023-01-30T00:00:00Z,orphan-pod,orphan,0,0,0,0,0,0,none,normal\n",
                encoding="utf-8",
            )

            graph = build_service_graph(root, processed_metrics_path=metrics_path)
            self.assertIn(("frontend", "cartservice"), graph.edges)
            self.assertEqual(graph.edges[("frontend", "cartservice")].span_count, 1)
            self.assertIn("orphan", graph.summary["isolated_services"])

            write_graph_outputs(graph, root / "outputs")
            directed = json.loads((root / "outputs" / "service_graph_directed.json").read_text(encoding="utf-8"))
            self.assertEqual(directed["edges"][0]["source_service"], "frontend")
            self.assertEqual(directed["edges"][0]["target_service"], "cartservice")


if __name__ == "__main__":
    unittest.main()
