"""Aggregate the V35 context-precision grading (02 SS4.2, M8 task 9). No LLM call.

    py scripts/m8_context_precision_score.py \
        --graded eval/manual/context_precision_test_v1.csv \
        --labels eval/manual/context_precision_test_v1.ai_scores.csv \
        --key eval/manual/context_precision_test_v1.key.csv \
        --out eval/results/m8_context_precision_v1

The graded file is blind (no method, rank or label). The labels file carries one verdict per
event (`1` relevant, `0` irrelevant, `?` unsure) plus two threshold-sensitivity columns written by
`m8_context_precision_rule_label.py`. The key file is opened only here, after the labels are
frozen, to attach each method's rank and compute:

- **micro precision** -- relevant retrieved events / retrieved events, pooled over the sample
  (the `% context event thực sự liên quan` of `02` SS4.2);
- **macro precision** -- mean of the per-window precision, so a window with fewer retrieved
  events does not count less;
- **delta** (C1 minus BM25) with a paired bootstrap CI over windows (`--n-boot`, `--seed`).

`?` counts as irrelevant in the primary number (conservative); alternatives are reported (drop
them from the denominator, count them as relevant) together with the 100 ms / 500 ms label
variants. Directory `--out` is never overwritten: a rerun with other inputs needs a new `run_id`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

METHODS = ("bm25", "c1")
PRIMARY_LABELS = frozenset({"0", "1", "?"})
BINARY_LABELS = frozenset({"0", "1"})


@dataclass(frozen=True)
class Event:
    """One graded event: its labels per column and the rank each method gave it (None = absent)."""

    window_no: int
    event_no: int
    labels: dict[str, str]
    ranks: dict[str, int | None]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _index(rows: list[dict[str, str]], source: str) -> dict[tuple[int, int], dict[str, str]]:
    out: dict[tuple[int, int], dict[str, str]] = {}
    for row in rows:
        key = (int(row["window_no"]), int(row["event_no"]))
        if key in out:
            raise ValueError(f"{source}: duplicate row for window {key[0]} event {key[1]}")
        out[key] = row
    return out


def _check_labels(key: tuple[int, int], labels: dict[str, str]) -> None:
    if labels["relevance"] not in PRIMARY_LABELS:
        raise ValueError(
            f"window {key[0]} event {key[1]}: relevance {labels['relevance']!r} "
            f"is not one of {sorted(PRIMARY_LABELS)}"
        )
    for column in ("relevance_loose", "relevance_strict"):
        value = labels.get(column)
        if value is not None and value not in BINARY_LABELS:
            raise ValueError(f"window {key[0]} event {key[1]}: {column} {value!r} is not 0/1")


def load_events(graded_path: Path, labels_path: Path, key_path: Path, top_k: int) -> list[Event]:
    """Join the blind grading file, the label file and the key, validating the three covers."""
    graded = _index(_read_csv(graded_path), "graded")
    labels = _index(_read_csv(labels_path), "labels")
    key = _index(_read_csv(key_path), "key")
    if not set(graded) == set(labels) == set(key):
        missing_labels = set(graded) - set(labels)
        extra_labels = set(labels) - set(graded)
        missing_key = set(graded) - set(key)
        raise ValueError(
            f"row sets differ: {len(missing_labels)} unlabeled, {len(extra_labels)} unknown labels, "
            f"{len(missing_key)} rows without a key entry"
        )
    events: list[Event] = []
    for row_key in sorted(graded):
        row = labels[row_key]
        columns = {
            "relevance": row.get("relevance", "").strip(),
            "relevance_loose": row.get("relevance_loose", "").strip(),
            "relevance_strict": row.get("relevance_strict", "").strip(),
        }
        if not columns["relevance"]:
            raise ValueError(f"window {row_key[0]} event {row_key[1]}: relevance is empty")
        columns = {name: value for name, value in columns.items() if value}
        _check_labels(row_key, columns)
        ranks: dict[str, int | None] = {}
        for method in METHODS:
            raw = key[row_key].get(f"rank_{method}", "").strip()
            if raw == "":
                ranks[method] = None
                continue
            rank = int(raw)
            if not 1 <= rank <= top_k:
                raise ValueError(
                    f"window {row_key[0]} event {row_key[1]}: rank_{method}={rank} outside 1..{top_k}"
                )
            ranks[method] = rank
        events.append(Event(row_key[0], row_key[1], columns, ranks))
    return events


def counts(
    events: list[Event], method: str, column: str, unsure_as: str
) -> tuple[int, int, int, int]:
    """(relevant, retrieved, unsure, total) for one method under a given unsure policy.

    `retrieved` follows the policy (an excluded `?` leaves the denominator); `total` is always the
    number of events the method retrieved, which is the denominator of the unsure rate.
    """
    relevant = retrieved = unsure = total = 0
    for event in events:
        if event.ranks[method] is None:
            continue
        total += 1
        label = event.labels.get(column, "0")
        if label == "?":
            unsure += 1
            if unsure_as == "relevant":
                relevant += 1
                retrieved += 1
            elif unsure_as != "exclude":
                retrieved += 1
            continue
        retrieved += 1
        if label == "1":
            relevant += 1
    return relevant, retrieved, unsure, total


def per_window(
    events: list[Event], method: str, column: str, unsure_as: str
) -> dict[int, tuple[int, int]]:
    """window_no -> (relevant, retrieved) for one method."""
    buckets: dict[int, list[Event]] = defaultdict(list)
    for event in events:
        buckets[event.window_no].append(event)
    return {
        window_no: counts(rows, method, column, unsure_as)[:2]
        for window_no, rows in buckets.items()
    }


def micro(pairs: list[tuple[int, int]]) -> float:
    relevant = sum(pair[0] for pair in pairs)
    retrieved = sum(pair[1] for pair in pairs)
    return relevant / retrieved if retrieved else float("nan")


def macro(pairs: list[tuple[int, int]]) -> float:
    values = [relevant / retrieved for relevant, retrieved in pairs if retrieved]
    return statistics.fmean(values) if values else float("nan")


def bootstrap(
    windows: list[int],
    by_method: dict[str, dict[int, tuple[int, int]]],
    n_boot: int,
    seed: int,
    statistic: str,
) -> dict[str, tuple[float, float]]:
    """Percentile 95 % CI per method plus the paired delta (C1 - BM25)."""
    rng = random.Random(seed)
    pool = list(windows)
    aggregate = micro if statistic == "micro" else macro
    samples: dict[str, list[float]] = {key: [] for key in (*METHODS, "delta")}
    for _ in range(n_boot):
        drawn = [pool[rng.randrange(len(pool))] for _ in pool]
        values: dict[str, float] = {}
        for method in METHODS:
            pairs = [by_method[method][window] for window in drawn if window in by_method[method]]
            values[method] = aggregate(pairs)
        samples["delta"].append(values["c1"] - values["bm25"])
        for method in METHODS:
            samples[method].append(values[method])
    out: dict[str, tuple[float, float]] = {}
    for name, values in samples.items():
        finite = sorted(value for value in values if not math.isnan(value))
        if not finite:
            out[name] = (float("nan"), float("nan"))
            continue
        out[name] = (finite[int(0.025 * (len(finite) - 1))], finite[int(0.975 * (len(finite) - 1))])
    return out


def _fmt(value: float) -> str:
    return "n/a" if math.isnan(value) else f"{value:.4f}"


def _display(path: Path) -> str:
    """Path relative to the repo when inside it, absolute otherwise (tests use temp dirs)."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _ci(interval: tuple[float, float]) -> str:
    return f"[{_fmt(interval[0])}; {_fmt(interval[1])}]"


