"""V17 (QD-022): the vectorised window engine equals the reference pure-Python
path bit for bit; V16 (QD-022): C1-quota (`k_graph`)."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import networkx as nx
import pytest

from packages.graph.service_graph import ServiceGraph
from packages.schemas.evidence import EvidenceDoc, InMemoryEvidenceStore, NezhaEvidenceStore, _MinuteFile
from packages.schemas.models import AlertCandidate, RetrievalBudget
from services.retrieval.bm25_hybrid import _Corpus, _index, tokenize
from services.retrieval.hybrid_bm25_graph import HybridBm25GraphRetriever
from services.retrieval.window_index import WindowIndex

T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)
SERVICES = ["cart", "redis", "frontend", "ads", "disk", "lonely"]
WORDS = ["cart", "redis", "timeout", "error", "GetCart", "slow", "latency", "cpu", "93", "2", "memory",
         "periodic healthcheck succeeded", "anomaly", "frontend", "disk", "x"]  # fmt: skip


class FileStore:
    """NezhaEvidenceStore's query()/files_for()/load_file() over in-memory minute files."""

    files_for = NezhaEvidenceStore.files_for
    load_file = NezhaEvidenceStore.load_file
    query = NezhaEvidenceStore.query

    def __init__(self, files: dict[tuple[datetime, str], list[EvidenceDoc]]) -> None:
        self._files = [_MinuteFile(Path(f"{m:%H_%M}_{k}.csv"), "d", m, k) for m, k in sorted(files)]  # type: ignore[arg-type]
        self._minutes = [f.minute for f in self._files]
        self._data = {f.path: files[(f.minute, f.kind)] for f in self._files}
        self.loads = 0

    def _load(self, file: _MinuteFile) -> list[EvidenceDoc]:
        self.loads += 1
        return self._data[file.path]


def _random_store(seed: int, minutes: int = 30, per_file: int = 40) -> FileStore:
    rng = random.Random(seed)
    files: dict[tuple[datetime, str], list[EvidenceDoc]] = {}
    serial = 0
    for m in range(minutes):
        minute = T0 + timedelta(minutes=m)
        for kind in ("log", "trace"):
            docs = []
            for _ in range(per_file):
                serial += 1
                service = rng.choice(SERVICES)
                # coarse timestamps (+ file overlap) -> ties and (ts, service, message) duplicates
                ts = minute - timedelta(seconds=rng.choice([0, 5, 10, 30, 55, 61, 65]))
                message = " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 6)))
                trace = kind == "trace"
                docs.append(EvidenceDoc(f"{kind}-{serial}", ts, f"{service}-abc-x1", service,
                                        rng.choice(["INFO", "WARN", "ERROR"]),
                                        "trace_span" if trace else "application_log",
                                        "nezha_trace" if trace else "nezha_log", message))  # fmt: skip
            if docs and m % 3 == 0:  # exact copy of an earlier row in the same file
                docs.append(docs[0])
            files[(minute, kind)] = docs
    return FileStore(files)


def _graph() -> ServiceGraph:
    g = nx.DiGraph()
    g.add_edges_from([("frontend", "cart"), ("cart", "redis"), ("redis", "disk"), ("frontend", "ads")])
    g.add_node("lonely")
    return ServiceGraph(g)


def _candidate(service: str, minute: int, features: list[str]) -> AlertCandidate:
    ts = T0 + timedelta(minutes=minute)
    return AlertCandidate(candidate_id=f"c{minute}{service}", window_id="w", service=service,
                          pod=f"{service}-abc-x1", ts=ts, end_ts=ts + timedelta(seconds=60), anomaly_score=0.9,
                          source="metric", top_features=features,
                          metric_snapshot={"cpu_usage": 93.2, "memory": 2.5, "latency": 12.0})  # fmt: skip


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_window_index_equals_reference_corpus(seed):
    store = _random_store(seed)
    index = WindowIndex(store, cache_files=8)
    for minute in (3, 9, 15, 22):
        lo, hi = T0 + timedelta(minutes=minute - 8), T0 + timedelta(minutes=minute + 9)
        services = {"cart", "redis", "frontend", "disk"}
        query = "cart cart-abc-x1 anomaly latency cpu cpu_usage:93.2 memory:2.5 error timeout GetCart"
        reference = _Corpus([_index(d) for d in store.query(lo, hi, services)])
        found = index.search(lo, hi, services, query, top_n=25)
        assert [d.doc_id for d in found.docs] == [i.doc.doc_id for i in reference.items]
        tokens = tokenize(query)
        assert [float(x) for x in found.bm25] == [reference._bm25(tokens, i) for i in reference.items]
        expected = reference.search(query, top_n=25)
        assert [found.docs[i].doc_id for i in found.top] == [m[2].doc.doc_id for m in expected]
        assert [float(found.search_score[i]) for i in found.top] == [m[0] for m in expected]


