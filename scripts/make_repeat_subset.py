"""Fixed subset of judged candidate windows for the judge-variance (`repeat`) runs (M8, QD-034).

    py scripts/make_repeat_subset.py --run h0_test_bm25_v1 --n 200 --seed 42 --out eval/samples/m8_repeat_test_v1.csv

Draws `n` windows uniformly, without replacement, from the candidates of `run` that have
telemetry (the main subset, QD-016/017). Uses `is_candidate` and `has_telemetry` only -- no
label, no verdict -- so the subset does not depend on what any method answered. The output is a
`window_set` file for the runner (columns `gd2_window_id`, `role`), in replay order; the
detector still replays the full history, only the judged windows are restricted.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.runner import RESULTS  # noqa: E402


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


def draw(rows: list[dict[str, str]], n: int, seed: int) -> list[str]:
    """`n` candidate windows with telemetry, in the order of `rows`."""
    pool = [r["window_id"] for r in rows if _flag(r["is_candidate"]) and _flag(r["has_telemetry"])]
    if len(pool) < n:
        raise ValueError(f"only {len(pool)} candidate windows with telemetry, asked for {n}")
    chosen = set(random.Random(seed).sample(pool, n))
    return [w for w in pool if w in chosen]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, help="a full run of the split (its per_window.csv)")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else REPO / args.out
    if out.exists():
        raise SystemExit(f"{out} already exists: samples are never overwritten")
    with (RESULTS / args.run / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = draw(rows, args.n, args.seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["gd2_window_id", "role"])
        writer.writerows([w, "evaluated"] for w in ids)
    print(f"wrote {out} ({len(ids)} windows from {args.run}, seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
