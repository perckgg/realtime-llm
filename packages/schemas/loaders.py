"""Nezha dataset loader that emits packages.schemas.TelemetryWindow.

This is the wrapper promised in the Week 1 "Tuần sau" note: it
reuses the Week 1 labelling logic in scripts/nezha_windows.py (window
definition, wall-clock vs epoch join, pod -> service mapping) so that no
service downstream has to parse the Nezha CSVs itself and risk repeating the
timestamp bug documented in docs/label-audit.md §5 / docs/experiment-log.md
QĐ-002.

Week 1's scripts/nezha_windows.py deliberately only produced a label (fault or
normal) per window, not the metric values, because Week 1 was not allowed to
write pipeline code (docs/CURRENT-WEEK.md). This module adds the metric
values, wrapped in the TelemetryWindow/MetricPoint schema from
docs/Final_Thesis_Phase2/03-schemas-and-contracts.md §1.1, for Week 2's
replayer.

Logs and traces are intentionally left as empty lists here: no Week 2 service
consumes them yet (the detector only looks at `metrics`), and building them
would mean guessing a join/parsing strategy that hasn't been asked for. When
retrieval (services/retrieval) needs LogEvent/TraceSpan content, extend this
loader then -- don't let retrieval parse CSVs on its own either.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections.abc import Iterator
from pathlib import Path

from packages.schemas.models import MetricPoint, TelemetryWindow, WindowLabel
from scripts.nezha_windows import (
    DEFAULT_TIME_SOURCE,
    LABEL_AFTER_SECONDS,
    LABEL_BEFORE_SECONDS,
    Injection,
    TimeSource,
    _matching_injection,
    dataset_root,
    load_injections,
    load_known_services,
    make_window_id,
    parse_wall_clock,
    pod_to_service,
)

# Columns that are timestamps or identifiers, not metric values.
_NON_METRIC_COLUMNS = {"Time", "TimeStamp", "PodName"}


def load_split_window_ids(split: str, splits_dir: Path | None = None) -> set[str]:
    """Read the committed `window_ids` list from `data/splits/{split}.json`.

    `splits_dir` defaults to `SPLITS_DIR` (see .env.example), matching the
    convention `dataset_root()` uses for `NEZHA_DATA_DIR`. The split files are
    committed by scripts/make_splits.py (Week 1) and must not be regenerated
    here -- this only reads them.
    """
    root = splits_dir if splits_dir is not None else Path(os.environ.get("SPLITS_DIR", "./data/splits"))
    with (root / f"{split}.json").open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return set(payload["window_ids"])


def iter_telemetry_windows(
    root: Path | None = None,
    time_source: TimeSource = DEFAULT_TIME_SOURCE,
    window_ids: set[str] | None = None,
    limit: int | None = None,
) -> Iterator[TelemetryWindow]:
    """Yield labelled TelemetryWindow objects from the Nezha metric CSVs.

    Args:
        root: dataset root, defaults to scripts.nezha_windows.dataset_root().
        time_source: "wall" (default, matches the committed splits) or
            "epoch" (reproduces the Phase 1 bug-for-bug labelling — see
            docs/experiment-log.md QĐ-002). Never hardcode this in a caller;
            it must come from the run config once one exists.
        window_ids: if given, only yield windows whose deterministic
            window_id is in this set. Used to replay an exact committed split
            (data/splits/*.json) without regenerating data/window_index.csv.
        limit: stop after this many *matching* windows. None means no limit.

    Windows are read in file order, i.e. per-pod, not globally time-sorted.
    Callers that need time order (e.g. the replayer's watermark) must sort
    the materialized list themselves -- kept a generator here so a caller
    that only wants a handful of windows (window_ids) doesn't have to hold
    the whole corpus in memory.
    """
    root = root if root is not None else dataset_root()
    known = load_known_services(root)
    by_day: dict[str, list[Injection]] = {}
    for injection in load_injections(root, time_source):
        by_day.setdefault(injection.day, []).append(injection)

    before_after = (LABEL_BEFORE_SECONDS, LABEL_AFTER_SECONDS)

    yielded = 0
    for path in sorted((root / "rca_data").glob("*/metric/*_metric.csv")):
        day = path.parent.parent.name
        day_injections = by_day.get(day, ())
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            metric_names = [name for name in (reader.fieldnames or []) if name not in _NON_METRIC_COLUMNS]
            for raw in reader:
                window = _row_to_window(raw, day, known, day_injections, time_source, metric_names, before_after)
                if window is None:
                    continue
                if window_ids is not None and window.window_id not in window_ids:
                    continue
                yield window
                yielded += 1
                if limit is not None and yielded >= limit:
                    return


def _row_to_window(
    raw: dict[str, str],
    day: str,
    known: dict[str, str],
    day_injections,
    time_source: TimeSource,
    metric_names: list[str],
    before_after: tuple[int, int],
) -> TelemetryWindow | None:
    from datetime import timedelta

    try:
        if time_source == "wall":
            start_ts = parse_wall_clock(raw["Time"])
        else:
            start_ts = _epoch_ts(raw["TimeStamp"])
        pod = raw.get("PodName") or ""
    except (KeyError, TypeError, ValueError):
        return None
    if not pod:
        return None

    service, _ = pod_to_service(pod, known)
    window_id = make_window_id(service, pod, start_ts)
    end_ts = start_ts + timedelta(seconds=60)

    metrics: list[MetricPoint] = []
    for name in metric_names:
        value = raw.get(name)
        if value is None or value == "":
            continue
        try:
            parsed = float(value)
        except ValueError:
            continue
        if not math.isfinite(parsed):
            # The Pod*Latency P90/P95/P99 columns hold the literal string "NaN"
            # for windows with zero requests (percentile undefined, not zero
            # latency) -- affects 28.6% of windows corpus-wide. Dropped here
            # rather than kept as 0.0/inf, which would misrepresent an idle
            # window as a fast one. See docs/experiment-log.md QD-009.
            continue
        metrics.append(MetricPoint(name=name, value=parsed, ts=start_ts))

    before = timedelta(seconds=before_after[0])
    after = timedelta(seconds=before_after[1])
    hit = _matching_injection(start_ts, pod, day_injections, before, after)
    label = WindowLabel(
        is_fault=hit is not None,
        fault_type=hit.fault_type if hit else "normal",
        root_cause_service=hit.root_cause_service if hit else None,
    )
    return TelemetryWindow(
        window_id=window_id,
        service=service,
        pod=pod,
        start_ts=start_ts,
        end_ts=end_ts,
        metrics=metrics,
        logs=[],
        spans=[],
        label=label,
    )


def _epoch_ts(value: str):
    from datetime import UTC, datetime

    return datetime.fromtimestamp(int(float(value)), tz=UTC)
