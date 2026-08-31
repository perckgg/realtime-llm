from __future__ import annotations

import unittest

from scripts.phase2.run_retrieval_only_eval import METHODS
from src.phase2.evaluation.retrieval_metrics import summarize_retrieval


class Phase2RetrievalEvalTest(unittest.TestCase):
    def test_methods_match_level_a_plan(self) -> None:
        methods = {method.method: method for method in METHODS}
        self.assertEqual(set(methods), {"M0_bm25_only", "M1_bm25_time", "M2_bm25_graph", "M3_full_fusion"})
        self.assertEqual(methods["M0_bm25_only"].weights.alpha, 1.0)
        self.assertEqual(methods["M0_bm25_only"].graph_per_service_limit, 0)
        self.assertEqual(methods["M1_bm25_time"].weights.gamma, 0.0)
        self.assertGreater(methods["M2_bm25_graph"].graph_per_service_limit, 0)
        self.assertGreater(methods["M3_full_fusion"].graph_per_service_limit, 0)

    def test_summarize_retrieval_computes_coverage_and_ratios(self) -> None:
        records = [
            {
                "service_id": "svc-a",
                "ground_truth": "true_alert",
                "fault_type": "network_delay",
                "retrieval_latency_ms": 10,
                "graph_candidate_count": 20,
                "candidate_pool_size": 80,
                "duplicates_removed": 1,
                "contexts": [
                    {
                        "context_service": "svc-a",
                        "content_preview": "latency spike",
                        "graph_distance": 0,
                        "source_flags": ["graph"],
                    },
                    {
                        "context_service": "svc-b",
                        "content_preview": "downstream trace",
                        "graph_distance": 1,
                        "source_flags": ["bm25", "graph"],
                    },
                ],
            },
            {
                "service_id": "svc-c",
                "ground_truth": "normal",
                "fault_type": "none",
                "retrieval_latency_ms": 20,
                "graph_candidate_count": 0,
                "candidate_pool_size": 60,
                "duplicates_removed": 0,
                "contexts": [],
            },
        ]

        summary = summarize_retrieval(records)
        self.assertEqual(summary["windows"], 2)
        self.assertEqual(summary["context_coverage"], 0.5)
        self.assertEqual(summary["positive_context_coverage"], 1.0)
        self.assertEqual(summary["service_context_coverage"], 0.5)
        self.assertEqual(summary["network_delay_service_context_coverage"], 1.0)
        self.assertEqual(summary["topology_expanded_context_ratio"], 1.0)
        self.assertEqual(summary["topology_only_context_ratio"], 0.5)
        self.assertEqual(summary["avg_retrieval_latency_ms"], 15.0)


if __name__ == "__main__":
    unittest.main()
