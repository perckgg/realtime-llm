"""Vectorised BM25 search over a time window of the evidence store (V17, QD-022).

Same results as building `bm25_hybrid._Corpus` over `store.query(lo, hi,
services)` and calling `search()` -- same docs in the same order, the same BM25
and search scores **bit for bit**, the same ranking -- only faster:

- each Nezha per-minute file is tokenised once (LRU of `cache_files` files) into
  integer arrays: time, service, length, sum of squared counts, and a posting
  list (token id -> rows, counts);
- a query selects rows with numpy masks and re-does `NezhaEvidenceStore.query`'s
  ordering (logs before traces, then `clean()`: noise dropped, first of each
  (ts, service, message) kept, stable sort by time);
- BM25 is accumulated per query token in the query's token order, with the same
  float operations as `_Corpus._bm25`, so every per-doc sum is identical;
- cosine is accumulated in the query embedding's key order. `cosine()` iterates
  the *smaller* dict, so for docs with fewer distinct tokens than the query and
  >= 3 shared tokens the float sum order can differ; those few docs are scored
  with the original `cosine()` instead.

Stores without `files_for` (e.g. `InMemoryEvidenceStore` in tests) are served
from `store.query()` directly, without caching.

Keep `engine: reference` in `hybrid_bm25_graph` as the fallback / oracle
(tests/test_window_index.py compares the two).
"""

from __future__ import annotations

import math
from collections import Counter, OrderedDict
from collections.abc import Collection, Hashable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from numpy.typing import NDArray

from packages.schemas.evidence import NOISE_PATTERNS, EvidenceDoc
from services.retrieval.bm25_hybrid import EvidenceSource, cosine, embed, tokenize

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_US = timedelta(microseconds=1)
K1, B = 1.5, 0.75  # _Corpus._bm25 defaults


def to_us(ts: datetime) -> int:
    return (ts - EPOCH) // _US


@dataclass(frozen=True)
class _FileIndex:
    docs: list[EvidenceDoc]
    keys: list[tuple[int, str, str]]  # clean() de-duplication key
    ts: NDArray[np.int64]
    svc: NDArray[np.int64]
    is_trace: NDArray[np.bool_]
    noise: NDArray[np.bool_]
    length: NDArray[np.int64]
    sqnorm: NDArray[np.int64]  # sum of squared token counts (embedding norm^2)
    distinct: NDArray[np.int64]  # distinct tokens (embedding dict size)
    post_tid: NDArray[np.int64]  # posting list sorted by (token id, row)
    post_row: NDArray[np.int64]
    post_cnt: NDArray[np.int64]


@dataclass(frozen=True)
class WindowSearch:
    """The window corpus in `store.query` order and its search results."""

    docs: list[EvidenceDoc]
    ts: NDArray[np.int64]  # microseconds since epoch
    svc: NDArray[np.int64]  # WindowIndex.services ids
    bm25: NDArray[np.float64]  # `_Corpus._bm25` of every doc
    top: list[int]  # `_Corpus.search(query, top_n)` order, as indices into docs
    search_score: NDArray[np.float64]


