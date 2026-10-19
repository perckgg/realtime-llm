"""Nezha logs and traces as an evidence corpus for services/retrieval.

Each raw log line or trace span becomes one `EvidenceDoc` carrying exactly the
fields, ids and text GD1 built in legacy/nezha_setup/prepare_nezha_data.py
(`_log_event`, `_trace_event`) and kept after legacy/src/preprocessing/
log_preprocessing.py (health-check noise dropped, duplicates on
(timestamp, service, message) dropped). Keeping GD1's doc ids and text is what
lets the ported BM25 and judge prompt hit GD1's Gemini cache (M3, G-paper).

Two stores, same `query()`:

- `NezhaEvidenceStore` -- GD2. Reads `rca_data/<day>/{log,trace}/HH_MM_*.csv`
  lazily, one file per minute, with a small LRU, and returns the events of a
  time range. It indexes the **whole** dataset. GD1's corpus kept only events
  within [-300 s, +600 s] of a labelled fault (`context_filter_rule` in
  legacy/nezha_setup/processed/summary.json), so whether a window had any
  evidence depended on its label (docs/experiment-log.md QD-016). GD2 never
  filters evidence by label.
- `InMemoryEvidenceStore` -- a fixed list of docs, e.g. GD1's processed corpus
  via `load_gd1_corpus()` for the parity gates (G-port, G-paper), or tests.

Service names come from `packages.schemas.nezha.pod_to_service`, the same
mapping as TelemetryWindow.service.
"""

from __future__ import annotations

import csv
import json
import re
from bisect import bisect_left, bisect_right
from collections import OrderedDict
from collections.abc import Collection, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from packages.schemas.nezha import dataset_root, load_known_services, pod_to_service

# legacy/src/preprocessing/log_preprocessing.py NOISE_PATTERNS
NOISE_PATTERNS = [re.compile(r"periodic healthcheck succeeded", re.IGNORECASE)]

_FILE_RE = re.compile(r"^(?P<hour>\d{2})_(?P<minute>\d{2})_(?P<kind>log|trace)\.csv$")


@dataclass(frozen=True, slots=True)
class EvidenceDoc:
    """One log line or trace span, in GD1's LogEvent shape (legacy/src/models.py)."""

    doc_id: str
    ts: datetime
    pod: str
    service: str
    severity: str  # INFO | WARN | ERROR ... (traces: WARN iff duration >= 1000 ms)
    event_type: str  # application_log | trace_span
    source: str  # nezha_log | nezha_trace
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    duration_ms: float | None = None

    @property
    def modality(self) -> Literal["log", "trace"]:
        return "trace" if self.event_type == "trace_span" else "log"

    def text(self) -> str:
        """Indexed text -- legacy/src/retrieval/context_store.py `_event_text`."""
        return f"{self.service} {self.pod} {self.severity} {self.event_type} {self.source} {self.message}"


