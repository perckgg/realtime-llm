"""Retrieval strategy name -> constructor (01-architecture-design.md SS6.3).

A run config's `retrieval:` block (eval/configs/*.yaml) picks the strategy:

    retrieval:
      type: bm25_hybrid
      top_k: 6            # -> RetrievalBudget
      max_tokens: 4000
      timeout_ms: 500
      params: {}          # -> the strategy's constructor

Adding a strategy = one entry here + 01 SS6.3 + the `debug` table in 03 SS1.3
(rule R-F1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from packages.schemas.models import RetrievalBudget
from packages.schemas.protocols import RetrievalStrategy
from services.retrieval.bm25_hybrid import Bm25HybridRetriever, EvidenceSource
from services.retrieval.hybrid_bm25_graph import HybridBm25GraphRetriever
from services.retrieval.no_retrieval import NoRetrieval

StrategyFactory = Callable[..., RetrievalStrategy]

STRATEGIES: dict[str, StrategyFactory] = {
    "bm25_hybrid": Bm25HybridRetriever,
    "hybrid_bm25_graph": HybridBm25GraphRetriever,  # C1 (M3)
    "none": NoRetrieval,  # LLM-without-RAG baseline of H0 (M4, QD-026), not a retrieval method
}


def build_strategy(config: Mapping[str, Any], store: EvidenceSource) -> RetrievalStrategy:
    name = str(config["type"])
    if name not in STRATEGIES:
        raise ValueError(f"unknown retrieval strategy {name!r}; known: {sorted(STRATEGIES)}")
    return STRATEGIES[name](store, **dict(config.get("params") or {}))


def build_budget(config: Mapping[str, Any]) -> RetrievalBudget:
    fields = RetrievalBudget.model_fields
    return RetrievalBudget(**{key: config[key] for key in fields if key in config})