def summarise(
    events: list[Event], column: str, unsure_as: str, n_boot: int, seed: int
) -> dict[str, object]:
    """Counts, micro/macro with CI and the paired delta, for one label column and policy."""
    windows = sorted({event.window_no for event in events})
    by_method = {method: per_window(events, method, column, unsure_as) for method in METHODS}
    micro_ci = bootstrap(windows, by_method, n_boot, seed, "micro")
    macro_ci = bootstrap(windows, by_method, n_boot, seed, "macro")
    block: dict[str, object] = {"label_column": column, "unsure_policy": unsure_as, "methods": {}}
    for method in METHODS:
        pairs = list(by_method[method].values())
        relevant, retrieved, unsure, total = counts(events, method, column, unsure_as)
        block["methods"][method] = {  # type: ignore[index]
            "retrieved": retrieved,
            "relevant": relevant,
            "unsure": unsure,
            "total_retrieved": total,
            "unsure_rate": unsure / total if total else float("nan"),
            "windows_with_context": sum(1 for value in pairs if value[1]),
            "micro": micro(pairs),
            "micro_ci95": micro_ci[method],
            "macro": macro(pairs),
            "macro_ci95": macro_ci[method],
        }
    block["delta"] = {
        "micro": micro(list(by_method["c1"].values())) - micro(list(by_method["bm25"].values())),
        "micro_ci95": micro_ci["delta"],
        "macro": macro(list(by_method["c1"].values())) - macro(list(by_method["bm25"].values())),
        "macro_ci95": macro_ci["delta"],
    }
    block["per_window"] = {
        str(window): {method: by_method[method][window] for method in METHODS} for window in windows
    }
    return block


