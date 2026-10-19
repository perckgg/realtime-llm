"""`hybrid_bm25_graph` -- C1, the paper's topology-aware Fusion Score (08 SS4).

Port of GD1's TopologyAwareRetriever (legacy/src/phase2/retrieval/
topology_aware_retriever.py, fusion_ranker.py, topology_candidate_expander.py):

    pool  = top-`bm25_k` lexical matches (bm25_hybrid's search score)
          + graph expansion: services within `graph_max_distance` hops of s0
            (undirected, s0 itself at distance 0), each service's
            `graph_per_service_limit` events closest in time to the window's
            midpoint, within [start - margin, end + margin]
    score = alpha * BM25_norm + beta * exp(-|t - t0| / tau) + gamma * 1 / (1 + d_G)
            (BM25_norm = min-max of raw BM25 over the pool; t0 = window midpoint;
            unreachable service -> GraphSim 0); ties: BM25_norm, TimeSim,
            distance, doc id -- all as GD1.

`bm25_pool` (QD-021, V13):

- "global" -- the paper exactly: lexical matches come from the whole corpus with
  **no time limit** (QD-020: 80% of the paper's topology contexts are outside
  +-8 min). Only meaningful on a fixed corpus; with `extra_query_terms` it is
  the parity mode for G-paper.
- "window" -- GD2: the corpus is the evidence of every service within
  `graph_max_distance` hops of s0 inside [start - margin, end + margin] (full
  Nezha store); BM25 statistics and lexical matches come from that pool.
  Lexical matches from services outside the hop limit (allowed by the paper)
  are not reachable; the full +-8 min corpus of all services is ~800k events
  per query, too slow for BM25 in Python, and such events get GraphSim 0.

`origin` (QD-021, V14): "local" when the event is at s0 (d_G = 0), otherwise
"graph"; which channel found it (bm25 / graph) is in `debug["source_flags"]`.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

from packages.graph.service_graph import ServiceGraph, load_graph
from packages.schemas.evidence import EvidenceDoc
from packages.schemas.models import AlertCandidate, ContextEvent, RetrievalBudget, RetrievalResult
from services.retrieval.bm25_hybrid import (
    EvidenceSource,
    _Corpus,
    _index,
    _Indexed,
    build_query,
    estimate_tokens,
    tokenize,
)

EPSILON = 1e-9


@dataclass
class _Candidate:
    item: _Indexed
    bm25_raw: float
    graph_distance: int | None
    source_flags: set[str] = field(default_factory=set)
    bm25_norm: float = 0.0
    time_sim: float = 0.0
    graph_sim: float = 0.0
    score_final: float = 0.0


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 1.0 if value > 0.0 else 0.0
    return _clamp01((value - low) / (high - low + EPSILON))


class HybridBm25GraphRetriever:
    """RetrievalStrategy `hybrid_bm25_graph`; defaults = paper configuration A4."""

    name = "hybrid_bm25_graph"

    def __init__(
        self,
        store: EvidenceSource,
        graph: ServiceGraph | None = None,
        alpha: float = 0.35,
        beta: float = 0.25,
        gamma: float = 0.40,
        tau_seconds: float = 300.0,
        bm25_k: int = 60,
        graph_max_distance: int = 2,
        graph_per_service_limit: int = 20,
        time_margin_minutes: float = 8,
        window_seconds: int = 60,
        bm25_pool: Literal["window", "global"] = "window",
        extra_query_terms: Callable[[AlertCandidate], Sequence[str]] | None = None,
    ) -> None:
        if min(alpha, beta, gamma) < 0 or not math.isclose(alpha + beta + gamma, 1.0, abs_tol=1e-9):
            raise ValueError("alpha, beta, gamma must be >= 0 and sum to 1")
        if tau_seconds <= 0:
            raise ValueError("tau_seconds must be positive")
        self.store = store
        self.graph = graph or load_graph()
        self.alpha, self.beta, self.gamma = alpha, beta, gamma
        self.tau_seconds = tau_seconds
        self.bm25_k = bm25_k
        self.graph_max_distance = graph_max_distance
        self.graph_per_service_limit = graph_per_service_limit
        self.time_margin = timedelta(minutes=time_margin_minutes)
        self.window = timedelta(seconds=window_seconds)
        self.bm25_pool = bm25_pool
        self.extra_query_terms = extra_query_terms
        self._global: _Corpus | None = None
        self._indexed: dict[str, _Indexed] = {}

    def _item(self, doc: EvidenceDoc) -> _Indexed:
        item = self._indexed.get(doc.doc_id)
        if item is None or item.doc is not doc:
            if len(self._indexed) > 500_000:
                self._indexed.clear()
            item = self._indexed[doc.doc_id] = _index(doc)
        return item

    def _corpus(self, lo: datetime, hi: datetime, reachable: set[str]) -> _Corpus:
        if self.bm25_pool == "global":
            if self._global is None:
                docs = getattr(self.store, "docs", None)
                if docs is None:
                    raise ValueError("bm25_pool='global' needs a fixed corpus (InMemoryEvidenceStore)")
                self._global = _Corpus([_index(doc) for doc in docs])
            return self._global
        return _Corpus([self._item(doc) for doc in self.store.query(lo, hi, reachable)])

    def retrieve(self, candidate: AlertCandidate, budget: RetrievalBudget) -> RetrievalResult:
        started = time.perf_counter()
        start = candidate.ts
        end = candidate.end_ts or candidate.ts + self.window
        t0 = start + (end - start) / 2
        lo, hi = start - self.time_margin, end + self.time_margin
        extra = self.extra_query_terms(candidate) if self.extra_query_terms else ()
        query = build_query(candidate, extra)
        near = self.graph.distances(candidate.service, self.graph_max_distance)
        all_distances = self.graph.distances(candidate.service)
        corpus = self._corpus(lo, hi, set(near) or {candidate.service})
        query_tokens = tokenize(query)

        pool: dict[str, _Candidate] = {}
        lexical = corpus.search(query, top_n=self.bm25_k) if self.bm25_k > 0 else []
        for _, bm25, item in lexical:
            entry = pool.get(item.doc.doc_id)
            if entry is None:
                pool[item.doc.doc_id] = _Candidate(item, bm25, all_distances.get(item.doc.service), {"bm25"})
            else:
                entry.source_flags.add("bm25")
        expanded = self._expand(corpus, near, lo, hi, t0)
        for item, distance in expanded:
            entry = pool.get(item.doc.doc_id)
            if entry is None:
                pool[item.doc.doc_id] = _Candidate(item, corpus._bm25(query_tokens, item), distance, {"graph"})
            else:
                entry.source_flags.add("graph")
                entry.graph_distance = distance if entry.graph_distance is None else min(entry.graph_distance, distance)

        ranked = self._rank(list(pool.values()), t0, budget.top_k)
        events: list[ContextEvent] = []
        tokens = 0
        truncated = False
        for rank, entry in enumerate(ranked, start=1):
            cost = estimate_tokens(entry.item.doc.message[:240])
            if events and tokens + cost > budget.max_tokens:
                truncated = True
                break
            tokens += cost
            events.append(_event(rank, entry, start, end, candidate.service))
        latency = (time.perf_counter() - started) * 1000
        return RetrievalResult(
            strategy=self.name,
            events=events,
            latency_ms=latency,
            token_estimate=tokens,
            truncated=truncated,
            debug={
                "query": query,
                "bm25_pool": self.bm25_pool,
                "pool_corpus_size": len(corpus.items),
                "bm25_candidates": len(lexical),
                "graph_candidates": len(expanded),
                "candidate_pool_size": len(pool),
                "duplicates_removed": len(lexical) + len(expanded) - len(pool),
                "reachable_services": len(near),
                "weights": {"alpha": self.alpha, "beta": self.beta, "gamma": self.gamma},
                "tau_seconds": self.tau_seconds,
                "timeout_exceeded": latency > budget.timeout_ms,
            },
        )

    def _expand(
        self, corpus: _Corpus, near: dict[str, int], lo: datetime, hi: datetime, t0: datetime
    ) -> list[tuple[_Indexed, int]]:
        """GD1 TopologyCandidateExpander.expand over the corpus' items."""
        if not near:
            return []
        by_service: dict[str, list[_Indexed]] = {service: [] for service in near}
        for item in corpus.items:
            doc = item.doc
            if doc.service in near and lo <= doc.ts <= hi:
                by_service[doc.service].append(item)
        chosen: list[tuple[_Indexed, int]] = []
        for service, items in by_service.items():
            items.sort(key=lambda it: (abs((it.doc.ts - t0).total_seconds()), it.doc.doc_id))
            chosen.extend((item, near[service]) for item in items[: self.graph_per_service_limit])
        chosen.sort(key=lambda pair: (pair[1], abs((pair[0].doc.ts - t0).total_seconds()), pair[0].doc.doc_id))
        return chosen

    def _rank(self, pool: list[_Candidate], t0: datetime, top_k: int) -> list[_Candidate]:
        """GD1 FusionRanker.rank."""
        if top_k <= 0 or not pool:
            return []
        low = min(c.bm25_raw for c in pool)
        high = max(c.bm25_raw for c in pool)
        for c in pool:
            c.bm25_norm = _normalize(c.bm25_raw, low, high)
            c.time_sim = _clamp01(math.exp(-abs((c.item.doc.ts - t0).total_seconds()) / self.tau_seconds))
            c.graph_sim = 0.0 if c.graph_distance is None else _clamp01(1.0 / (1.0 + c.graph_distance))
            c.score_final = _clamp01(self.alpha * c.bm25_norm + self.beta * c.time_sim + self.gamma * c.graph_sim)
        pool.sort(
            key=lambda c: (
                -c.score_final,
                -c.bm25_norm,
                -c.time_sim,
                c.graph_distance if c.graph_distance is not None else 10**9,
                c.item.doc.doc_id,
            )
        )
        return pool[:top_k]


