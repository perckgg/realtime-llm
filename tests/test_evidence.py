"""packages.schemas.evidence: GD1 document format, cleaning, time filtering."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.schemas.evidence import (
    EvidenceDoc,
    InMemoryEvidenceStore,
    NezhaEvidenceStore,
    clean,
    load_gd1_corpus,
    log_doc,
    trace_doc,
)
from tests.gd1 import LEGACY

POD = "cartservice-579f59597d-wc2lz"
KNOWN = {"cartservice": "online_boutique", "frontend": "online_boutique"}


def _log_row(ts: str, nanos: str, message: str, severity: str = "info") -> dict[str, str]:
    inner = json.dumps({"message": message, "severity": severity, "timestamp": ts})
    return {
        "Timestamp": ts,
        "TimeUnixNano": nanos,
        "Node": "33.33.33.115",
        "PodName": POD,
        "Container": "server",
        "TraceID": "0163a3c609fab47d57e071bc12344f25",
        "SpanID": "0f6a63f0464e170f",
        "Log": json.dumps({"log": inner + "\n", "stream": "stdout", "time": ts}),
    }


def _trace_row(span: str, start_ns: int, duration_ns: int, parent: str = "root") -> dict[str, str]:
    return {
        "TraceID": "092506f023c94e1f581f5eca21b19162",
        "SpanID": span,
        "ParentID": parent,
        "PodName": POD,
        "OperationName": "hipstershop.CartService/GetCart",
        "StartTimeUnixNano": str(start_ns),
        "EndTimeUnixNano": str(start_ns + duration_ns),
        "Duration": str(duration_ns // 1000),
    }


@pytest.fixture(scope="module")
def gd1_prepare():
    sys.path.insert(0, str(LEGACY))
    try:
        spec = importlib.util.spec_from_file_location("gd1_prepare", LEGACY / "nezha_setup" / "prepare_nezha_data.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(LEGACY))


def _gd1_fields(doc: EvidenceDoc) -> dict[str, str]:
    from packages.schemas.evidence import isoformat

    return {
        "doc_id": doc.doc_id,
        "timestamp": isoformat(doc.ts),
        "node_id": doc.pod,
        "service_id": doc.service,
        "pod_id": doc.pod,
        "severity": doc.severity,
        "event_type": doc.event_type,
        "source": doc.source,
        "message": doc.message,
    }


def test_log_doc_matches_gd1(gd1_prepare):
    raw = _log_row("2022-08-22T03:51:10.529109633Z", "1661140270529109633", "Query product successfully")
    assert _gd1_fields(log_doc(raw, "2022-08-22", KNOWN)) == gd1_prepare._log_event(raw, "2022-08-22")


@pytest.mark.parametrize("duration_ns", [4_245_140, 1_250_000_000])
def test_trace_doc_matches_gd1(gd1_prepare, duration_ns):
    raw = _trace_row("c1d338fbf10c6fee", 1661140244346108571, duration_ns)
    doc = trace_doc(raw, "2022-08-22", KNOWN)
    assert doc is not None
    assert _gd1_fields(doc) == gd1_prepare._trace_event(raw, "2022-08-22")
    assert doc.parent_span_id is None and doc.duration_ms == pytest.approx(duration_ns / 1e6)


def test_clean_drops_noise_and_duplicates_keeps_time_order():
    t0 = datetime(2022, 8, 22, 3, 52, tzinfo=UTC)

    def doc(i: str, ts: datetime, message: str) -> EvidenceDoc:
        return EvidenceDoc(i, ts, POD, "cartservice", "INFO", "application_log", "nezha_log", message)

    docs = [
        doc("b", t0 + timedelta(seconds=1), "later"),
        doc("a", t0, "first"),
        doc("dup", t0, "first"),
        doc("hc", t0, "Periodic healthcheck succeeded"),
    ]
    assert [d.doc_id for d in clean(docs)] == ["a", "b"]


def test_in_memory_query_filters_time_and_service():
    t0 = datetime(2022, 8, 22, 3, 52, tzinfo=UTC)
    docs = [
        EvidenceDoc(f"d{i}", t0 + timedelta(seconds=i), POD, svc, "INFO", "application_log", "nezha_log", f"m{i}")
        for i, svc in enumerate(["cartservice", "frontend", "cartservice", "cartservice"])
    ]
    store = InMemoryEvidenceStore(docs)
    assert [d.doc_id for d in store.query(t0 + timedelta(seconds=1), t0 + timedelta(seconds=2))] == ["d1", "d2"]
    assert [d.doc_id for d in store.query(t0, t0 + timedelta(seconds=9), {"cartservice"})] == ["d0", "d2", "d3"]


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_nezha_store_reads_minute_files_and_dedupes_overlap(tmp_path):
    day = tmp_path / "rca_data" / "2022-08-22"
    in_window = _log_row("2022-08-22T03:53:10.000000001Z", "1661140390000000001", "Adding to cart")
    # File 03_54 overlaps 03_53 by a few seconds: the same line appears in both.
    _write(day / "log" / "03_53_log.csv", [in_window])
    _write(day / "log" / "03_54_log.csv", [in_window, _log_row("2022-08-22T03:54:05Z", "1661140445000000000", "x")])
    _write(day / "log" / "05_00_log.csv", [_log_row("2022-08-22T04:59:30Z", "1661144370000000000", "far")])
    _write(day / "trace" / "03_53_trace.csv", [_trace_row("aaaa", 1661140385000000000, 2_000_000)])

    store = NezhaEvidenceStore(root=tmp_path)
    start = datetime(2022, 8, 22, 3, 53, tzinfo=UTC)
    docs = store.query(start, start + timedelta(seconds=30), {"cartservice"})
    assert [d.event_type for d in docs] == ["trace_span", "application_log"]  # time order
    assert len({d.doc_id for d in docs}) == len(docs) == 2
    assert store.query(start, start + timedelta(seconds=30), {"frontend"}) == []


def test_gd1_corpus_loads_in_gd1_order():
    store = load_gd1_corpus(LEGACY / "nezha_setup" / "processed" / "logs.jsonl")
    assert len(store.docs) > 10_000
    assert all(a.ts <= b.ts for a, b in zip(store.docs, store.docs[1:], strict=False))
