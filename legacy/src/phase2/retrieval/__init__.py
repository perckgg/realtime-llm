"""Phase 2 retrieval namespace."""

from src.phase2.retrieval.graph_builder import ServiceGraph, build_service_graph
from src.phase2.retrieval.pipeline_adapter import PipelineTopologyAwareRetriever
from src.phase2.retrieval.topology_aware_retriever import TopologyAwareRetriever
from src.phase2.retrieval.topology_candidate_expander import ServiceTopology

__all__ = [
    "PipelineTopologyAwareRetriever",
    "ServiceGraph",
    "ServiceTopology",
    "TopologyAwareRetriever",
    "build_service_graph",
]
