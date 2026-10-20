"""`none` -- the LLM-without-RAG baseline of H0 (04 M4, QD-026).

Not a retrieval method: it returns no evidence, so the judge sees only the
alert (metric snapshot, top features). The prompt then equals the one BM25 or
C1 build for a candidate whose retrieval is empty, and the LLM cache shares
those answers across runs.
"""

from __future__ import annotations

from typing import Any

from packages.schemas.models import AlertCandidate, RetrievalBudget, RetrievalResult


class NoRetrieval:
    name = "none"

    def __init__(self, store: Any = None) -> None:
        """`store` is accepted (and ignored) so the registry can build it like the others."""

    def retrieve(self, candidate: AlertCandidate, budget: RetrievalBudget) -> RetrievalResult:
        return RetrievalResult(
            strategy=self.name,
            events=[],
            latency_ms=0.0,
            token_estimate=0,
            truncated=False,
            debug={"baseline": "llm_without_rag"},
        )
