"""Assign the V35 context-precision labels with a fixed, auditable rule (no LLM call).

    py scripts/m8_context_precision_rule_label.py \
        --graded eval/manual/context_precision_test_v1.csv \
        --out eval/manual/context_precision_test_v1.ai_scores.csv

Why a rule instead of free-form judging (decision 2026-11-22, QD-051): the blind grading file
carries 525 events and the rubric in `eval/manual/README-context-precision.md` names exactly two
positive signals ("log ERROR/WARN/exception/5xx related to the call path" and "span whose
duration spiked on the alerting service or a directly related one, near the alert time"). Turning
those into a threshold rule keeps the labels reproducible and lets the thesis report a sensitivity
analysis, which a hand-waved per-row verdict cannot.

Rule (primary column `relevance`):

- `1`  severity is WARN/ERROR/FATAL/CRITICAL, or `duration_ms >= --slow-ms`, and
       `abs(seconds_from_window_start) <= --window-s`;
- `?`  `--unsure-ms <= duration_ms < --slow-ms` and `abs(seconds) <= --unsure-window-s`;
- `0`  everything else (fast INFO spans, and any event far from the alert window, because a slow
       span several minutes away does not explain this window).

Error signals are also read from `content` (patch 2026-11-22), because the Nezha `severity`
column is `INFO` for almost every event: a log line whose own level token is ERROR/FATAL/CRITICAL
(e.g. `{"log":"... ERROR f.s.FoodServiceImpl ... Failed!"}`) and a `BasicErrorController.error`
trace span (Spring's error handler, ~1 ms, so the duration rule never fires) count as `1` inside
`--window-s`, exactly like a WARN/ERROR severity. The same check feeds the two sensitivity columns.

`--slow-ms` defaults to 200 ms: in this sample 88 % of the retrieved spans are under 100 ms and the
90th percentile is 99.9 ms, so 200 ms is an unambiguous spike rather than a normal frontend
request. Two binary sensitivity columns are written next to it (`relevance_loose` at 100 ms,
`relevance_strict` at 500 ms) so the aggregation script can show how the number moves.

The file is never overwritten unless `--force` is passed, and the blind file
(`context_precision_test_v1.csv`) is only read, never modified.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DURATION_RE = re.compile(r"duration_ms=([0-9.]+)")
POSITIVE_SEVERITY = frozenset({"WARN", "ERROR", "FATAL", "CRITICAL"})
# Level token inside a raw log line, e.g. `20:46:10.826 ERROR f.s.FoodServiceImpl#302 ...`.
ERROR_LOG_RE = re.compile(r"\b(ERROR|FATAL|CRITICAL)\b")
# Spring Boot's fallback error handler: the span exists only when a request failed.
ERROR_SPAN_RE = re.compile(r"^Trace span BasicErrorController\.error\b")
LABEL_FIELDS = ["window_no", "event_no", "relevance", "relevance_loose", "relevance_strict", "rule", "note"]


@dataclass(frozen=True)
class Rule:
    """Thresholds of the labeling rule; every value comes from the command line."""

    slow_ms: float = 200.0
    unsure_ms: float = 100.0
    window_s: float = 180.0
    unsure_window_s: float = 120.0


def parse_duration(content: str) -> float | None:
    """`duration_ms=` value of a trace event, or None for events without one (logs)."""
    match = DURATION_RE.search(content)
    return float(match.group(1)) if match else None


def content_error_kind(content: str, duration_ms: float | None) -> str | None:
    """`error_log` / `error_span` when `content` itself carries an error signal, else None."""
    if ERROR_SPAN_RE.match(content):
        return "error_span"
    if duration_ms is None and ERROR_LOG_RE.search(content):
        return "error_log"
    return None


def binary_label(
    seconds: float,
    severity: str,
    duration_ms: float | None,
    slow_ms: float,
    window_s: float,
    content: str = "",
) -> str:
    """`1` when the event is an error or a spike inside the window, `0` otherwise."""
    near = abs(seconds) <= window_s
    if severity.strip().upper() in POSITIVE_SEVERITY or content_error_kind(content, duration_ms):
        return "1" if near else "0"
    if duration_ms is None:
        return "0"
    return "1" if (duration_ms >= slow_ms and near) else "0"


def label_event(
    seconds: float, severity: str, duration_ms: float | None, rule: Rule, content: str = ""
) -> tuple[str, str]:
    """Primary label plus the rule branch that produced it."""
    near = abs(seconds) <= rule.window_s
    if severity.strip().upper() in POSITIVE_SEVERITY:
        return ("1", "warn_in_window") if near else ("0", "warn_out_of_window")
    kind = content_error_kind(content, duration_ms)
    if kind is not None:
        return ("1", f"{kind}_in_window") if near else ("0", f"{kind}_out_of_window")
    if duration_ms is None:
        return "0", "no_duration"
    if duration_ms >= rule.slow_ms:
        return ("1", "slow_in_window") if near else ("0", "slow_out_of_window")
    if duration_ms >= rule.unsure_ms and abs(seconds) <= rule.unsure_window_s:
        return "?", "mid_band_in_window"
    if duration_ms >= rule.unsure_ms:
        return "0", "mid_band_out_of_window"
    return "0", "fast_span"


def build_rows(graded: list[dict[str, str]], rule: Rule) -> list[dict[str, str]]:
    """One labeled row per graded event, in the input order."""
    out: list[dict[str, str]] = []
    for row in graded:
        seconds = float(row["seconds_from_window_start"])
        duration = parse_duration(row["content"])
        severity = row.get("severity", "")
        content = row.get("content", "")
        label, branch = label_event(seconds, severity, duration, rule, content)
        measured = "log" if duration is None else f"dur={duration:.1f}ms"
        out.append({
            "window_no": row["window_no"],
            "event_no": row["event_no"],
            "relevance": label,
            "relevance_loose": binary_label(seconds, severity, duration, 100.0, rule.window_s, content),
            "relevance_strict": binary_label(seconds, severity, duration, 500.0, rule.window_s, content),
            "rule": branch,
            "note": f"{measured};t={seconds:.1f}s;{severity}",
        })  # fmt: skip
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--graded", type=Path, default=Path("eval/manual/context_precision_test_v1.csv"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--slow-ms", type=float, default=200.0)
    parser.add_argument("--unsure-ms", type=float, default=100.0)
    parser.add_argument("--window-s", type=float, default=180.0)
    parser.add_argument("--unsure-window-s", type=float, default=120.0)
    parser.add_argument("--force", action="store_true", help="overwrite the label file if it exists")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    graded_path = args.graded if args.graded.is_absolute() else REPO / args.graded
    out_path = args.out if args.out.is_absolute() else REPO / args.out
    if out_path.exists() and not args.force:
        raise SystemExit(f"{out_path} already exists: labels are never overwritten without --force")
    with graded_path.open(encoding="utf-8-sig", newline="") as handle:
        graded = list(csv.DictReader(handle))
    if not graded:
        raise SystemExit(f"{graded_path} is empty")
    rule = Rule(
        slow_ms=args.slow_ms,
        unsure_ms=args.unsure_ms,
        window_s=args.window_s,
        unsure_window_s=args.unsure_window_s,
    )
    rows = build_rows(graded, rule)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts = {label: sum(1 for row in rows if row["relevance"] == label) for label in ("1", "0", "?")}
    print(
        f"wrote {out_path} ({len(rows)} events: relevant={counts['1']}, "
        f"irrelevant={counts['0']}, unsure={counts['?']})"
    )
    print(
        f"rule: slow_ms={rule.slow_ms:g} unsure_ms={rule.unsure_ms:g} "
        f"window_s={rule.window_s:g} unsure_window_s={rule.unsure_window_s:g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
