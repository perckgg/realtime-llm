"""Blind sample for the manual context-precision grading (M8 task 9, V35; 02 SS4.2). No LLM call.

    py scripts/m8_context_precision_sample.py --runs bm25=h0_test_bm25_v1,c1=h0_test_c1_k0_v1 \
        --n 50 --seed 42 --out eval/manual/context_precision_test_v1

Pool: candidate windows with telemetry for which *every* run retrieved at least one event, so
each method is graded on the same windows (paired). Half of the sample is drawn from fault
windows and half from normal ones (the label is used for the draw only and is hidden from the
grader); if a stratum is too small the other one fills the sample.

Writes two files (neither may exist):

- `<out>.csv` -- what the grader fills in. One row per (window, distinct event); an event that
  several methods retrieved appears once. Windows and the events inside a window are in a
  seeded random order, so neither the method, its rank nor the label can be read off the file.
- `<out>.key.csv` -- the mapping back (window_id, event_id, label, which run retrieved the
  event at which rank). Not to be opened before the grading is finished.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.runner import RESULTS  # noqa: E402

GRADE_FIELDS = [
    "window_no", "event_no", "alert_service", "alert_pod", "window_start", "anomaly_score", "top_features",
    "event_ts", "seconds_from_window_start", "event_service", "event_pod", "modality", "severity", "content",
    "relevance", "note",
]  # fmt: skip


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


def load_events(run_id: str) -> dict[str, list[dict[str, Any]]]:
    """window_id -> retrieved events in rank order (windows with an empty context are left out)."""
    out = {}
    with (RESULTS / run_id / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["events"]:
                out[row["window_id"]] = row["events"]
    return out


def draw(rows: list[dict[str, str]], eligible: set[str], n: int, seed: int) -> list[str]:
    """`n` window ids, half fault / half normal where possible, in a seeded random order."""
    rng = random.Random(seed)
    pool = [r for r in rows if r["window_id"] in eligible and _flag(r["is_candidate"]) and _flag(r["has_telemetry"])]
    fault = sorted(r["window_id"] for r in pool if _flag(r["label_is_fault"]))
    normal = sorted(r["window_id"] for r in pool if not _flag(r["label_is_fault"]))
    if len(fault) + len(normal) < n:
        raise ValueError(f"only {len(fault) + len(normal)} eligible windows, asked for {n}")
    n_fault = min(n // 2, len(fault))
    n_normal = min(n - n_fault, len(normal))
    n_fault = n - n_normal  # the fault stratum fills up if normal windows are short
    chosen = rng.sample(fault, n_fault) + rng.sample(normal, n_normal)
    rng.shuffle(chosen)
    return chosen


def build(
    rows: list[dict[str, str]], events: dict[str, dict[str, list[dict[str, Any]]]], n: int, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = set.intersection(*(set(by_window) for by_window in events.values()))
    by_id = {r["window_id"]: r for r in rows}
    rng = random.Random(seed + 1)  # event order: independent of the window draw
    grade: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    for window_no, window_id in enumerate(draw(rows, eligible, n, seed), start=1):
        window = by_id[window_id]
        start = datetime.fromisoformat(window["window_ts"])
        merged: dict[str, dict[str, Any]] = {}
        ranks: dict[str, dict[str, int]] = {}
        for run_name, by_window in events.items():
            for rank, event in enumerate(by_window[window_id], start=1):
                merged.setdefault(event["event_id"], event)
                ranks.setdefault(event["event_id"], {})[run_name] = rank
        order = sorted(merged)
        rng.shuffle(order)
        for event_no, event_id in enumerate(order, start=1):
            event = merged[event_id]
            debug = event.get("debug") or {}
            ts = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
            grade.append({
                "window_no": window_no,
                "event_no": event_no,
                "alert_service": window["service"],
                "alert_pod": window["pod"],
                "window_start": window["window_ts"],
                "anomaly_score": window["anomaly_score"],
                "top_features": window["top_features"],
                "event_ts": event["ts"],
                "seconds_from_window_start": round((ts - start).total_seconds(), 1),
                "event_service": event["service"],
                "event_pod": debug.get("pod", ""),
                "modality": event["modality"],
                "severity": debug.get("severity", ""),
                "content": event["content"],
                "relevance": "",
                "note": "",
            })  # fmt: skip
            entry = {
                "window_no": window_no,
                "event_no": event_no,
                "window_id": window_id,
                "event_id": event_id,
                "label_is_fault": window["label_is_fault"],
                "label_fault_type": window["label_fault_type"],
                "label_root_cause": window["label_root_cause"],
            }
            for run_name in events:
                entry[f"rank_{run_name}"] = ranks[event_id].get(run_name, "")
            key.append(entry)
    return grade, key


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:  # BOM: Excel reads the Vietnamese-free CSV as UTF-8
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", required=True, help="name=run_id,... (the first run supplies the window rows)")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True, help="path prefix, e.g. eval/manual/context_precision_test_v1")
    args = parser.parse_args()
    prefix = args.out if args.out.is_absolute() else REPO / args.out
    grade_path, key_path = prefix.with_name(prefix.name + ".csv"), prefix.with_name(prefix.name + ".key.csv")
    for path in (grade_path, key_path):
        if path.exists():
            raise SystemExit(f"{path} already exists: samples are never overwritten")
    runs = dict(item.split("=", 1) for item in args.runs.split(","))
    with (RESULTS / next(iter(runs.values())) / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grade, key = build(rows, {name: load_events(run_id) for name, run_id in runs.items()}, args.n, args.seed)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    _write(grade_path, grade)
    _write(key_path, key)
    windows = len({g["window_no"] for g in grade})
    print(f"wrote {grade_path} ({windows} windows, {len(grade)} events to grade) and {key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
