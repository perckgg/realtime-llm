from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from src.models import AlertCandidate
from src.phase2.retrieval.fusion_ranker import FusionCandidate, FusionRanker, FusionWeights
from src.phase2.retrieval.topology_candidate_expander import (
    ServiceTopology,
    TopologyCandidateExpander,
    alert_reference_time,
    graph_distance_for_service,
)
from src.retrieval.context_store import LocalContextStore, StoredContext, _bm25_score
from src.retrieval.embedder import tokenize


@dataclass
class RetrievalDebugInfo:
    window_id: str
    alert_id: str
    alert_service: str
    bm25_candidate_count: int
    graph_candidate_count: int
    duplicates_removed: int
    candidate_pool_size: int
    retrieved_context_count: int
    retrieval_latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "alert_id": self.alert_id,
            "alert_service": self.alert_service,
            "bm25_candidate_count": self.bm25_candidate_count,
            "graph_candidate_count": self.graph_candidate_count,
            "duplicates_removed": self.duplicates_removed,
            "candidate_pool_size": self.candidate_pool_size,
            "retrieved_context_count": self.retrieved_context_count,
            "retrieval_latency_ms": round(self.retrieval_latency_ms, 4),
        }


class TopologyAwareRetriever:
    def __init__(
        self,
        store: LocalContextStore,
        topology: ServiceTopology,
        top_k: int = 6,
        bm25_k: int = 60,
        graph_max_distance: int = 2,
        graph_per_service_limit: int = 20,
        time_margin_minutes: int = 5,
        tau_seconds: float = 300.0,
        weights: FusionWeights | None = None,
    ) -> None:
        self.store = store
        self.topology = topology
        self.top_k = top_k
        self.bm25_k = bm25_k
        self.expander = TopologyCandidateExpander(
            topology=topology,
            max_graph_distance=graph_max_distance,
            time_margin_minutes=time_margin_minutes,
            per_service_limit=graph_per_service_limit,
        )
        self.ranker = FusionRanker(weights=weights, tau_seconds=tau_seconds)

    def retrieve(self, alert: AlertCandidate) -> tuple[list[dict[str, Any]], RetrievalDebugInfo]:
        started = time.perf_counter()
        query = build_query(alert)
        bm25_matches = self.store.search(query, top_n=self.bm25_k) if self.bm25_k > 0 else []
        graph_matches = self.expander.expand(alert, self.store)

        candidates_by_id: dict[str, FusionCandidate] = {}
        total_input_candidates = len(bm25_matches) + len(graph_matches)

        for _, item in bm25_matches:
            candidate = candidates_by_id.get(item.event.doc_id)
            if candidate is None:
                candidate = FusionCandidate(
                    context=item,
                    bm25_raw=bm25_raw(self.store, query, item),
                    graph_distance=graph_distance_for_service(
                        self.topology, alert.service_id, item.event.service_id
                    ),
                    source_flags={"bm25"},
                )
                candidates_by_id[item.event.doc_id] = candidate
            else:
                candidate.source_flags.add("bm25")

        for graph_candidate in graph_matches:
            item = graph_candidate.context
            candidate = candidates_by_id.get(item.event.doc_id)
            if candidate is None:
                candidate = FusionCandidate(
                    context=item,
                    bm25_raw=bm25_raw(self.store, query, item),
                    graph_distance=graph_candidate.graph_distance,
                    source_flags={"graph"},
                )
                candidates_by_id[item.event.doc_id] = candidate
            else:
                candidate.source_flags.add("graph")
                candidate.graph_distance = closer_distance(
                    candidate.graph_distance, graph_candidate.graph_distance
                )

        alert_time = alert_reference_time(alert)
        pool = list(candidates_by_id.values())
        ranked = self.ranker.rank(pool, alert_time=alert_time, top_k=self.top_k)
        latency_ms = (time.perf_counter() - started) * 1000
        debug = RetrievalDebugInfo(
            window_id=alert.window_id,
            alert_id=alert.alert_id,
            alert_service=alert.service_id,
            bm25_candidate_count=len(bm25_matches),
            graph_candidate_count=len(graph_matches),
            duplicates_removed=total_input_candidates - len(pool),
            candidate_pool_size=len(pool),
            retrieved_context_count=len(ranked),
            retrieval_latency_ms=latency_ms,
        )
        return [context_payload(alert, candidate, index + 1) for index, candidate in enumerate(ranked)], debug


def build_query(alert: AlertCandidate) -> str:
    high_metrics = [
        f"{name}:{value}"
        for name, value in sorted(
            alert.metric_snapshot.items(),
            key=lambda item: abs(float(item[1])),
            reverse=True,
        )[:4]
    ]
    return " ".join(
        token
        for token in [
            alert.service_id,
            alert.node_id,
            alert.detector_label,
            alert.fault_type,
            *alert.top_features,
            *high_metrics,
        ]
        if token
    )


def bm25_raw(store: LocalContextStore, query: str, item: StoredContext) -> float:
    return _bm25_score(
        query_tokens=tokenize(query),
        item=item,
        document_frequencies=store._document_frequencies,
        document_count=len(store.items),
        average_document_length=store._average_document_length(),
    )


def closer_distance(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def context_payload(alert: AlertCandidate, candidate: FusionCandidate, rank: int) -> dict[str, Any]:
    event = candidate.context.event
    return {
        "window_id": alert.window_id,
        "alert_id": alert.alert_id,
        "doc_id": event.doc_id,
        "alert_service": alert.service_id,
        "context_id": event.doc_id,
        "context_type": "trace" if event.event_type == "trace_span" else "log",
        "context_service": event.service_id,
        "service_id": event.service_id,
        "node_id": event.node_id,
        "pod_id": event.pod_id,
        "context_timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
        "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
        "source": event.source,
        "severity": event.severity,
        "event_type": event.event_type,
        "source_flags": sorted(candidate.source_flags),
        "bm25_raw": round(candidate.bm25_raw, 6),
        "bm25_norm": round(candidate.bm25_norm, 6),
        "time_sim": round(candidate.time_sim, 6),
        "graph_distance": candidate.graph_distance,
        "graph_sim": round(candidate.graph_sim, 6),
        "score_final": round(candidate.score_final, 6),
        "score": round(candidate.score_final, 6),
        "rank": rank,
        "message": event.message,
        "content_preview": event.message[:240],
        "retrieval_backend": "topology_aware_fusion",
    }
