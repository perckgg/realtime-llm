from __future__ import annotations

from typing import Any

from src.models import AlertCandidate
from src.phase2.retrieval.fusion_ranker import FusionWeights
from src.phase2.retrieval.topology_aware_retriever import RetrievalDebugInfo, TopologyAwareRetriever
from src.phase2.retrieval.topology_candidate_expander import ServiceTopology
from src.retrieval.context_store import LocalContextStore


class PipelineTopologyAwareRetriever:
    actual_backend = "topology_aware_fusion"
    backend_warning: str | None = None

    def __init__(
        self,
        store: LocalContextStore,
        topology: ServiceTopology,
        config: dict[str, Any],
    ) -> None:
        weights = FusionWeights(
            alpha=float(config.get("alpha", 0.35)),
            beta=float(config.get("beta", 0.25)),
            gamma=float(config.get("gamma", 0.4)),
        )
        self.retriever = TopologyAwareRetriever(
            store=store,
            topology=topology,
            top_k=int(config.get("top_k", 6)),
            bm25_k=int(config.get("bm25_k", config.get("search_k", 60))),
            graph_max_distance=int(config.get("graph_max_distance", 2)),
            graph_per_service_limit=int(config.get("graph_per_service_limit", 20)),
            time_margin_minutes=int(config.get("time_margin_minutes", 5)),
            tau_seconds=float(config.get("tau_seconds", 300.0)),
            weights=weights,
        )
        self.last_debug: RetrievalDebugInfo | None = None

    def retrieve(self, alert: AlertCandidate) -> tuple[list[dict[str, Any]], float]:
        contexts, debug = self.retriever.retrieve(alert)
        self.last_debug = debug
        return contexts, debug.retrieval_latency_ms
