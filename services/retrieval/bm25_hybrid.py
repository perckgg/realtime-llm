"""`bm25_hybrid` -- the BM25 baseline (01-architecture-design.md SS6.3).

Port of GD1's `HybridRetriever` (legacy/src/retrieval/retriever.py) over the
`local_hybrid_bm25` search of legacy/src/retrieval/context_store.py, with the
same tokenizer, BM25 (k1 1.5, b 0.75), hashing-embedding cosine and scores:

    search   = 0.6 * bm25 / (bm25 + 1) + 0.4 * cosine(query, doc)
    final    = 0.45 * search + 0.25 * time + 0.20 * metadata + 0.10 * signal

Changes from GD1 (docs/experiment-log.md QD-016):

1. The query no longer contains the window's fault type (GD1 `_build_query`
   appended `alert.fault_type`, the ground truth -- paper SS3.5). GD2's
   AlertCandidate has no label to leak. `extra_query_terms` exists only for
   the parity gates, to put GD1's `detector_label` and `fault_type` back.
2. `pool="window"` (GD2 default): the corpus is the s0 service's evidence in
   [start - margin, end + margin], read from the full, unfiltered Nezha store,
   and BM25 statistics are computed over that pool. GD1 searched its whole
   (label-filtered) corpus, kept the global top `max(search_k, 20 top_k)`
   and only then filtered by time; on the full 8.3 M-event dataset that would
   leave almost every window without evidence. `pool="global"` keeps GD1's
   behaviour exactly, for G-port / G-paper on GD1's corpus.
   Restricting to s0 also makes the baseline "local evidence only", which is
   CTAV's tier 1 (08 SS4); other services' evidence is C1's job.
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol

from packages.schemas.evidence import EvidenceDoc
from packages.schemas.models import AlertCandidate, ContextEvent, RetrievalBudget, RetrievalResult

TOKEN_RE = re.compile(r"[a-zA-Z0-9_/-]+")  # legacy/src/retrieval/embedder.py


class EvidenceSource(Protocol):
    def query(
        self, start: datetime, end: datetime, services: Collection[str] | None = None
    ) -> list[EvidenceDoc]: ...


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def embed(tokens: list[str]) -> dict[str, float]:
    """`HashingEmbedder.embed`: L2-normalised term counts."""
    counts = Counter(tokens)
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {key: value / norm for key, value in counts.items()}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def estimate_tokens(text: str) -> int:
    """legacy/src/llm/prompt_composer.py `estimate_tokens` (whitespace words)."""
    return max(1, len(text.split()))


@dataclass(frozen=True, slots=True)
class _Indexed:
    doc: EvidenceDoc
    counts: Counter[str]
    length: int
    embedding: dict[str, float]


def _index(doc: EvidenceDoc) -> _Indexed:
    tokens = tokenize(doc.text())
    counts = Counter(tokens)
    return _Indexed(doc, counts, sum(counts.values()), embed(tokens))


class _Corpus:
    """BM25 statistics over a list of docs -- `LocalContextStore` (hybrid_bm25)."""

    def __init__(self, items: list[_Indexed]) -> None:
        self.items = items
        self.df: Counter[str] = Counter()
        total = 0
        for item in items:
            self.df.update(item.counts.keys())
            total += item.length
        self.avgdl = (total / len(items) or 1.0) if items else 1.0

    def _bm25(self, query_tokens: list[str], item: _Indexed, k1: float = 1.5, b: float = 0.75) -> float:
        n = len(self.items)
        if not query_tokens or n <= 0:
            return 0.0
        score = 0.0
        for token in query_tokens:
            frequency = item.counts.get(token, 0)
            if not frequency:
                continue
            df = self.df.get(token, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * (item.length / self.avgdl))
            score += idf * ((frequency * (k1 + 1)) / denominator)
        return score

    def search(self, query: str, top_n: int) -> list[tuple[float, float, _Indexed]]:
        """(search score, raw bm25, item), best first; ties keep corpus order."""
        query_tokens = tokenize(query)
        query_embedding = embed(query_tokens)
        matches = []
        for item in self.items:
            bm25 = self._bm25(query_tokens, item)
            bm25_normalized = bm25 / (bm25 + 1.0) if bm25 > 0 else 0.0
            semantic = cosine(query_embedding, item.embedding)
            matches.append(((0.6 * bm25_normalized) + (0.4 * semantic), bm25, item))
        matches.sort(key=lambda match: match[0], reverse=True)
        return matches[:top_n]


def build_query(candidate: AlertCandidate, extra_terms: Sequence[str] = ()) -> str:
    """GD1 `_build_query` without `alert.fault_type` (QD-016).

    GD1: service, node, detector_label, fault_type, top_features, top-4
    metrics by |value| as "name:value". `detector_label` was "anomaly" for
    every metric candidate, so it is kept as a constant.
    """
    high_metrics = [
        f"{name}:{value}"
        for name, value in sorted(
            candidate.metric_snapshot.items(), key=lambda item: abs(float(item[1])), reverse=True
        )[:4]
    ]
    label = "anomaly" if candidate.source == "metric" else candidate.source
    return " ".join(
        [
            candidate.service,
            candidate.pod or candidate.service,
            *(extra_terms or [label]),
            *candidate.top_features,
            *high_metrics,
        ]
    )


def _metadata_score(candidate: AlertCandidate, doc: EvidenceDoc) -> float:
    score = 0.0
    if doc.service == candidate.service:
        score += 0.65
    if doc.pod == (candidate.pod or candidate.service):
        score += 0.35
    if candidate.service and candidate.service in doc.message:
        score += 0.15
    return min(score, 1.0)


def _time_score(ts: datetime, start: datetime, end: datetime, margin: timedelta) -> float:
    if start <= ts <= end:
        return 1.0
    distance = min(abs((ts - start).total_seconds()), abs((ts - end).total_seconds()))
    margin_seconds = margin.total_seconds() or 1.0
    return max(0.0, 1.0 - distance / margin_seconds)


def _duration_ms(message: str) -> float:
    marker = "duration_ms="
    if marker not in message:
        return 0.0
    tail = message.split(marker, 1)[1].split()[0]
    try:
        value = float(tail)
    except ValueError:
        return 0.0
    return value if math.isfinite(value) else 0.0


def _trace_score(candidate: AlertCandidate, doc: EvidenceDoc) -> float:
    if doc.event_type != "trace_span" and doc.source != "nezha_trace":
        return 0.0
    score = 0.5
    if any(feature in {"latency", "network", "workload"} for feature in candidate.top_features):
        score += 0.25
    duration = _duration_ms(doc.message)
    if duration >= 1000:
        score += 0.25
    elif duration >= 500:
        score += 0.1
    return min(score, 1.0)


_SEVERITY_SCORE = {"CRITICAL": 1.0, "ERROR": 0.9, "WARN": 0.65, "INFO": 0.25}


class Bm25HybridRetriever:
    """RetrievalStrategy `bm25_hybrid`. Parameters as GD1's paper_500 config
    (legacy/nezha_setup/config/experiment_phase2_topology_fusion_500w.yaml)."""

    name = "bm25_hybrid"

    def __init__(
        self,
        store: EvidenceSource,
        time_margin_minutes: float = 8,
        search_k: int = 60,
        semantic_weight: float = 0.45,
        time_weight: float = 0.25,
        metadata_weight: float = 0.2,
        signal_weight: float = 0.1,
        window_seconds: int = 60,
        pool: Literal["window", "global"] = "window",
        extra_query_terms: Callable[[AlertCandidate], Sequence[str]] | None = None,
    ) -> None:
        self.store = store
        self.time_margin = timedelta(minutes=time_margin_minutes)
        self.search_k = search_k
        self.semantic_weight = semantic_weight
        self.time_weight = time_weight
        self.metadata_weight = metadata_weight
        self.signal_weight = signal_weight
        self.window = timedelta(seconds=window_seconds)
        self.pool = pool
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

    def _corpus(self, candidate: AlertCandidate, start: datetime, end: datetime) -> _Corpus:
        if self.pool == "global":
            if self._global is None:
                docs = getattr(self.store, "docs", None)
                if docs is None:
                    raise ValueError("pool='global' needs a fixed corpus (InMemoryEvidenceStore)")
                self._global = _Corpus([_index(doc) for doc in docs])
            return self._global
        docs = self.store.query(start - self.time_margin, end + self.time_margin, {candidate.service})
        return _Corpus([self._item(doc) for doc in docs])

    def retrieve(self, candidate: AlertCandidate, budget: RetrievalBudget) -> RetrievalResult:
        started = time.perf_counter()
        start = candidate.ts
        end = candidate.end_ts or candidate.ts + self.window
        extra = self.extra_query_terms(candidate) if self.extra_query_terms else ()
        query = build_query(candidate, extra)
        corpus = self._corpus(candidate, start, end)
        top_k = budget.top_k
        matches = corpus.search(query, top_n=max(self.search_k, top_k * 20))

        strict: list[tuple[float, dict[str, float], EvidenceDoc]] = []
        relaxed: list[tuple[float, dict[str, float], EvidenceDoc]] = []
        lo, hi = start - self.time_margin, end + self.time_margin
        for search_score, bm25, item in matches:
            doc = item.doc
            if not (lo <= doc.ts <= hi):
                continue
            trace = _trace_score(candidate, doc)
            components = {
                "semantic_score": max(0.0, min(1.0, search_score)),
                "bm25_raw": bm25,
                "time_score": _time_score(doc.ts, start, end, self.time_margin),
                "metadata_score": _metadata_score(candidate, doc),
                "severity_score": _SEVERITY_SCORE.get(doc.severity.upper(), 0.2),
                "trace_score": trace,
            }
            components["signal_score"] = max(components["severity_score"], trace)
            score = (
                components["semantic_score"] * self.semantic_weight
                + components["time_score"] * self.time_weight
                + components["metadata_score"] * self.metadata_weight
                + components["signal_score"] * self.signal_weight
            )
            (strict if components["metadata_score"] > 0.0 else relaxed).append((score, components, doc))

        ranked = sorted(strict, key=lambda entry: entry[0], reverse=True)
        if len(ranked) < top_k:
            ranked.extend(sorted(relaxed, key=lambda entry: entry[0], reverse=True))

        events: list[ContextEvent] = []
        tokens = 0
        truncated = False
        for rank, (score, components, doc) in enumerate(ranked[:top_k], start=1):
            cost = estimate_tokens(doc.message[:240])
            if events and tokens + cost > budget.max_tokens:
                truncated = True
                break
            tokens += cost
            events.append(_event(rank, score, components, doc, start, end, candidate))
        latency = (time.perf_counter() - started) * 1000
        debug: dict[str, Any] = {
            "query": query,
            "pool": self.pool,
            "pool_size": len(corpus.items),
            "search_top_n": max(self.search_k, top_k * 20),
            "time_margin_sec": self.time_margin.total_seconds(),
            "in_window_strict": len(strict),
            "in_window_relaxed": len(relaxed),
            "timeout_exceeded": latency > budget.timeout_ms,
        }
        return RetrievalResult(
            strategy=self.name,
            events=events,
            latency_ms=latency,
            token_estimate=tokens,
            truncated=truncated,
            debug=debug,
        )


def _event(
    rank: int,
    score: float,
    components: dict[str, float],
    doc: EvidenceDoc,
    start: datetime,
    end: datetime,
    candidate: AlertCandidate,
) -> ContextEvent:
    if start <= doc.ts <= end:
        time_distance = 0.0
    else:
        time_distance = min(abs((doc.ts - start).total_seconds()), abs((doc.ts - end).total_seconds()))
    return ContextEvent(
        event_id=doc.doc_id,
        modality=doc.modality,
        ts=doc.ts,
        service=doc.service,
        content=doc.message,
        score=score,
        origin="local",
        graph_distance=0 if doc.service == candidate.service else None,
        debug={
            "rank": rank,
            "bm25_score": components["semantic_score"],  # GD1 "semantic_score": 0.6 bm25_norm + 0.4 cosine
            "bm25_raw": components["bm25_raw"],
            "time_distance_sec": time_distance,
            "time_score": components["time_score"],
            "metadata_score": components["metadata_score"],
            "severity_score": components["severity_score"],
            "trace_score": components["trace_score"],
            "pod": doc.pod,
            "severity": doc.severity,
            "event_type": doc.event_type,
            "source": doc.source,
            "trace_id": doc.trace_id,
            "span_id": doc.span_id,
            "parent_span_id": doc.parent_span_id,
            "duration_ms": doc.duration_ms,
        },
    )
