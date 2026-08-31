from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.models import LogEvent
from src.retrieval.embedder import HashingEmbedder, cosine, tokenize


@dataclass
class StoredContext:
    event: LogEvent
    embedding: dict[str, float]
    text: str
    token_counts: Counter[str]
    length: int


class LocalContextStore:
    def __init__(
        self,
        embedder: HashingEmbedder | None = None,
        vector_db: str = "local",
        embedding_dimensions: int = 512,
    ) -> None:
        self.embedder = embedder or HashingEmbedder()
        self.items: list[StoredContext] = []
        self.requested_backend = vector_db
        self.actual_backend = "local_hashing"
        self.backend_warning: str | None = None
        self.embedding_dimensions = embedding_dimensions
        self._faiss_index: Any | None = None
        self._document_frequencies: Counter[str] = Counter()
        self._total_document_length = 0
        self.backend_info = _resolve_backend(vector_db)
        if self.backend_info["actual_backend"] != "local_hashing":
            self.actual_backend = self.backend_info["actual_backend"]
            if self.actual_backend == "faiss_flat":
                faiss = __import__("faiss")
                self._faiss_index = faiss.IndexFlatIP(self.embedding_dimensions)
        self.backend_warning = self.backend_info.get("warning")

    def add_events(self, events: list[LogEvent]) -> None:
        for event in events:
            text = _event_text(event)
            token_counts = Counter(tokenize(text))
            length = sum(token_counts.values())
            self.items.append(
                StoredContext(
                    event=event,
                    embedding=self.embedder.embed(text),
                    text=text,
                    token_counts=token_counts,
                    length=length,
                )
            )
            self._document_frequencies.update(token_counts.keys())
            self._total_document_length += length
            if self._faiss_index is not None:
                import numpy as np

                dense = self.embedder.embed_dense(text, self.embedding_dimensions)
                self._faiss_index.add(np.array([dense], dtype="float32"))

    def search(self, query: str, top_n: int | None = None) -> list[tuple[float, StoredContext]]:
        if not self.items:
            return []
        if self._faiss_index is not None and self._faiss_index.ntotal:
            import numpy as np

            limit = min(top_n or len(self.items), len(self.items))
            query_vector = self.embedder.embed_dense(query, self.embedding_dimensions)
            distances, indexes = self._faiss_index.search(np.array([query_vector], dtype="float32"), limit)
            matches: list[tuple[float, StoredContext]] = []
            for score, index in zip(distances[0], indexes[0]):
                if index < 0:
                    continue
                matches.append((float(score), self.items[int(index)]))
            return matches
        if self.actual_backend == "local_hybrid_bm25":
            return self._search_hybrid_bm25(query, top_n)
        query_embedding = self.embedder.embed(query)
        matches = [(cosine(query_embedding, item.embedding), item) for item in self.items]
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[:top_n] if top_n else matches

    def _search_hybrid_bm25(self, query: str, top_n: int | None = None) -> list[tuple[float, StoredContext]]:
        query_tokens = tokenize(query)
        query_embedding = self.embedder.embed(query)
        matches = []
        for item in self.items:
            bm25 = _bm25_score(
                query_tokens=query_tokens,
                item=item,
                document_frequencies=self._document_frequencies,
                document_count=len(self.items),
                average_document_length=self._average_document_length(),
            )
            bm25_normalized = bm25 / (bm25 + 1.0) if bm25 > 0 else 0.0
            semantic = cosine(query_embedding, item.embedding)
            score = (0.6 * bm25_normalized) + (0.4 * semantic)
            matches.append((score, item))
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[:top_n] if top_n else matches

    def _average_document_length(self) -> float:
        if not self.items:
            return 1.0
        return self._total_document_length / len(self.items) or 1.0


def _resolve_backend(vector_db: str) -> dict[str, Any]:
    requested = (vector_db or "local").lower()
    if requested in {"local", "hashing", "in_memory"}:
        return {"requested_backend": requested, "actual_backend": "local_hashing", "warning": None}
    if requested in {"bm25", "hybrid_bm25", "local_hybrid", "sparse"}:
        return {"requested_backend": requested, "actual_backend": "local_hybrid_bm25", "warning": None}
    if requested == "faiss":
        try:
            __import__("faiss")
            __import__("numpy")
        except ImportError as exc:
            return {
                "requested_backend": requested,
                "actual_backend": "local_hashing",
                "warning": f"faiss backend unavailable, using local hashing fallback: {exc}",
            }
        return {"requested_backend": requested, "actual_backend": "faiss_flat", "warning": None}
    if requested == "chroma":
        try:
            __import__("chromadb")
        except ImportError as exc:
            return {
                "requested_backend": requested,
                "actual_backend": "local_hashing",
                "warning": f"chroma backend unavailable, using local hashing fallback: {exc}",
            }
        return {
            "requested_backend": requested,
            "actual_backend": "local_hashing",
            "warning": "chroma is installed but this experiment uses the FAISS/local search path; using local hashing fallback",
        }
    return {
        "requested_backend": requested,
        "actual_backend": "local_hashing",
        "warning": f"unknown vector backend '{vector_db}', using local hashing fallback",
    }


def _event_text(event: LogEvent) -> str:
    return " ".join(
        [
            event.service_id,
            event.node_id,
            event.severity,
            event.event_type,
            event.source,
            event.message,
        ]
    )


def _bm25_score(
    query_tokens: list[str],
    item: StoredContext,
    document_frequencies: Counter[str],
    document_count: int,
    average_document_length: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    if not query_tokens or document_count <= 0:
        return 0.0
    score = 0.0
    for token in query_tokens:
        frequency = item.token_counts.get(token, 0)
        if not frequency:
            continue
        df = document_frequencies.get(token, 0)
        idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
        denominator = frequency + k1 * (1 - b + b * (item.length / average_document_length))
        score += idf * ((frequency * (k1 + 1)) / denominator)
    return score
