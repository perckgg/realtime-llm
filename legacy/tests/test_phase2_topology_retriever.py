from __future__ import annotations

import unittest

from src.models import AlertCandidate, LogEvent
from src.phase2.retrieval.fusion_ranker import FusionCandidate, FusionRanker, FusionWeights
from src.phase2.retrieval.topology_aware_retriever import TopologyAwareRetriever
from src.phase2.retrieval.topology_candidate_expander import ServiceTopology, graph_sim
from src.retrieval.context_store import LocalContextStore
from src.time_utils import parse_timestamp


class Phase2TopologyRetrieverTest(unittest.TestCase):
    def test_graph_sim_handles_unreachable_service(self) -> None:
        self.assertEqual(graph_sim(None), 0.0)
        self.assertEqual(graph_sim(0), 1.0)
        self.assertEqual(graph_sim(1), 0.5)

    def test_fusion_score_is_bounded_and_deterministic(self) -> None:
        event = LogEvent(
            doc_id="ctx-1",
            timestamp=parse_timestamp("2023-01-30T00:00:00Z"),
            node_id="svc-a-pod",
            service_id="svc-a",
            pod_id="svc-a-pod",
            severity="INFO",
            event_type="application_log",
            message="svc-a error",
        )
        store = LocalContextStore(vector_db="hybrid_bm25")
        store.add_events([event])
        candidate = FusionCandidate(
            context=store.items[0],
            bm25_raw=2.0,
            graph_distance=0,
            source_flags={"bm25", "graph"},
        )
        ranked = FusionRanker(FusionWeights(0.4, 0.3, 0.3)).rank(
            [candidate],
            alert_time=parse_timestamp("2023-01-30T00:00:00Z"),
            top_k=1,
        )
        self.assertEqual(len(ranked), 1)
        self.assertGreaterEqual(ranked[0].score_final, 0.0)
        self.assertLessEqual(ranked[0].score_final, 1.0)

    def test_retriever_unions_bm25_and_graph_candidates(self) -> None:
        store = LocalContextStore(vector_db="hybrid_bm25")
        store.add_events(
            [
                LogEvent(
                    doc_id="ctx-alert-service",
                    timestamp=parse_timestamp("2023-01-30T00:01:00Z"),
                    node_id="svc-a-pod",
                    service_id="svc-a",
                    pod_id="svc-a-pod",
                    severity="WARN",
                    event_type="application_log",
                    message="latency spike on svc-a",
                ),
                LogEvent(
                    doc_id="ctx-neighbor-service",
                    timestamp=parse_timestamp("2023-01-30T00:01:30Z"),
                    node_id="svc-b-pod",
                    service_id="svc-b",
                    pod_id="svc-b-pod",
                    severity="ERROR",
                    event_type="trace_span",
                    message="downstream payment trace latency",
                    source="nezha_trace",
                ),
            ]
        )
        topology = ServiceTopology({"svc-a": {"svc-b": 1.0}, "svc-b": {"svc-a": 1.0}})
        alert = AlertCandidate(
            alert_id="alert-1",
            window_id="window-1",
            time_window={
                "start": "2023-01-30T00:00:00Z",
                "end": "2023-01-30T00:02:00Z",
            },
            node_id="svc-a-pod",
            service_id="svc-a",
            anomaly_score=0.9,
            metric_snapshot={"latency": 3.0},
            detector_label="anomaly",
            top_features=["latency"],
            ground_truth="true_alert",
            fault_type="network_delay",
        )
        contexts, debug = TopologyAwareRetriever(
            store,
            topology,
            top_k=2,
            bm25_k=1,
            graph_max_distance=1,
            graph_per_service_limit=1,
        ).retrieve(alert)

        self.assertEqual(debug.candidate_pool_size, 2)
        self.assertEqual(debug.duplicates_removed, 1)
        self.assertEqual(len(contexts), 2)
        self.assertTrue(all(0.0 <= ctx["score_final"] <= 1.0 for ctx in contexts))
        self.assertEqual(contexts[0]["rank"], 1)


if __name__ == "__main__":
    unittest.main()
