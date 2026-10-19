"""Evidence coverage by label: GD1's corpus vs GD2's full Nezha store.

On the candidates GD1 sent to the judge (dump of scripts/dump_gd1_prompts.py),
compare how often the BM25 top-k is non-empty for fault vs normal windows:

- GD1: the contexts GD1 actually retrieved (label-filtered corpus, global
  search then time filter, fault type in the query);
- GD2: `bm25_hybrid` defaults (full rca_data log/trace store, s0 window pool,
  no fault type), same alert time windows.

If coverage depends on the label, the presence of evidence alone leaks the
label to the judge (docs/experiment-log.md QD-016).

Second part: Nezha itself only ships log/trace files for some minutes (around
fault injections), while metrics are continuous. For every window of the GD2
splits, report whether any log/trace minute file exists within the retrieval
margin (+-8 min), by split and label.

    py scripts/evidence_coverage.py   # -> data/gd1_parity/evidence_coverage.json
"""

from __future__ import annotations

import csv
import json
import sys
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.schemas.evidence import NezhaEvidenceStore, parse_timestamp
from packages.schemas.loaders import load_split_window_ids
from packages.schemas.models import RetrievalBudget
from scripts.check_gd1_parity import DUMP, gd1_candidate
from services.retrieval.bm25_hybrid import Bm25HybridRetriever


def main() -> int:
    rows = [json.loads(line) for line in DUMP.open(encoding="utf-8") if line.strip()]
    rows.sort(key=lambda row: row["alert"]["time_window"]["start"])  # LRU-friendly
    retriever = Bm25HybridRetriever(NezhaEvidenceStore())
    budget = RetrievalBudget(timeout_ms=10**9)
    counts: Counter[str] = Counter()
    pool_sizes: dict[str, list[int]] = {"fault": [], "normal": []}
    for row in rows:
        label = "fault" if row["alert"]["ground_truth"] == "true_alert" else "normal"
        result = retriever.retrieve(gd1_candidate(row["alert"]), budget)
        counts[f"{label}_n"] += 1
        counts[f"{label}_gd1_with_context"] += bool(row["contexts"])
        counts[f"{label}_gd2_with_context"] += bool(result.events)
        pool_sizes[label].append(result.debug["pool_size"])
    report_splits = split_file_coverage(retriever.store)  # type: ignore[arg-type]
    report = {
        **{f"{label}_{side}_coverage": round(counts[f"{label}_{side}_with_context"] / counts[f"{label}_n"], 4)
           for label in ("fault", "normal") for side in ("gd1", "gd2")},
        "counts": dict(counts),
        "gd2_median_pool_size": {k: sorted(v)[len(v) // 2] for k, v in pool_sizes.items() if v},
        "gd2_splits_with_log_trace_files": report_splits,
    }
    out = REPO / "data" / "gd1_parity" / "evidence_coverage.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


def split_file_coverage(store: NezhaEvidenceStore, margin_minutes: int = 8) -> dict[str, dict[str, object]]:
    """Share of split windows with at least one log/trace minute file within the margin."""
    minutes = store._minutes
    margin = timedelta(minutes=margin_minutes)
    with (REPO / "data" / "window_index.csv").open(encoding="utf-8", newline="") as handle:
        index = {row["window_id"]: row for row in csv.DictReader(handle)}
    out: dict[str, dict[str, object]] = {}
    for split in ("dev", "val", "test"):
        counts: Counter[str] = Counter()
        for window_id in load_split_window_ids(split):
            row = index[window_id]
            start = parse_timestamp(row["start_ts"])
            label = "fault" if row["is_fault"] == "1" else "normal"
            lo = bisect_left(minutes, start - margin - timedelta(minutes=1))
            hi = bisect_right(minutes, start + timedelta(minutes=1) + margin + timedelta(minutes=2))
            counts[f"{label}_n"] += 1
            counts[f"{label}_covered"] += hi > lo
        out[split] = {
            **dict(counts),
            **{f"{label}_coverage": round(counts[f"{label}_covered"] / counts[f"{label}_n"], 4)
               for label in ("fault", "normal") if counts[f"{label}_n"]},
        }
    return out


if __name__ == "__main__":
    raise SystemExit(main())
