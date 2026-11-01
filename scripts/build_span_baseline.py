"""Span duration baseline on `dev` for C3 (M6, QD-029). See services/judge/span_baseline.py.

    py scripts/build_span_baseline.py --out data/span_baseline.parquet --summary m6_span_baseline_v1

Writes the parquet (data/ is not committed) and eval/results/<summary>/summary.json; neither
is overwritten. Reads every trace CSV once; no LLM call.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "eval" / "results"
sys.path.insert(0, str(REPO))

from packages.schemas.evidence import NezhaEvidenceStore  # noqa: E402
from packages.schemas.loaders import load_split_window_ids  # noqa: E402
from packages.schemas.nezha import dataset_root, load_injections, read_window_index  # noqa: E402
from services.judge.span_baseline import (  # noqa: E402
    MIN_SPANS,
    SpanBaseline,
    SpanSelector,
    percentile_rows,
    span_operation,
)


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO, check=True).stdout.strip()


def coverage(baseline: SpanBaseline, run_id: str) -> dict[str, Any]:
    """Of the local trace events a run retrieved: how many have a threshold, how many exceed it."""
    total = covered = over_p95 = over_p99 = 0
    missing: Counter[str] = Counter()
    with (RESULTS / run_id / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            for event in json.loads(line)["events"]:
                if event["modality"] != "trace":
                    continue
                total += 1
                operation = span_operation(event["content"])
                p95 = baseline.threshold(event["service"], operation, 95) if operation else None
                p99 = baseline.threshold(event["service"], operation, 99) if operation else None
                if p95 is None or p99 is None:
                    missing[event["service"]] += 1
                    continue
                covered += 1
                duration = float(event["debug"]["duration_ms"])
                over_p95 += duration > p95
                over_p99 += duration > p99
    return {
        "trace_events": total,
        "covered": covered,
        "covered_share": covered / total if total else None,
        "over_p95_share_of_covered": over_p95 / covered if covered else None,
        "over_p99_share_of_covered": over_p99 / covered if covered else None,
        "uncovered_by_service": dict(missing.most_common(10)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--windows", type=Path, default=REPO / "data" / "window_index.csv")
    parser.add_argument("--coverage-runs", default="h0_val_bm25_v3,h0_val_c1_k0_v1")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else REPO / args.out
    summary_dir = RESULTS / args.summary
    if out.exists() or summary_dir.exists():
        raise SystemExit(f"{out} or {summary_dir} already exists: results are never overwritten")

    started = time.perf_counter()
    root = dataset_root()
    selector = SpanSelector(read_window_index(args.windows), load_split_window_ids("dev"), load_injections(root))
    store = NezhaEvidenceStore(root, cache_files=2)
    wide = timedelta(days=365 * 20)
    anchor = datetime(2022, 1, 1, tzinfo=UTC)
    files = [f for f in store.files_for(anchor, anchor + wide) if f.kind == "trace"]

    reasons: Counter[str] = Counter()
    kept: dict[tuple[str, str], list[float]] = defaultdict(list)
    during: dict[tuple[str, str], list[float]] = defaultdict(list)
    seen: set[str] = set()
    for file in files:
        for doc in store.load_file(file):
            if doc.doc_id in seen:  # consecutive minute files overlap by a few seconds
                reasons["duplicate"] += 1
                continue
            seen.add(doc.doc_id)
            reason = selector.reason(doc)
            reasons[reason] += 1
            if reason not in ("kept", "during_injection"):
                continue
            operation = span_operation(doc.message)
            if operation is None or doc.duration_ms is None:
                reasons["unparsed"] += 1
                continue
            (kept if reason == "kept" else during)[(doc.service, operation)].append(doc.duration_ms)

    frame = percentile_rows(kept)
    other = percentile_rows(during).set_index(["service", "operation"])
    ratios = []
    for row in frame.itertuples(index=False):
        key = (row.service, row.operation)
        if row.n >= MIN_SPANS and key in other.index and other.loc[key, "n"] >= MIN_SPANS and row.p95 > 0:
            ratios.append(float(other.loc[key, "p95"]) / row.p95)
    summary = {
        "git_commit": _git_commit(),
        "created_at": datetime.now(UTC).isoformat(),
        "trace_files": len(files),
        "span_reasons": dict(reasons.most_common()),
        "keys": len(frame),
        "keys_with_min_spans": int((frame["n"] >= MIN_SPANS).sum()),
        "min_spans": MIN_SPANS,
        "keys_compared_during_injection": len(ratios),
        "median_p95_ratio_during_vs_clean": statistics.median(ratios) if ratios else None,
        "share_keys_p95_higher_during": sum(1 for r in ratios if r > 1) / len(ratios) if ratios else None,
        "coverage": {run: coverage(SpanBaseline(frame), run) for run in args.coverage_runs.split(",")},
        "wall_seconds": round(time.perf_counter() - started, 1),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    summary_dir.mkdir(parents=True)
    (summary_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