@pytest.mark.parametrize("seed", [4, 5])
@pytest.mark.parametrize("k_graph", [0, 2])
def test_vectorized_engine_equals_reference(seed, k_graph):
    store = _random_store(seed)
    args = {"graph": _graph(), "graph_per_service_limit": 5, "bm25_k": 12, "k_graph": k_graph}
    fast = HybridBm25GraphRetriever(store, engine="vectorized", **args)
    slow = HybridBm25GraphRetriever(store, engine="reference", **args)
    for service, minute in (("cart", 10), ("redis", 20), ("frontend", 5), ("lonely", 12)):
        candidate = _candidate(service, minute, ["latency", "cpu"])
        a = fast.retrieve(candidate, RetrievalBudget(top_k=6))
        b = slow.retrieve(candidate, RetrievalBudget(top_k=6))
        assert [(e.event_id, e.score, e.origin, e.debug) for e in a.events] == [
            (e.event_id, e.score, e.origin, e.debug) for e in b.events
        ]
        assert a.debug["pool_corpus_size"] == b.debug["pool_corpus_size"]


def test_vectorized_engine_on_store_without_files():
    docs = [d for docs in _random_store(6)._data.values() for d in docs]
    store = InMemoryEvidenceStore(docs)
    fast = HybridBm25GraphRetriever(store, graph=_graph(), engine="vectorized")
    slow = HybridBm25GraphRetriever(store, graph=_graph(), engine="reference")
    candidate = _candidate("cart", 12, ["latency"])
    assert [e.event_id for e in fast.retrieve(candidate, RetrievalBudget()).events] == [
        e.event_id for e in slow.retrieve(candidate, RetrievalBudget()).events
    ]


def _quota_corpus() -> InMemoryEvidenceStore:
    def doc(i: int, service: str, message: str) -> EvidenceDoc:
        return EvidenceDoc(f"q{i:02d}", T0 + timedelta(seconds=30), f"{service}-abc-x1", service, "INFO",
                           "application_log", "nezha_log", message)  # fmt: skip

    local = [doc(i, "cart", f"cart timeout error GetCart attempt{i}") for i in range(8)]
    graph = [doc(10, "redis", "redis slow"), doc(11, "frontend", "request failed"), doc(12, "disk", "disk io")]
    return InMemoryEvidenceStore(local + graph)


def test_k_graph_zero_is_c1_paper_and_local_wins_without_quota():
    store = _quota_corpus()
    plain = HybridBm25GraphRetriever(store, graph=_graph()).retrieve(_candidate("cart", 0, []), RetrievalBudget())
    zero = HybridBm25GraphRetriever(store, graph=_graph(), k_graph=0).retrieve(
        _candidate("cart", 0, []), RetrievalBudget()
    )
    assert [e.event_id for e in plain.events] == [e.event_id for e in zero.events]
    assert all(e.origin == "local" for e in plain.events)  # Finding 4 in miniature
    assert plain.debug["quota_promoted"] == 0


def test_k_graph_reserves_best_neighbours_and_keeps_score_order():
    store = _quota_corpus()
    result = HybridBm25GraphRetriever(store, graph=_graph(), k_graph=2).retrieve(
        _candidate("cart", 0, []), RetrievalBudget()
    )
    origins = [e.origin for e in result.events]
    assert len(result.events) == 6
    assert origins.count("graph") == 2
    assert result.debug["quota_promoted"] == 2
    graph_ids = [e.event_id for e in result.events if e.origin == "graph"]
    # d = 1 neighbours (GraphSim 0.5) outrank d = 2 (0.33) at equal time
    assert set(graph_ids) <= {"q10", "q11"}
    scores = [e.score for e in result.events]
    assert scores == sorted(scores, reverse=True)
    assert [e.debug["rank"] for e in result.events] == list(range(1, 7))


def test_k_graph_larger_than_available_takes_all_neighbours():
    store = _quota_corpus()
    result = HybridBm25GraphRetriever(store, graph=_graph(), k_graph=5).retrieve(
        _candidate("cart", 0, []), RetrievalBudget()
    )
    assert [e.origin for e in result.events].count("graph") == 3
    assert len(result.events) == 6


def test_invalid_engine_and_k_graph():
    with pytest.raises(ValueError):
        HybridBm25GraphRetriever(InMemoryEvidenceStore([]), graph=_graph(), k_graph=-1)
    with pytest.raises(ValueError):
        HybridBm25GraphRetriever(InMemoryEvidenceStore([]), graph=_graph(), engine="fast")  # type: ignore[arg-type]