class WindowIndex:
    def __init__(self, store: EvidenceSource, cache_files: int = 48) -> None:
        self.store = store
        self.cache_files = cache_files
        self.vocab: dict[str, int] = {}
        self.services: dict[str, int] = {}
        self._files: OrderedDict[Hashable, _FileIndex] = OrderedDict()

    # -- indexing ----------------------------------------------------------
    def _service_id(self, service: str) -> int:
        sid = self.services.get(service)
        if sid is None:
            sid = self.services[service] = len(self.services)
        return sid

    def _build(self, docs: Sequence[EvidenceDoc]) -> _FileIndex:
        vocab = self.vocab
        n = len(docs)
        length = np.zeros(n, dtype=np.int64)
        sqnorm = np.zeros(n, dtype=np.int64)
        distinct = np.zeros(n, dtype=np.int64)
        rows: list[int] = []
        tids: list[int] = []
        cnts: list[int] = []
        for i, doc in enumerate(docs):
            counts = Counter(tokenize(doc.text()))
            total = square = 0
            for token, count in counts.items():
                tid = vocab.get(token)
                if tid is None:
                    tid = vocab[token] = len(vocab)
                tids.append(tid)
                cnts.append(count)
                total += count
                square += count * count
            rows.extend([i] * len(counts))
            length[i], sqnorm[i], distinct[i] = total, square, len(counts)
        tid_arr = np.asarray(tids, dtype=np.int64)
        order = np.argsort(tid_arr, kind="stable")  # rows stay ascending within a token
        return _FileIndex(
            docs=list(docs),
            keys=[(to_us(d.ts), d.service, d.message) for d in docs],
            ts=np.fromiter((to_us(d.ts) for d in docs), dtype=np.int64, count=n),
            svc=np.fromiter((self._service_id(d.service) for d in docs), dtype=np.int64, count=n),
            is_trace=np.fromiter((d.event_type == "trace_span" for d in docs), dtype=np.bool_, count=n),
            noise=np.fromiter(
                (any(p.search(d.message) for p in NOISE_PATTERNS) for d in docs), dtype=np.bool_, count=n
            ),
            length=length,
            sqnorm=sqnorm,
            distinct=distinct,
            post_tid=tid_arr[order],
            post_row=np.asarray(rows, dtype=np.int64)[order],
            post_cnt=np.asarray(cnts, dtype=np.int64)[order],
        )

    def _file(self, key: Hashable, load: Any) -> _FileIndex:
        index = self._files.get(key)
        if index is not None:
            self._files.move_to_end(key)
            return index
        index = self._files[key] = self._build(load())
        while len(self._files) > self.cache_files:
            self._files.popitem(last=False)
        return index

    # -- query ---------------------------------------------------------------
    def search(
        self, lo: datetime, hi: datetime, services: Collection[str], query: str, top_n: int
    ) -> WindowSearch:
        files_for = getattr(self.store, "files_for", None)
        if files_for is not None:
            parts = [
                self._file(f.path, lambda f=f: self.store.load_file(f))  # type: ignore[attr-defined]
                for f in files_for(lo, hi)
            ]
            presorted = False
        else:
            parts = [self._build(self.store.query(lo, hi, services))]  # already clean, keep order
            presorted = True

        lo_us, hi_us = to_us(lo), to_us(hi)
        wanted = np.asarray([self.services[s] for s in services if s in self.services], dtype=np.int64)
        part_rows: list[NDArray[np.int64]] = []
        for part in parts:
            if presorted:
                part_rows.append(np.arange(len(part.docs), dtype=np.int64))
                continue
            mask = (part.ts >= lo_us) & (part.ts <= hi_us) & np.isin(part.svc, wanted) & ~part.noise
            part_rows.append(np.flatnonzero(mask))
        file_of = np.concatenate(
            [np.full(len(r), i, dtype=np.int64) for i, r in enumerate(part_rows)] or [np.empty(0, np.int64)]
        )
        row_of = np.concatenate(part_rows or [np.empty(0, np.int64)])
        n_all = len(row_of)
        ts = np.concatenate([p.ts[r] for p, r in zip(parts, part_rows, strict=True)] or [np.empty(0, np.int64)])
        svc = np.concatenate([p.svc[r] for p, r in zip(parts, part_rows, strict=True)] or [np.empty(0, np.int64)])
        if presorted:
            order = np.arange(n_all, dtype=np.int64)
        else:
            trace = np.concatenate(
                [p.is_trace[r] for p, r in zip(parts, part_rows, strict=True)] or [np.empty(0, np.bool_)]
            )
            # query(): logs before traces (stable), then clean(): first of each key, stable by time.
            order = np.lexsort((np.arange(n_all), trace, ts))
            order = order[~self._duplicates(order, ts, svc, parts, file_of, row_of)]
        n = len(order)
        docs = [parts[file_of[j]].docs[row_of[j]] for j in order]
        ts, svc = ts[order], svc[order]

        query_tokens = tokenize(query)
        query_counts = Counter(query_tokens)
        unique = list(query_counts)
        tf = np.zeros((n, len(unique)), dtype=np.int64)
        length = np.zeros(n, dtype=np.int64)
        sqnorm = np.zeros(n, dtype=np.int64)
        distinct = np.zeros(n, dtype=np.int64)
        if n:
            position = np.empty(n_all, dtype=np.int64)
            position.fill(-1)
            position[order] = np.arange(n)
            start = 0
            for part, rows in zip(parts, part_rows, strict=True):
                dest = position[start : start + len(rows)]
                start += len(rows)
                keep = dest >= 0
                rows, dest = rows[keep], dest[keep]
                length[dest] = part.length[rows]
                sqnorm[dest] = part.sqnorm[rows]
                distinct[dest] = part.distinct[rows]
                local = np.full(len(part.docs), -1, dtype=np.int64)
                local[rows] = dest
                for j, token in enumerate(unique):
                    tid = self.vocab.get(token)
                    if tid is None:
                        continue
                    a = np.searchsorted(part.post_tid, tid, side="left")
                    b = np.searchsorted(part.post_tid, tid, side="right")
                    if a == b:
                        continue
                    target = local[part.post_row[a:b]]
                    hit = target >= 0
                    tf[target[hit], j] = part.post_cnt[a:b][hit]

        bm25 = self._bm25(query_tokens, unique, tf, length)
        semantic = self._cosine(query_tokens, query_counts, unique, tf, sqnorm, distinct, docs)
        positive = bm25 > 0
        normalized = np.zeros(n, dtype=np.float64)
        normalized[positive] = bm25[positive] / (bm25[positive] + 1.0)
        score = (0.6 * normalized) + (0.4 * semantic)
        top = np.argsort(-score, kind="stable")[: max(top_n, 0)]
        return WindowSearch(docs=docs, ts=ts, svc=svc, bm25=bm25, top=[int(i) for i in top], search_score=score)

    @staticmethod
    def _duplicates(
        order: NDArray[np.int64],
        ts: NDArray[np.int64],
        svc: NDArray[np.int64],
        parts: list[_FileIndex],
        file_of: NDArray[np.int64],
        row_of: NDArray[np.int64],
    ) -> NDArray[np.bool_]:
        """Mask over `order`: later copies of a (ts, service, message) key."""
        drop = np.zeros(len(order), dtype=np.bool_)
        if len(order) < 2:
            return drop
        ts_o, svc_o = ts[order], svc[order]
        group = np.lexsort((np.arange(len(order)), svc_o, ts_o))  # by (ts, service), then position
        same = (ts_o[group][1:] == ts_o[group][:-1]) & (svc_o[group][1:] == svc_o[group][:-1])
        if not same.any():
            return drop
        seen: set[tuple[int, str, str]] = set()
        last = -2
        for k in np.flatnonzero(same):
            for pos in (int(group[k]), int(group[k + 1])):
                if pos == last:
                    continue
                last = pos
                j = order[pos]
                key = parts[file_of[j]].keys[row_of[j]]
                if key in seen:
                    drop[pos] = True
                else:
                    seen.add(key)
        return drop

    @staticmethod
    def _bm25(
        query_tokens: list[str], unique: list[str], tf: NDArray[np.int64], length: NDArray[np.int64]
    ) -> NDArray[np.float64]:
        """`_Corpus._bm25` for every doc: same per-token terms, same summation order."""
        n = len(length)
        score = np.zeros(n, dtype=np.float64)
        if not query_tokens or n <= 0:
            return score
        total = int(length.sum())
        avgdl = total / n or 1.0
        column = {token: j for j, token in enumerate(unique)}
        ratio = 1 - B + B * (length / avgdl)
        for token in query_tokens:
            frequency = tf[:, column[token]]
            hit = frequency > 0
            if not hit.any():
                continue
            df = int(hit.sum())
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            f = frequency[hit].astype(np.float64)
            score[hit] += idf * ((f * (K1 + 1)) / (f + K1 * ratio[hit]))
        return score

    @staticmethod
    def _cosine(
        query_tokens: list[str],
        query_counts: Counter[str],
        unique: list[str],
        tf: NDArray[np.int64],
        sqnorm: NDArray[np.int64],
        distinct: NDArray[np.int64],
        docs: list[EvidenceDoc],
    ) -> NDArray[np.float64]:
        """`cosine(embed(query), embed(doc))` for every doc, bit for bit."""
        n = len(docs)
        semantic = np.zeros(n, dtype=np.float64)
        if not unique or n == 0:
            return semantic
        query_embedding = embed(query_tokens)
        norm = np.sqrt(sqnorm.astype(np.float64))
        norm[norm == 0] = 1.0
        for j, token in enumerate(unique):
            hit = tf[:, j] > 0
            semantic[hit] += query_embedding[token] * (tf[hit, j] / norm[hit])
        # cosine() sums over the smaller dict: other order when the doc has fewer
        # distinct tokens; with >= 3 shared tokens the float sum may differ.
        shared = (tf > 0).sum(axis=1)
        for i in np.flatnonzero((distinct < len(unique)) & (shared >= 3)):
            semantic[i] = cosine(query_embedding, embed(tokenize(docs[i].text())))
        return semantic