def parse_timestamp(value: str) -> datetime:
    """legacy/src/time_utils.py `parse_timestamp` (sub-microsecond digits are truncated)."""
    parsed = datetime.fromisoformat(value)  # GD1: value.replace("Z", "+00:00"); same result on 3.11+
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def isoformat(value: datetime) -> str:
    """legacy/src/time_utils.py `isoformat`."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_log_payload(value: str) -> dict[str, Any]:
    try:
        outer = json.loads(value)
        inner = outer.get("log", "")
        if isinstance(inner, str):
            parsed = json.loads(inner.strip())
            return parsed if isinstance(parsed, dict) else {}
        if isinstance(inner, dict):
            return inner
    except (ValueError, AttributeError, TypeError):
        return {}
    return {}


def log_doc(raw: dict[str, str], day: str, known: dict[str, str]) -> EvidenceDoc | None:
    """One `rca_data/<day>/log/*_log.csv` row -- GD1 `_log_event`."""
    try:
        ts = parse_timestamp(raw["Timestamp"])
        pod = raw.get("PodName") or "unknown"
        parsed = _parse_log_payload(raw.get("Log", ""))
        severity = str(parsed.get("severity") or "INFO").upper()
        message = str(parsed.get("message") or parsed.get("log") or raw.get("Log", ""))[:1000]
    except (KeyError, ValueError, TypeError):
        return None
    return EvidenceDoc(
        doc_id=f"log-{day}-{raw.get('TraceID', '')}-{raw.get('SpanID', '')}-{raw.get('TimeUnixNano', '')}",
        ts=ts,
        pod=pod,
        service=pod_to_service(pod, known)[0],
        severity=severity,
        event_type="application_log",
        source="nezha_log",
        message=message,
        trace_id=raw.get("TraceID") or None,
        span_id=raw.get("SpanID") or None,
    )


def trace_doc(raw: dict[str, str], day: str, known: dict[str, str]) -> EvidenceDoc | None:
    """One `rca_data/<day>/trace/*_trace.csv` row -- GD1 `_trace_event`."""
    try:
        start_ns = int(raw["StartTimeUnixNano"])
        end_ns = int(raw["EndTimeUnixNano"])
        # Same float division as GD1, so the microsecond in the prompt matches.
        ts = datetime.fromtimestamp(start_ns / 1_000_000_000, tz=UTC)
        duration_ms = (end_ns - start_ns) / 1_000_000
        pod = raw.get("PodName") or "unknown"
        operation = raw.get("OperationName", "unknown")
    except (KeyError, ValueError, TypeError):
        return None
    parent = raw.get("ParentID") or None
    return EvidenceDoc(
        doc_id=f"trace-{day}-{raw.get('TraceID', '')}-{raw.get('SpanID', '')}",
        ts=ts,
        pod=pod,
        service=pod_to_service(pod, known)[0],
        severity="WARN" if duration_ms >= 1000 else "INFO",
        event_type="trace_span",
        source="nezha_trace",
        message=f"Trace span {operation} on {pod} duration_ms={duration_ms:.3f}",
        trace_id=raw.get("TraceID") or None,
        span_id=raw.get("SpanID") or None,
        parent_span_id=None if parent == "root" else parent,
        duration_ms=duration_ms,
    )


def clean(docs: Iterable[EvidenceDoc]) -> list[EvidenceDoc]:
    """GD1 `preprocess_logs`: drop health-check noise and (timestamp, service,
    message) duplicates, keep the first; then sort by time (stable)."""
    seen: set[tuple[str, str, str]] = set()
    kept: list[EvidenceDoc] = []
    for doc in docs:
        if any(pattern.search(doc.message) for pattern in NOISE_PATTERNS):
            continue
        key = (doc.ts.isoformat(), doc.service, doc.message)
        if key in seen:
            continue
        seen.add(key)
        kept.append(doc)
    return sorted(kept, key=lambda doc: doc.ts)


class InMemoryEvidenceStore:
    """A fixed corpus, kept in `clean()` order (time, then input order)."""

    def __init__(self, docs: Iterable[EvidenceDoc], already_clean: bool = False) -> None:
        self.docs: list[EvidenceDoc] = list(docs) if already_clean else clean(docs)
        self._ts = [doc.ts for doc in self.docs]

    def query(
        self, start: datetime, end: datetime, services: Collection[str] | None = None
    ) -> list[EvidenceDoc]:
        """Docs with start <= ts <= end (and service in `services`, if given)."""
        lo, hi = bisect_left(self._ts, start), bisect_right(self._ts, end)
        return [d for d in self.docs[lo:hi] if services is None or d.service in services]


def load_gd1_corpus(path: Path) -> InMemoryEvidenceStore:
    """GD1's processed corpus (legacy/nezha_setup/processed/logs.jsonl) for
    the parity gates. Label-filtered by construction -- never use it for GD2
    results (QD-016)."""
    docs: list[EvidenceDoc] = []
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            r = json.loads(line)
            docs.append(
                EvidenceDoc(
                    doc_id=str(r.get("doc_id") or f"log-{index + 1}"),
                    ts=parse_timestamp(str(r["timestamp"])),
                    pod=str(r.get("node_id", "unknown")),
                    service=str(r.get("service_id", "unknown")),
                    severity=str(r.get("severity", "INFO")).upper(),
                    event_type=str(r.get("event_type", "log")),
                    source=str(r.get("source", "log")),
                    message=str(r.get("message", "")),
                )
            )
    return InMemoryEvidenceStore(docs)


@dataclass(frozen=True)
class _MinuteFile:
    path: Path
    day: str
    minute: datetime
    kind: Literal["log", "trace"]


class NezhaEvidenceStore:
    """All of `rca_data`, loaded one per-minute file at a time.

    Nezha writes one log and one trace CSV per minute (`HH_MM_log.csv`); a file
    holds roughly the minute *before* its name plus a few seconds of overlap,
    so a query for [start, end] reads files named start-1 min .. end+2 min and
    filters exactly. Duplicates in the overlap are removed by `clean()`.
    The replayer moves forward in time, so a small LRU keeps the cost to about
    two file parses per new minute.
    """

    def __init__(self, root: Path | None = None, cache_files: int = 48) -> None:
        self.root = root or dataset_root()
        self.cache_files = cache_files
        self._known = load_known_services(self.root)
        self._files: list[_MinuteFile] = sorted(self._index(), key=lambda f: (f.minute, f.kind))
        self._minutes = [f.minute for f in self._files]
        self._cache: OrderedDict[Path, list[EvidenceDoc]] = OrderedDict()

    def _index(self) -> Iterator[_MinuteFile]:
        for kind in ("log", "trace"):
            for path in (self.root / "rca_data").glob(f"*/{kind}/*_{kind}.csv"):
                match = _FILE_RE.match(path.name)
                if not match:
                    continue
                day = path.parent.parent.name
                minute = datetime.strptime(
                    f"{day} {match['hour']}:{match['minute']}", "%Y-%m-%d %H:%M"
                ).replace(tzinfo=UTC)
                yield _MinuteFile(path, day, minute, kind)  # type: ignore[arg-type]

    def _load(self, file: _MinuteFile) -> list[EvidenceDoc]:
        cached = self._cache.get(file.path)
        if cached is not None:
            self._cache.move_to_end(file.path)
            return cached
        parse = log_doc if file.kind == "log" else trace_doc
        docs: list[EvidenceDoc] = []
        with file.path.open(newline="", encoding="utf-8-sig") as handle:
            for raw in csv.DictReader(handle):
                doc = parse(raw, file.day, self._known)
                if doc is not None:
                    docs.append(doc)
        self._cache[file.path] = docs
        while len(self._cache) > self.cache_files:
            self._cache.popitem(last=False)
        return docs

    def has_telemetry(self, start: datetime, end: datetime, margin: timedelta = timedelta(minutes=8)) -> bool:
        """True if Nezha has any log or trace file within `margin` of [start, end].

        QD-017: Nezha only ships logs/traces for minutes around fault
        injections, so the main metrics are computed on windows where this is
        true. Uses only the dataset's file list, never labels."""
        lo = bisect_left(self._minutes, start - margin - timedelta(minutes=1))
        hi = bisect_right(self._minutes, end + margin + timedelta(minutes=2))
        return hi > lo

    def query(
        self, start: datetime, end: datetime, services: Collection[str] | None = None
    ) -> list[EvidenceDoc]:
        lo = bisect_left(self._minutes, start - timedelta(minutes=1))
        hi = bisect_right(self._minutes, end + timedelta(minutes=2))
        selected: list[EvidenceDoc] = []
        for file in self._files[lo:hi]:
            selected.extend(
                d
                for d in self._load(file)
                if start <= d.ts <= end and (services is None or d.service in services)
            )
        # GD1 put every log before every trace, then sorted by time (stable).
        selected.sort(key=lambda d: d.event_type == "trace_span")
        return clean(selected)
