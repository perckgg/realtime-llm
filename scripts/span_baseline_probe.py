"""Can a rolling baseline replace the `dev` one for C3? (M6, QD-030). No label, no LLM call.

    py scripts/span_baseline_probe.py --out m6_rolling_probe_v1

For every local trace event a run retrieved: the same (service, operation) spans in the
`minutes` before the alert window, ending `GUARD_SECONDS` before it, give a p95 when at least
MIN_SPANS exist. Reports coverage, the share of events above that p95, and rolling p95 / `dev`
p95 on the keys that have both.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "eval" / "results"
sys.path.insert(0, str(REPO))

from packages.schemas.evidence import NezhaEvidenceStore  # noqa: E402
from packages.schemas.nezha import dataset_root  # noqa: E402
from services.judge.span_baseline import MIN_SPANS, SpanBaseline, span_operation  # noqa: E402

GUARD_SECONDS = 60
LOOKBACKS = (10, 30, 60)
Key = tuple[str, str | None]


def span_index() -> dict[Key, tuple[np.ndarray, np.ndarray]]:
    """(start timestamps, durations) of every span per key, sorted by time, duplicates removed."""
    store = NezhaEvidenceStore(dataset_root(), cache_files=2)
    anchor = datetime(2022, 1, 1, tzinfo=UTC)
    spans: dict[Key, dict[str, tuple[float, float]]] = defaultdict(dict)
    for file in store.files_for(anchor, anchor + timedelta(days=7300)):
        if file.kind != "trace":
            continue
        for doc in store.load_file(file):
            spans[(doc.service, span_operation(doc.message))][doc.doc_id] = (doc.ts.timestamp(), float(doc.duration_ms or 0))
    index = {}
    for key, items in spans.items():
        rows = np.array(sorted(items.values()))
        index[key] = (rows[:, 0], rows[:, 1])
    return index


def probe_run(run_id: str, index: dict[Key, tuple[np.ndarray, np.ndarray]], dev: SpanBaseline) -> dict[str, Any]:
    with (RESULTS / run_id / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        starts = {r["window_id"]: datetime.fromisoformat(r["window_ts"]).timestamp() for r in csv.DictReader(handle)}
    total = dev_covered = 0
    covered: Counter[int] = Counter()
    over: Counter[int] = Counter()
    only_rolling: Counter[int] = Counter()
    ratios: dict[int, list[float]] = defaultdict(list)
    empty = (np.array([]), np.array([]))
    with (RESULTS / run_id / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            end = starts[row["window_id"]] - GUARD_SECONDS
            for event in row["events"]:
                if event["modality"] != "trace":
                    continue
                total += 1
                operation = span_operation(event["content"])
                dev_p95 = dev.threshold(event["service"], operation, 95) if operation else None
                dev_covered += dev_p95 is not None
                times, durations = index.get((event["service"], operation), empty)
                hi = bisect_left(times, end)
                for minutes in LOOKBACKS:
                    lo = bisect_left(times, end - minutes * 60)
                    if hi - lo < MIN_SPANS:
                        continue
                    covered[minutes] += 1
                    p95 = float(np.percentile(durations[lo:hi], 95))
                    over[minutes] += float(event["debug"]["duration_ms"]) > p95
                    if dev_p95 is None:
                        only_rolling[minutes] += 1
                    elif dev_p95 > 0:
                        ratios[minutes].append(p95 / dev_p95)
    return {
        "trace_events": total,
        "dev_covered": dev_covered,
        "dev_covered_share": dev_covered / total,
        "rolling": {
            str(m): {
                "covered": covered[m],
                "covered_share": covered[m] / total,
                "only_rolling": only_rolling[m],
                "over_p95_share_of_covered": over[m] / covered[m] if covered[m] else None,
                "median_rolling_over_dev_p95": statistics.median(ratios[m]) if ratios[m] else None,
                "pairs_compared": len(ratios[m]),
            }
            for m in LOOKBACKS
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline", type=Path, default=REPO / "data" / "span_baseline.parquet")
    parser.add_argument("--runs", default="h0_val_bm25_v3,h0_val_c1_k0_v1")
    args = parser.parse_args()
    out = RESULTS / args.out
    if out.exists():
        raise SystemExit(f"{out} already exists: results are never overwritten")
    index = span_index()
    dev = SpanBaseline(pd.read_parquet(args.baseline))
    report = {
        "guard_seconds": GUARD_SECONDS,
        "min_spans": MIN_SPANS,
        "keys_in_corpus": len(index),
        "runs": {run: probe_run(run, index, dev) for run in args.runs.split(",")},
    }
    out.mkdir(parents=True)
    (out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
