"""Per (service, operation) `duration_ms` baseline for C3 (M6, QD-027, QD-029).

C3 asks whether a cited span is abnormally slow for its own operation, so the
threshold must come from spans that were not themselves slow because of a fault.
A normal label is not enough: labels are per pod, so during an injection the other
pods of the same system are labelled normal while the fault propagates to them.
Only spans in a normal `dev` window, outside every labelled injection interval of
that system, are kept; `SpanSelector` gives the reason for every other span.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from packages.schemas.evidence import EvidenceDoc
from packages.schemas.nezha import (
    LABEL_AFTER_SECONDS,
    LABEL_BEFORE_SECONDS,
    WINDOW_SECONDS,
    Injection,
    Window,
)

PERCENTILES = (50, 90, 95, 99)
MIN_SPANS = 30  # fewer spans than this: no reliable percentile, `threshold` gives None
_SPAN_MESSAGE = re.compile(r"^Trace span (?P<operation>.+) on \S+ duration_ms=[0-9.]+$")


def span_operation(message: str) -> str | None:
    """Operation name out of a `trace_doc` message (cached H0 events carry only the message)."""
    match = _SPAN_MESSAGE.match(message)
    return match["operation"] if match else None


class SpanSelector:
    """Decides which spans may enter the baseline."""

    def __init__(self, windows: Iterable[Window], dev_ids: set[str], injections: Iterable[Injection]) -> None:
        self._starts: dict[str, list[datetime]] = {}
        self._windows: dict[str, list[Window]] = {}
        grouped: dict[str, list[Window]] = defaultdict(list)
        for window in windows:
            grouped[window.pod].append(window)
        for pod, items in grouped.items():
            items.sort(key=lambda w: w.start_ts)
            self._windows[pod] = items
            self._starts[pod] = [w.start_ts for w in items]
        self.dev_ids = dev_ids
        busy: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
        for injection in injections:
            busy[injection.system].append(
                (
                    injection.inject_ts - timedelta(seconds=LABEL_BEFORE_SECONDS),
                    injection.inject_ts + timedelta(seconds=LABEL_AFTER_SECONDS),
                )
            )
        self._busy = {system: _merged(spans) for system, spans in busy.items()}

    def reason(self, doc: EvidenceDoc) -> str:
        """`kept`, or why the span is left out."""
        starts = self._starts.get(doc.pod)
        if starts is None:
            return "no_window"
        index = bisect_right(starts, doc.ts) - 1
        if index < 0:
            return "no_window"
        window = self._windows[doc.pod][index]
        if (doc.ts - window.start_ts).total_seconds() >= WINDOW_SECONDS:
            return "no_window"
        if window.window_id not in self.dev_ids:
            return "not_dev"
        if window.is_fault:
            return "fault_window"
        if _covered(self._busy.get(window.system, ()), doc.ts):
            return "during_injection"
        return "kept"


def _merged(spans: Sequence[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _covered(spans: Sequence[tuple[datetime, datetime]], ts: datetime) -> bool:
    index = bisect_right([start for start, _ in spans], ts) - 1
    return index >= 0 and ts <= spans[index][1]


def percentile_rows(durations: Mapping[tuple[str, str], Sequence[float]]) -> pd.DataFrame:
    """One row per (service, operation): n, p50, p90, p95, p99."""
    rows = []
    for (service, operation), values in sorted(durations.items()):
        points = np.percentile(np.asarray(values, dtype=float), PERCENTILES)
        rows.append(
            {
                "service": service,
                "operation": operation,
                "n": len(values),
                **{f"p{p}": float(v) for p, v in zip(PERCENTILES, points, strict=True)},
            }
        )
    columns = ["service", "operation", "n", *[f"p{p}" for p in PERCENTILES]]
    return pd.DataFrame(rows, columns=columns)


class RollingSpanBaseline:
    """Per (service, operation) percentile over the spans of the `lookback` before an alert window
    (V30, QD-031): the window [window_start - guard - lookback, window_start - guard).

    The `dev` baseline covers only about 32% of the spans retrieved on `val`
    (QD-030, Finding 8) because the split leaves several services without a `dev`
    normal window. The rolling baseline needs no label: it uses the history every
    deployment has. If a fault starts before the alert window, faulty spans can
    enter it, which makes C3 more conservative, never less.
    """

    def __init__(self, spans: Mapping[tuple[str, str | None], tuple[np.ndarray, np.ndarray]]) -> None:
        """`spans`: key -> (start timestamps in epoch seconds, durations in ms), sorted by time."""
        self._spans = spans

    @classmethod
    def from_docs(cls, docs: Iterable[EvidenceDoc]) -> RollingSpanBaseline:
        """Index trace docs by key; docs with the same id (overlapping minute files) count once."""
        grouped: dict[tuple[str, str | None], dict[str, tuple[float, float]]] = defaultdict(dict)
        for doc in docs:
            if doc.event_type != "trace_span":
                continue
            grouped[(doc.service, span_operation(doc.message))][doc.doc_id] = (
                doc.ts.timestamp(),
                float(doc.duration_ms or 0.0),
            )
        spans = {}
        for key, items in grouped.items():
            rows = np.array(sorted(items.values()), dtype=float)
            spans[key] = (rows[:, 0], rows[:, 1])
        return cls(spans)

    def thresholds(
        self,
        service: str,
        operation: str | None,
        window_start: datetime,
        lookback_minutes: float,
        guard_seconds: float,
        percentiles: Sequence[int],
        min_spans: int = MIN_SPANS,
    ) -> tuple[int, dict[int, float] | None]:
        """(spans in the lookback, {percentile: duration_ms}); None when fewer than `min_spans`."""
        times, durations = self._spans.get((service, operation), (np.empty(0), np.empty(0)))
        end = window_start.timestamp() - guard_seconds
        hi = int(np.searchsorted(times, end, side="left"))
        lo = int(np.searchsorted(times, end - lookback_minutes * 60, side="left"))
        n = hi - lo
        if n < min_spans:
            return n, None
        points = np.percentile(durations[lo:hi], list(percentiles))
        return n, {int(p): float(v) for p, v in zip(percentiles, points, strict=True)}


class SpanBaseline:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._rows = {(r.service, r.operation): r for r in frame.itertuples(index=False)}

    def threshold(self, service: str, operation: str, percentile: int) -> float | None:
        """Baseline at `percentile`, or None for an unseen key or fewer than MIN_SPANS spans."""
        row = self._rows.get((service, operation))
        if row is None or row.n < MIN_SPANS:
            return None
        return float(getattr(row, f"p{percentile}"))
