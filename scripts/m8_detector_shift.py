"""Descriptive comparison of the detector across splits (M8, QD-035 follow-up). No LLM call.

    py scripts/m8_detector_shift.py --runs dev=<run>,val=<run>,test=<run> --out m8_detector_shift_test_v1

Reads `per_window.csv` of one detector (or full) run per split -- same frozen detector config --
and reports, per split: windows, candidates, anomaly-score quantiles, candidate rate by
telemetry, by label (fault / normal), by service and by day. Nothing is tuned here: the
threshold and the detector are those of the registered configs. Writes `shift.json` and
`tables.md` to eval/results/<out>/ (must not exist).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.runner import RESULTS, _git_commit  # noqa: E402

QUANTILES = (10, 25, 50, 75, 90, 95, 99)


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


def _rate(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    rows = list(rows)
    candidates = sum(_flag(r["is_candidate"]) for r in rows)
    return {"windows": len(rows), "candidates": candidates, "rate": candidates / len(rows) if rows else None}


def _by(rows: list[dict[str, str]], key: Callable[[dict[str, str]], str]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    return {k: _rate(v) for k, v in sorted(groups.items())}


def describe(rows: list[dict[str, str]], threshold: float) -> dict[str, Any]:
    scores = np.array([float(r["anomaly_score"]) for r in rows if r["anomaly_score"] != ""])
    return {
        **_rate(rows),
        "scored_windows": int(scores.size),
        "score_quantiles": {f"p{q}": float(np.percentile(scores, q)) for q in QUANTILES},
        "score_mean": float(scores.mean()),
        "share_score_ge_threshold": float((scores >= threshold).mean()),
        "by_telemetry": _by(rows, lambda r: "telemetry" if _flag(r["has_telemetry"]) else "no_telemetry"),
        "by_label": _by(rows, lambda r: "fault" if _flag(r["label_is_fault"]) else "normal"),
        "by_label_telemetry": _by(
            rows,
            lambda r: ("fault" if _flag(r["label_is_fault"]) else "normal")
            + ("|telemetry" if _flag(r["has_telemetry"]) else "|no_telemetry"),
        ),
        "by_service": _by(rows, lambda r: r["service"]),
        "by_day": _by(rows, lambda r: r["window_ts"][:10]),
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def tables(report: dict[str, Any]) -> str:
    splits = list(report["splits"])
    out = ["## Bảng S1. Detector theo split", "", "| | " + " | ".join(f"`{s}`" for s in splits) + " |",
           "|---|" + "---:|" * len(splits)]
    block = report["splits"]

    def line(name: str, cell: Callable[[dict[str, Any]], str]) -> None:
        out.append(f"| {name} | " + " | ".join(cell(block[s]) for s in splits) + " |")

    line("Cửa sổ", lambda b: f"{b['windows']:,}")
    line("Candidate", lambda b: f"{b['candidates']:,}")
    line("Tỉ lệ candidate", lambda b: _pct(b["rate"]))
    line(f"Tỉ lệ điểm ≥ {report['threshold']}", lambda b: _pct(b["share_score_ge_threshold"]))
    for q in QUANTILES:
        line(f"Điểm p{q}", lambda b, q=q: f"{b['score_quantiles'][f'p{q}']:.4f}")
    for group, names in (
        ("by_telemetry", ("telemetry", "no_telemetry")),
        ("by_label", ("fault", "normal")),
        ("by_label_telemetry", ("fault|telemetry", "fault|no_telemetry", "normal|telemetry", "normal|no_telemetry")),
    ):
        for name in names:
            line(
                f"Candidate / cửa sổ — {name}",
                lambda b, g=group, n=name: (
                    f"{b[g][n]['candidates']:,} / {b[g][n]['windows']:,} ({_pct(b[g][n]['rate'])})" if n in b[g] else "—"
                ),
            )

    services = sorted({s for name in splits for s in block[name]["by_service"]})
    out += ["", "## Bảng S2. Tỉ lệ candidate theo service", "",
            "| Service | " + " | ".join(f"`{s}`" for s in splits) + " |", "|---|" + "---:|" * len(splits)]
    for service in services:
        cells = []
        for name in splits:
            entry = block[name]["by_service"].get(service)
            cells.append("—" if entry is None else f"{_pct(entry['rate'])} ({entry['candidates']:,} / {entry['windows']:,})")
        out.append(f"| {service} | " + " | ".join(cells) + " |")

    out += ["", "## Bảng S3. Tỉ lệ candidate theo ngày", "", "| Split | Ngày | Cửa sổ | Candidate | Tỉ lệ |", "|---|---|---:|---:|---:|"]
    for name in splits:
        for day, entry in block[name]["by_day"].items():
            out.append(f"| `{name}` | {day} | {entry['windows']:,} | {entry['candidates']:,} | {_pct(entry['rate'])} |")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", required=True, help="split=run_id,... (order = column order)")
    parser.add_argument("--threshold", type=float, default=0.85, help="the registered detector threshold (reporting only)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console (cp1252) cannot print the tables
    out_dir = RESULTS / args.out
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten")
    runs = dict(item.split("=", 1) for item in args.runs.split(","))
    report: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "runs": runs,
        "threshold": args.threshold,
        "git_commit": _git_commit(),
        "splits": {},
    }
    for split, run_id in runs.items():
        with (RESULTS / run_id / "per_window.csv").open(encoding="utf-8", newline="") as handle:
            report["splits"][split] = describe(list(csv.DictReader(handle)), args.threshold)
    out_dir.mkdir(parents=True)
    (out_dir / "shift.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text = tables(report)
    (out_dir / "tables.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