def _event(rank: int, c: _Candidate, start: datetime, end: datetime, s0: str) -> ContextEvent:
    doc = c.item.doc
    if start <= doc.ts <= end:
        time_distance = 0.0
    else:
        time_distance = min(abs((doc.ts - start).total_seconds()), abs((doc.ts - end).total_seconds()))
    debug: dict[str, Any] = {
        "rank": rank,
        "source_flags": sorted(c.source_flags),
        "bm25_raw": c.bm25_raw,
        "bm25_norm": c.bm25_norm,
        "time_sim": c.time_sim,
        "graph_sim": c.graph_sim,
        "score_final": c.score_final,
        "graph_distance": c.graph_distance,
        "time_distance_sec": time_distance,
        "prompt_score": round(c.score_final, 6),  # GD1 topology payload: 6 decimals (BM25: 4)
        "pod": doc.pod,
        "severity": doc.severity,
        "event_type": doc.event_type,
        "source": doc.source,
        "trace_id": doc.trace_id,
        "span_id": doc.span_id,
        "parent_span_id": doc.parent_span_id,
        "duration_ms": doc.duration_ms,
    }
    return ContextEvent(
        event_id=doc.doc_id,
        modality=doc.modality,
        ts=doc.ts,
        service=doc.service,
        content=doc.message,
        score=c.score_final,
        origin="local" if doc.service == s0 else "graph",
        graph_distance=c.graph_distance,
        debug=debug,
    )