def tables_markdown(primary: dict[str, object], sensitivity: dict[str, object]) -> str:
    """Human-readable tables for the milestone report and the thesis draft."""
    lines = [
        "# Context precision (V35) — tổng hợp",
        "",
        "Nhãn do quy tắc ngưỡng cố định gán (`scripts/m8_context_precision_rule_label.py`, QĐ-051):",
        "ngưỡng chính 200 ms trong cửa sổ ±180 s, dải `?` 100–200 ms trong ±120 s.",
        "",
        "## Chỉ số chính",
        "",
        "| Phương pháp | Retrieval | Relevant | Unsure | Micro P | CI 95% | Macro P | CI 95% |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    methods = primary["methods"]  # type: ignore[assignment]
    for method in METHODS:
        row = methods[method]  # type: ignore[index]
        lines.append(
            f"| {method} | {row['retrieved']} | {row['relevant']} | {row['unsure']} | "
            f"{_fmt(row['micro'])} | {_ci(row['micro_ci95'])} | {_fmt(row['macro'])} | "
            f"{_ci(row['macro_ci95'])} |"
        )
    delta = primary["delta"]  # type: ignore[assignment]
    delta_line = (
        f"Δ micro (C1 − BM25) = **{delta['micro']:+.4f}** {_ci(delta['micro_ci95'])}; "
        f"Δ macro = **{delta['macro']:+.4f}** {_ci(delta['macro_ci95'])}."
    )
    lines += [
        "",
        delta_line,
        "",
        "## Độ nhạy",
        "",
        "| Kịch bản | Micro BM25 | Micro C1 | Δ micro | CI 95% Δ |",
        "|---|---:|---:|---:|---|",
    ]
    for name, block in sensitivity.items():  # type: ignore[union-attr]
        block_methods = block["methods"]  # type: ignore[index]
        lines.append(
            f"| {name} | {_fmt(block_methods['bm25']['micro'])} | "
            f"{_fmt(block_methods['c1']['micro'])} | {block['delta']['micro']:+.4f} | "  # type: ignore[index]
            f"{_ci(block['delta']['micro_ci95'])} |"  # type: ignore[index]
        )
    lines += [
        "",
        "## Từng cửa sổ",
        "",
        "| # | BM25 (relevant/retrieved) | C1 (relevant/retrieved) |",
        "|---:|---|---|",
    ]
    for window, ranking in primary["per_window"].items():  # type: ignore[union-attr]
        bm25 = ranking["bm25"]
        c1 = ranking["c1"]
        lines.append(f"| {window} | {bm25[0]}/{bm25[1]} | {c1[0]}/{c1[1]} |")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--graded", type=Path, default=Path("eval/manual/context_precision_test_v1.csv"))
    parser.add_argument(
        "--labels", type=Path, default=Path("eval/manual/context_precision_test_v1.ai_scores.csv")
    )
    parser.add_argument("--key", type=Path, default=Path("eval/manual/context_precision_test_v1.key.csv"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = {
        "graded": args.graded if args.graded.is_absolute() else REPO / args.graded,
        "labels": args.labels if args.labels.is_absolute() else REPO / args.labels,
        "key": args.key if args.key.is_absolute() else REPO / args.key,
    }
    out = args.out if args.out.is_absolute() else REPO / args.out
    if out.exists():
        raise SystemExit(
            f"{out} already exists: rerun with a new --out (run_id), results are never overwritten"
        )
    events = load_events(paths["graded"], paths["labels"], paths["key"], args.top_k)
    primary = summarise(events, "relevance", "irrelevant", args.n_boot, args.seed)
    sensitivity = {
        "unsure_as_relevant": summarise(events, "relevance", "relevant", args.n_boot, args.seed),
        "unsure_excluded": summarise(events, "relevance", "exclude", args.n_boot, args.seed),
        "threshold_100ms": summarise(events, "relevance_loose", "irrelevant", args.n_boot, args.seed),
        "threshold_500ms": summarise(events, "relevance_strict", "irrelevant", args.n_boot, args.seed),
    }
    report: dict[str, object] = {
        "run_id": out.name,
        "inputs": {name: _display(path) for name, path in paths.items()},
        "config": {
            "top_k": args.top_k,
            "n_boot": args.n_boot,
            "seed": args.seed,
            "labels": "rule m8_context_precision_rule_label.py, QD-051",
        },
        "n_events": len(events),
        "n_windows": len({event.window_no for event in events}),
        **primary,
        "sensitivity": sensitivity,
    }
    out.mkdir(parents=True, exist_ok=False)
    (out / "context_precision.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "tables.md").write_text(tables_markdown(primary, sensitivity), encoding="utf-8")
    methods = primary["methods"]  # type: ignore[assignment]
    for method in METHODS:
        row = methods[method]  # type: ignore[index]
        print(
            f"{method}: retrieved={row['retrieved']} relevant={row['relevant']} "
            f"unsure={row['unsure']} micro={_fmt(row['micro'])} {_ci(row['micro_ci95'])} "
            f"macro={_fmt(row['macro'])} {_ci(row['macro_ci95'])}"
        )
    delta = primary["delta"]  # type: ignore[assignment]
    print(f"delta micro={delta['micro']:+.4f} {_ci(delta['micro_ci95'])}")
    print(f"wrote {out / 'context_precision.json'} and {out / 'tables.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
