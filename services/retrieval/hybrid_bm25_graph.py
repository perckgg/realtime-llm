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

`k_graph` (QD-022, V16 (b) -- "C1-quota"): after ranking the whole pool by the
Fusion Score, the top-k must hold at least min(k_graph, available) events with
origin "graph" -- the best-scoring ones; the remaining slots go to the best
events of any origin; the selection keeps Fusion Score order. `k_graph = 0`
(default) is C1-paper exactly.

`engine` (QD-022, V17): "vectorized" (default) runs `bm25_pool: window` on
`window_index.WindowIndex` -- identical output, ~10x faster; "reference" is
the original pure-Python path, kept as fallback and test oracle. `global`
always uses the reference path.

`retrieve()` = `build_pool()` (independent of alpha, beta, gamma, k_graph) +
`top_events()`; `reweighted()` gives a copy with other weights so the
retrieval-only ablation (QD-025) re-ranks one pool per grid point.
"""

from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

import numpy as np

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
from services.retrieval.window_index import WindowIndex, to_us

EPSILON = 1e-9


@dataclass
class _Candidate:
    doc: EvidenceDoc
    bm25_raw: float
    graph_distance: int | None
    source_flags: set[str] = field(default_factory=set)
    bm25_norm: float = 0.0
    time_sim: float = 0.0
    graph_sim: float = 0.0
    score_final: float = 0.0


@dataclass
class CandidatePool:
    """Output of `HybridBm25GraphRetriever.build_pool` (weights not applied yet)."""

    entries: list[_Candidate]
    service: str
    start: datetime
    end: datetime
    t0: datetime
    query: str
    corpus_size: int
    n_lexical: int
    n_expanded: int
    n_reachable: int

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
        k_graph: int = 0,
        engine: Literal["vectorized", "reference"] = "vectorized",
    ) -> None:
        if min(alpha, beta, gamma) < 0 or not math.isclose(alpha + beta + gamma, 1.0, abs_tol=1e-9):
            raise ValueError("alpha, beta, gamma must be >= 0 and sum to 1")
        if tau_seconds <= 0:
            raise ValueError("tau_seconds must be positive")
        if k_graph < 0:
            raise ValueError("k_graph must be >= 0")
        if engine not in {"vectorized", "reference"}:
            raise ValueError(f"unknown engine {engine!r}")
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
        self.k_graph = k_graph
        self.engine = engine
        self._global: _Corpus | None = None
        self._indexed: dict[str, _Indexed] = {}
        self._window_index: WindowIndex | None = None

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
        pool = self.build_pool(candidate)
        events, tokens, truncated, promoted = self.top_events(pool, budget)
        latency = (time.perf_counter() - started) * 1000
        return RetrievalResult(
            strategy=self.name,
            events=events,
            latency_ms=latency,
            token_estimate=tokens,
            truncated=truncated,
            debug={
                "query": pool.query,
                "bm25_pool": self.bm25_pool,
                "engine": self.engine if self.bm25_pool == "window" else "reference",
                "pool_corpus_size": pool.corpus_size,
                "bm25_candidates": pool.n_lexical,
                "graph_candidates": pool.n_expanded,
                "candidate_pool_size": len(pool.entries),
                "duplicates_removed": pool.n_lexical + pool.n_expanded - len(pool.entries),
                "reachable_services": pool.n_reachable,
                "weights": {"alpha": self.alpha, "beta": self.beta, "gamma": self.gamma},
                "tau_seconds": self.tau_seconds,
                "k_graph": self.k_graph,
                "quota_promoted": promoted,
                "timeout_exceeded": latency > budget.timeout_ms,
            },
        )

    def build_pool(self, candidate: AlertCandidate) -> CandidatePool:
        """Candidate pool of one alert: lexical top-`bm25_k` + graph expansion, deduplicated.
        Independent of alpha, beta, gamma and k_graph (they only rank/select it)."""
        start = candidate.ts
        end = candidate.end_ts or candidate.ts + self.window
        t0 = start + (end - start) / 2
        lo, hi = start - self.time_margin, end + self.time_margin
        extra = self.extra_query_terms(candidate) if self.extra_query_terms else ()
        query = build_query(candidate, extra)
        near = self.graph.distances(candidate.service, self.graph_max_distance)
        all_distances = self.graph.distances(candidate.service)
        reachable = set(near) or {candidate.service}
        if self.bm25_pool == "window" and self.engine == "vectorized":
            lexical, expanded, corpus_size = self._gather_vectorized(query, near, reachable, lo, hi, t0)
        else:
            lexical, expanded, corpus_size = self._gather_reference(query, near, reachable, lo, hi, t0)

        pool: dict[str, _Candidate] = {}
        for doc, bm25 in lexical:
            entry = pool.get(doc.doc_id)
            if entry is None:
                pool[doc.doc_id] = _Candidate(doc, bm25, all_distances.get(doc.service), {"bm25"})
            else:
                entry.source_flags.add("bm25")
        for doc, distance, bm25 in expanded:
            entry = pool.get(doc.doc_id)
            if entry is None:
                pool[doc.doc_id] = _Candidate(doc, bm25, distance, {"graph"})
            else:
                entry.source_flags.add("graph")
                entry.graph_distance = distance if entry.graph_distance is None else min(entry.graph_distance, distance)
        return CandidatePool(
            entries=list(pool.values()),
            service=candidate.service,
            start=start,
            end=end,
            t0=t0,
            query=query,
            corpus_size=corpus_size,
            n_lexical=len(lexical),
            n_expanded=len(expanded),
            n_reachable=len(near),
        )

    def top_events(
        self, pool: CandidatePool, budget: RetrievalBudget
    ) -> tuple[list[ContextEvent], int, bool, int]:
        """Rank `pool` with this retriever's weights, apply k_graph and the token budget.
        Returns (events, tokens, truncated, quota_promoted); `pool` can be re-ranked again."""
        ranked_all = self._rank(list(pool.entries), pool.t0, budget.top_k)
        ranked, promoted = self._select(ranked_all, budget.top_k, pool.service)
        events: list[ContextEvent] = []
        tokens = 0
        truncated = False
        for rank, entry in enumerate(ranked, start=1):
            cost = estimate_tokens(entry.doc.message[:240])
            if events and tokens + cost > budget.max_tokens:
                truncated = True
                break
            tokens += cost
            events.append(_event(rank, entry, pool.start, pool.end, pool.service))
        return events, tokens, truncated, promoted

    def reweighted(self, alpha: float, beta: float, gamma: float, k_graph: int) -> HybridBm25GraphRetriever:
        """Same retriever (store, graph, caches shared) with other Fusion weights / quota --
        for the retrieval-only ablation (QD-025)."""
        if min(alpha, beta, gamma) < 0 or not math.isclose(alpha + beta + gamma, 1.0, abs_tol=1e-9):
            raise ValueError("alpha, beta, gamma must be >= 0 and sum to 1")
        if k_graph < 0:
            raise ValueError("k_graph must be >= 0")
        clone = copy.copy(self)
        clone.alpha, clone.beta, clone.gamma, clone.k_graph = alpha, beta, gamma, k_graph
        return clone

    def _gather_reference(
        self, query: str, near: dict[str, int], reachable: set[str], lo: datetime, hi: datetime, t0: datetime
    ) -> tuple[list[tuple[EvidenceDoc, float]], list[tuple[EvidenceDoc, int, float]], int]:
        """Lexical top-`bm25_k` (doc, bm25) and graph expansion (doc, d, bm25) -- pure Python."""
        corpus = self._corpus(lo, hi, reachable)
        query_tokens = tokenize(query)
        lexical = (
            [(item.doc, bm25) for _, bm25, item in corpus.search(query, top_n=self.bm25_k)] if self.bm25_k > 0 else []
        )
        expanded = [
            (item.doc, distance, corpus._bm25(query_tokens, item))
            for item, distance in self._expand(corpus, near, lo, hi, t0)
        ]
        return lexical, expanded, len(corpus.items)

    def _gather_vectorized(
        self, query: str, near: dict[str, int], reachable: set[str], lo: datetime, hi: datetime, t0: datetime
    ) -> tuple[list[tuple[EvidenceDoc, float]], list[tuple[EvidenceDoc, int, float]], int]:
        """Same output as `_gather_reference` for bm25_pool='window', on WindowIndex."""
        if self._window_index is None:
            self._window_index = WindowIndex(self.store)
        index = self._window_index
        found = index.search(lo, hi, reachable, query, self.bm25_k if self.bm25_k > 0 else 0)
        docs = found.docs
        lexical = [(docs[i], float(found.bm25[i])) for i in found.top]
        expanded: list[tuple[EvidenceDoc, int, float]] = []
        limit = self.graph_per_service_limit
        if near and limit > 0 and docs:
            # Every doc of the window corpus is in a reachable service and in [lo, hi].
            dt = np.abs(found.ts - to_us(t0))
            for service, distance in near.items():
                sid = index.services.get(service)
                if sid is None:
                    continue
                rows = np.flatnonzero(found.svc == sid)
                if len(rows) > limit:
                    kth = np.partition(dt[rows], limit - 1)[limit - 1]
                    rows = rows[dt[rows] <= kth]
                best = sorted(rows.tolist(), key=lambda i: (int(dt[i]), docs[i].doc_id))[:limit]
                expanded.extend((docs[i], distance, float(found.bm25[i])) for i in best)
            expanded.sort(key=lambda e: (e[1], abs((e[0].ts - t0).total_seconds()), e[0].doc_id))
        return lexical, expanded, len(docs)

    def _select(self, ranked: list[_Candidate], top_k: int, s0: str) -> tuple[list[_Candidate], int]:
        """Top-k with at least min(k_graph, available) origin-"graph" events (C1-quota).
        Returns the selection in Fusion Score order and how many events the quota promoted."""
        plain = ranked[: max(top_k, 0)]
        if self.k_graph <= 0 or top_k <= 0:
            return plain, 0
        graph = [c for c in ranked if c.doc.service != s0]
        reserved = graph[: min(self.k_graph, top_k)]
        taken = {id(c) for c in reserved}
        rest = [c for c in ranked if id(c) not in taken][: top_k - len(reserved)]
        taken.update(id(c) for c in rest)
        selected = [c for c in ranked if id(c) in taken]
        plain_ids = {id(c) for c in plain}
        return selected, sum(1 for c in selected if id(c) not in plain_ids)

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
        """GD1 FusionRanker.rank, returning the whole ranked pool (callers cut to top-k)."""
        if top_k <= 0 or not pool:
            return []
        low = min(c.bm25_raw for c in pool)
        high = max(c.bm25_raw for c in pool)
        for c in pool:
            c.bm25_norm = _normalize(c.bm25_raw, low, high)
            c.time_sim = _clamp01(math.exp(-abs((c.doc.ts - t0).total_seconds()) / self.tau_seconds))
            c.graph_sim = 0.0 if c.graph_distance is None else _clamp01(1.0 / (1.0 + c.graph_distance))
            c.score_final = _clamp01(self.alpha * c.bm25_norm + self.beta * c.time_sim + self.gamma * c.graph_sim)
        pool.sort(
            key=lambda c: (
                -c.score_final,
                -c.bm25_norm,
                -c.time_sim,
                c.graph_distance if c.graph_distance is not None else 10**9,
                c.doc.doc_id,
            )
        )
        return pool


def _event(rank: int, c: _Candidate, start: datetime, end: datetime, s0: str) -> ContextEvent:
    doc = c.doc
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
