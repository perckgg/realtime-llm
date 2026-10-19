"""Week 1 split generator — dev / val / test, stratified, seed 42.

Implements docs/Final_Thesis_Phase2/02-data-and-experiment-protocol.md §2:
dev 20% / val 30% / test 50%, stratified by fault type, written to
data/splits/{dev,val,test}.json and committed to git. Once committed the files
must not be regenerated; if they ever are, the reason belongs in the commit
message and in docs/experiment-log.md.

    python scripts/make_splits.py              # reads data/window_index.csv
    python scripts/make_splits.py --check      # verify the committed files still match

Two rules go beyond the protocol document, both to stop the splits leaking:

Group by injection
    All 7 windows produced by one fault injection describe the same event. Split
    them individually and a model tuned on val is scored on test windows it has
    effectively already seen. The unit of assignment is therefore the injection,
    not the window.

Buffer around injections
    A normal window one minute after a fault window is nearly the same system
    state. Normal windows on the same pod within BUFFER_SECONDS of any injection
    are dropped from every split rather than handed to a different split than the
    fault they sit next to. They stay in data/window_index.csv, marked by their
    absence from the three split files.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.schemas.nezha import (
    DEFAULT_TIME_SOURCE,
    LABEL_AFTER_SECONDS,
    LABEL_BEFORE_SECONDS,
    build_windows,
    dataset_root,
    load_injections,
    read_window_index,
)

SEED = 42
SPLIT_RATIOS = {"dev": 0.20, "val": 0.30, "test": 0.50}
# Normal windows this close to an injection on the same pod are excluded from
# every split. 600 s comfortably covers the [-60 s, +360 s] label interval plus
# the tail of the fault still visible in the metrics.
BUFFER_SECONDS = 600

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = REPO_ROOT / "data" / "window_index.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "splits"


def assign_groups(keys: list[str], strata: dict[str, str]) -> dict[str, str]:
    """Assign each group key to a split, keeping the ratio inside every stratum.

    Deterministic given SEED: sort the keys, shuffle each stratum with a fresh
    Random(SEED), then cut at the ratio boundaries. Largest-remainder rounding
    keeps small strata from losing their last member to floor().
    """
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for key in sorted(keys):
        by_stratum[strata[key]].append(key)

    assignment: dict[str, str] = {}
    for stratum in sorted(by_stratum):
        members = by_stratum[stratum]
        random.Random(SEED).shuffle(members)
        for split, count in _quota(len(members)).items():
            for key in members[:count]:
                assignment[key] = split
            members = members[count:]
    return assignment


def _quota(total: int) -> dict[str, int]:
    """Split `total` items by SPLIT_RATIOS using largest-remainder rounding."""
    exact = {split: total * ratio for split, ratio in SPLIT_RATIOS.items()}
    counts = {split: int(value) for split, value in exact.items()}
    remaining = total - sum(counts.values())
    order = sorted(exact, key=lambda split: (-(exact[split] - counts[split]), split))
    for split in order[:remaining]:
        counts[split] += 1
    return counts


def build_split_assignment(windows, injections) -> tuple[dict[str, str], list, dict]:
    """Return (window_id -> split), the excluded buffer windows, and the stats."""
    fault_windows = [w for w in windows if w.is_fault]
    normal_windows = [w for w in windows if not w.is_fault]

    # Fault windows: assign per injection, stratified by fault type.
    fault_type_of = {i.injection_id: i.fault_type for i in injections}
    used_injections = sorted({w.injection_id for w in fault_windows})
    injection_split = assign_groups(used_injections, fault_type_of)

    # Normal windows: drop the buffer zone, then assign per pod-day so that a
    # whole pod-day of background traffic lands in one split.
    buffer = timedelta(seconds=BUFFER_SECONDS)
    by_pod: dict[str, list[datetime]] = defaultdict(list)
    for injection in injections:
        by_pod[injection.inject_pod].append(injection.inject_ts)

    kept_normal: list = []
    excluded: list = []
    for window in normal_windows:
        near = any(abs((window.start_ts - ts).total_seconds()) <= buffer.total_seconds()
                   for ts in by_pod.get(window.pod, ()))
        (excluded if near else kept_normal).append(window)

    pod_days = sorted({f"{w.day}|{w.pod}" for w in kept_normal})
    pod_day_split = assign_groups(pod_days, {key: "normal" for key in pod_days})

    assignment: dict[str, str] = {}
    for window in fault_windows:
        assignment[window.window_id] = injection_split[window.injection_id]
    for window in kept_normal:
        assignment[window.window_id] = pod_day_split[f"{window.day}|{window.pod}"]

    stats = {
        "injections_assigned": len(used_injections),
        "pod_days_assigned": len(pod_days),
        "normal_excluded_buffer": len(excluded),
    }
    return assignment, excluded, stats


def render_split_file(split: str, windows, assignment, stats) -> dict:
    members = [w for w in windows if assignment.get(w.window_id) == split]
    members.sort(key=lambda w: (w.start_ts, w.window_id))
    by_type = Counter(w.fault_type for w in members)
    return {
        "split": split,
        "seed": SEED,
        "generated_by": "scripts/make_splits.py",
        "protocol": "docs/Final_Thesis_Phase2/02-data-and-experiment-protocol.md §2",
        "time_source": DEFAULT_TIME_SOURCE,
        "label_rule": {
            "same_pod": True,
            "before_seconds": LABEL_BEFORE_SECONDS,
            "after_seconds": LABEL_AFTER_SECONDS,
        },
        "grouping": {
            "fault_windows": "by injection_id",
            "normal_windows": "by day|pod",
            "buffer_seconds": BUFFER_SECONDS,
        },
        "target_ratio": SPLIT_RATIOS[split],
        "n_windows": len(members),
        "n_fault_windows": sum(1 for w in members if w.is_fault),
        "n_injections": len({w.injection_id for w in members if w.is_fault}),
        "counts_by_fault_type": dict(sorted(by_type.items())),
        "corpus_stats": stats,
        "window_ids": [w.window_id for w in members],
    }


def load_windows(args):
    """Prefer the committed index; rebuild from the dataset when it is missing."""
    if args.index.exists():
        return read_window_index(args.index), load_injections(dataset_root())
    print(f"{args.index} not found — rebuilding from the dataset", file=sys.stderr)
    root = dataset_root()
    windows, _ = build_windows(root)
    return windows, load_injections(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true",
                        help="regenerate in memory and diff against the committed files")
    args = parser.parse_args()

    windows, injections = load_windows(args)
    assignment, _excluded, stats = build_split_assignment(windows, injections)

    payloads = {split: render_split_file(split, windows, assignment, stats)
                for split in SPLIT_RATIOS}

    if args.check:
        return _check(payloads, args.out)

    args.out.mkdir(parents=True, exist_ok=True)
    for split, payload in payloads.items():
        path = args.out / f"{split}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"wrote {path}  n={payload['n_windows']:,} "
              f"fault={payload['n_fault_windows']} "
              f"injections={payload['n_injections']}", file=sys.stderr)

    total = sum(p["n_windows"] for p in payloads.values())
    print(f"assigned {total:,} / {len(windows):,} windows; "
          f"{stats['normal_excluded_buffer']:,} normal windows held out as buffer",
          file=sys.stderr)
    _write_manifest(args.out, payloads, windows, stats)
    return 0


def _write_manifest(out: Path, payloads, windows, stats) -> None:
    """One small file summarising the three splits, easy to cite in the thesis."""
    manifest = {
        "seed": SEED,
        "generated_by": "scripts/make_splits.py",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "time_source": DEFAULT_TIME_SOURCE,
        "buffer_seconds": BUFFER_SECONDS,
        "total_windows_in_corpus": len(windows),
        "total_windows_assigned": sum(p["n_windows"] for p in payloads.values()),
        "normal_excluded_buffer": stats["normal_excluded_buffer"],
        "splits": {
            split: {
                "n_windows": payload["n_windows"],
                "n_fault_windows": payload["n_fault_windows"],
                "n_injections": payload["n_injections"],
                "counts_by_fault_type": payload["counts_by_fault_type"],
            }
            for split, payload in payloads.items()
        },
    }
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"wrote {path}", file=sys.stderr)


def _check(payloads, out: Path) -> int:
    """Exit non-zero if the committed splits differ from a fresh generation."""
    problems = []
    for split, payload in payloads.items():
        path = out / f"{split}.json"
        if not path.exists():
            problems.append(f"{path} is missing")
            continue
        committed = json.loads(path.read_text(encoding="utf-8"))
        if committed.get("window_ids") != payload["window_ids"]:
            problems.append(
                f"{path}: {len(committed.get('window_ids', []))} committed window ids "
                f"vs {len(payload['window_ids'])} regenerated"
            )
    if problems:
        for problem in problems:
            print(f"MISMATCH {problem}", file=sys.stderr)
        return 1
    print("splits match the committed files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
