from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.main import run_pipeline


class Phase2PipelineIntegrationTest(unittest.TestCase):
    def test_topology_backend_writes_required_audit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_path = root / "graph.json"
            graph_path.write_text(
                json.dumps(
                    {
                        "nodes": [{"id": "payment-api"}, {"id": "auth-api"}],
                        "edges": [],
                        "adjacency": {
                            "payment-api": [{"service": "auth-api", "weight": 1}],
                            "auth-api": [{"service": "payment-api", "weight": 1}],
                        },
                    }
                ),
                encoding="utf-8",
            )
            config = sample_topology_config(root, graph_path)

            records, _ = run_pipeline(config, "hybrid", output_mode="unit_topology")
            candidate_records = [record for record in records if record["is_candidate"]]
            self.assertTrue(candidate_records)
            record = next(record for record in candidate_records if record["retrieved_context_count"] > 0)
            self.assertEqual(record["retrieval_backend"], "topology_aware_fusion")
            for field in [
                "candidate_pool_size",
                "bm25_candidate_count",
                "graph_candidate_count",
                "duplicates_removed",
                "bm25_norm",
                "time_sim",
                "graph_distance",
                "graph_sim",
                "score_final",
                "context_coverage",
                "actual_api_calls",
                "cache_hits",
                "actual_api_call",
                "llm_cache_hit",
                "json_valid",
                "final_decision",
            ]:
                self.assertIn(field, record)
            self.assertTrue(record["retrieved_context_score_components"])

    def test_missing_graph_falls_back_to_empty_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = sample_topology_config(root, root / "missing_graph.json")
            records, _ = run_pipeline(config, "hybrid", output_mode="unit_missing_graph")
            self.assertTrue(records)
            self.assertTrue(any(record.get("retrieval_backend_warning") for record in records))


def sample_topology_config(root: Path, graph_path: Path) -> dict:
    return {
        "data": {
            "metric_path": "data/sample/metrics.csv",
            "log_path": "data/sample/logs.jsonl",
        },
        "preprocessing": {
            "window_size": 60,
            "stride": 30,
            "normalization": "zscore",
        },
        "detector": {
            "name": "feature_pressure",
            "threshold": 0.1,
        },
        "retrieval": {
            "backend": "topology_aware_fusion",
            "lexical_backend": "hybrid_bm25",
            "graph_path": str(graph_path),
            "top_k": 2,
            "bm25_k": 3,
            "graph_max_distance": 1,
            "graph_per_service_limit": 2,
            "time_margin_minutes": 5,
            "alpha": 0.35,
            "beta": 0.25,
            "gamma": 0.4,
        },
        "llm_gate": {
            "enabled": True,
            "low_threshold": 0.1,
            "high_threshold": 1.1,
            "high_score_action": "call_llm",
            "max_llm_calls_per_minute": 0,
            "max_total_calls": 10,
        },
        "llm": {
            "provider": "mock",
            "model": "mock-judge",
            "temperature": 0,
            "max_output_tokens": 128,
        },
        "decision": {
            "confidence_threshold": 0.8,
            "require_evidence_for_true_alert": True,
            "llm_budget_exhausted_action": "manual_review",
        },
        "evaluation": {
            "output_dir": str(root / "results"),
            "audit_dir": str(root / "audit"),
            "max_windows": 6,
            "max_llm_calls": 10,
        },
    }


if __name__ == "__main__":
    unittest.main()
