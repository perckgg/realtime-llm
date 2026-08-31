from __future__ import annotations

import unittest

from src.decision.policy import build_alert_candidate
from src.detectors.feature_pressure_detector import FeaturePressureDetector
from src.ingestion.log_loader import load_logs
from src.models import MetricWindow
from src.preprocessing.log_preprocessing import preprocess_logs
from src.retrieval.context_store import LocalContextStore
from src.retrieval.retriever import HybridRetriever
from src.time_utils import parse_timestamp


class RetrieverTests(unittest.TestCase):
    def test_retriever_filters_metadata_and_top_k(self) -> None:
        store = LocalContextStore()
        store.add_events(preprocess_logs(load_logs("data/sample/logs.jsonl")))
        window = MetricWindow(
            window_id="w1",
            start_time=parse_timestamp("2026-05-14T00:02:00Z"),
            end_time=parse_timestamp("2026-05-14T00:03:00Z"),
            node_id="node-a",
            service_id="payment-api",
            features=[[0.0], [3.0]],
            feature_names=["latency"],
        )
        alert = build_alert_candidate(window, FeaturePressureDetector().score(window))
        contexts, _ = HybridRetriever(store, top_k=2, time_margin_minutes=2).retrieve(alert)
        self.assertLessEqual(len(contexts), 2)
        self.assertTrue(all(ctx["service_id"] == "payment-api" for ctx in contexts))

    def test_hybrid_bm25_backend_prioritizes_lexical_matches(self) -> None:
        store = LocalContextStore(vector_db="hybrid_bm25")
        store.add_events(preprocess_logs(load_logs("data/sample/logs.jsonl")))
        matches = store.search("payment database connection pool exhausted", top_n=1)
        self.assertEqual(store.actual_backend, "local_hybrid_bm25")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][1].event.service_id, "payment-api")
        self.assertIn("Database connection pool exhausted", matches[0][1].event.message)


if __name__ == "__main__":
    unittest.main()
