from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_PHASE2 = ROOT / "outputs" / "phase2"

WINDOW_INDEX = OUT_PHASE2 / "window_index.csv"
BASELINE_REFERENCE = OUT_PHASE2 / "baseline_reference.csv"
FREEZE_JSON = OUT_PHASE2 / "input_freeze.json"
FREEZE_MD = OUT_PHASE2 / "input_freeze.md"

DATASET_NAME = "IntelligentDDS/Nezha"
EXPECTED_SPLITS = {
    "debug_50": 50,
    "paper_300": 300,
    "paper_500": 500,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_strings(values: list[str]) -> str:
    h = hashlib.sha256()
    for value in values:
        h.update(value.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def split_for_baseline(audit_rows: int) -> str | None:
    if audit_rows == EXPECTED_SPLITS["paper_500"]:
        return "paper_500"
    if audit_rows == EXPECTED_SPLITS["paper_300"]:
        return "paper_300"
    return None


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def summarize_window_sets(rows: list[dict[str, str]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split in EXPECTED_SPLITS:
        split_rows = [row for row in rows if row.get("split") == split]
        window_ids = [row.get("window_id", "") for row in split_rows]
        unique_window_ids = unique_ordered(window_ids)
        duplicate_count = len(window_ids) - len(unique_window_ids)
        datasets = sorted({row.get("dataset", "") for row in split_rows})
        summary[split] = {
            "rows": len(split_rows),
            "expected_rows": EXPECTED_SPLITS[split],
            "unique_windows": len(unique_window_ids),
            "duplicate_windows": duplicate_count,
            "dataset_values": datasets,
            "fault_type_counts": dict(
                sorted(Counter(row.get("fault_type") or "none" for row in split_rows).items())
            ),
            "ground_truth_counts": dict(
                sorted(Counter(row.get("ground_truth") or "unknown" for row in split_rows).items())
            ),
            "window_id_sha256": sha256_strings(unique_window_ids),
        }
    return summary


def summarize_baselines(
    baseline_rows: list[dict[str, str]], window_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    windows_by_split = {
        split: set(row.get("window_id", "") for row in window_rows if row.get("split") == split)
        for split in EXPECTED_SPLITS
    }
    out: list[dict[str, Any]] = []
    for row in baseline_rows:
        audit_rel = row.get("audit_path", "")
        summary_csv_rel = row.get("summary_csv", "")
        summary_md_rel = row.get("summary_md", "")
        audit_path = ROOT / audit_rel
        summary_csv_path = ROOT / summary_csv_rel
        summary_md_path = ROOT / summary_md_rel

        audit_records = read_jsonl(audit_path)
        audit_window_ids = unique_ordered(
            [str(record.get("window_id") or "") for record in audit_records]
        )
        audit_window_set = set(audit_window_ids)
        expected_split = split_for_baseline(len(audit_records))
        expected_window_set = windows_by_split.get(expected_split or "", set())
        missing_from_baseline = sorted(expected_window_set - audit_window_set)
        extra_in_baseline = sorted(audit_window_set - expected_window_set)

        out.append(
            {
                "baseline": row.get("baseline", ""),
                "expected_split": expected_split,
                "audit_path": audit_rel,
                "summary_csv": summary_csv_rel,
                "summary_md": summary_md_rel,
                "audit_rows": len(audit_records),
                "unique_windows": len(audit_window_ids),
                "exists_audit": audit_path.exists(),
                "exists_summary_csv": summary_csv_path.exists(),
                "exists_summary_md": summary_md_path.exists(),
                "audit_sha256": sha256_file(audit_path) if audit_path.exists() else None,
                "summary_csv_sha256": sha256_file(summary_csv_path)
                if summary_csv_path.exists()
                else None,
                "summary_md_sha256": sha256_file(summary_md_path)
                if summary_md_path.exists()
                else None,
                "window_id_sha256": sha256_strings(audit_window_ids),
                "matches_expected_split": bool(
                    expected_split
                    and not missing_from_baseline
                    and not extra_in_baseline
                    and len(audit_window_ids) == len(expected_window_set)
                ),
                "missing_from_baseline_count": len(missing_from_baseline),
                "extra_in_baseline_count": len(extra_in_baseline),
                "missing_from_baseline_sample": missing_from_baseline[:5],
                "extra_in_baseline_sample": extra_in_baseline[:5],
            }
        )
    return out


def validate_freeze(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for path_key in ["window_index", "baseline_reference"]:
        if not data["source_files"][path_key]["exists"]:
            issues.append(f"Missing required source file: {data['source_files'][path_key]['path']}")

    for split, summary in data["window_sets"].items():
        if summary["rows"] != summary["expected_rows"]:
            issues.append(
                f"{split} has {summary['rows']} rows, expected {summary['expected_rows']}"
            )
        if summary["unique_windows"] != summary["expected_rows"]:
            issues.append(
                f"{split} has {summary['unique_windows']} unique windows, expected {summary['expected_rows']}"
            )
        if summary["duplicate_windows"]:
            issues.append(f"{split} has {summary['duplicate_windows']} duplicate window IDs")
        if summary["dataset_values"] != [DATASET_NAME]:
            issues.append(f"{split} dataset values are {summary['dataset_values']}")

    for baseline in data["baseline_alignment"]:
        if not baseline["exists_audit"]:
            issues.append(f"{baseline['baseline']} is missing audit file")
        if not baseline["exists_summary_csv"]:
            issues.append(f"{baseline['baseline']} is missing summary CSV")
        if not baseline["exists_summary_md"]:
            issues.append(f"{baseline['baseline']} is missing summary Markdown")
        if not baseline["expected_split"]:
            issues.append(
                f"{baseline['baseline']} has unsupported audit row count {baseline['audit_rows']}"
            )
        if not baseline["matches_expected_split"]:
            issues.append(
                f"{baseline['baseline']} does not match {baseline['expected_split']} window set "
                f"(missing={baseline['missing_from_baseline_count']}, "
                f"extra={baseline['extra_in_baseline_count']})"
            )
    return issues


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Phase 2 Input Freeze",
        "",
        f"Generated at UTC: `{data['generated_at_utc']}`",
        "",
        "## Source files",
        "",
        "| File | SHA-256 |",
        "|---|---|",
    ]
    for source in data["source_files"].values():
        lines.append(f"| `{source['path']}` | `{source['sha256']}` |")

    lines.extend(
        [
            "",
            "## Frozen window sets",
            "",
            "| Split | Rows | Unique windows | Ground truth | Fault types | Window ID SHA-256 |",
            "|---|---:|---:|---|---|---|",
        ]
    )
    for split, summary in data["window_sets"].items():
        gt = ", ".join(f"{k}={v}" for k, v in summary["ground_truth_counts"].items())
        faults = ", ".join(f"{k}={v}" for k, v in summary["fault_type_counts"].items())
        lines.append(
            f"| `{split}` | {summary['rows']} | {summary['unique_windows']} | "
            f"{gt} | {faults} | `{summary['window_id_sha256']}` |"
        )

    lines.extend(
        [
            "",
            "## Baseline alignment",
            "",
            "| Baseline | Expected split | Audit rows | Unique windows | Matches split |",
            "|---|---|---:|---:|---|",
        ]
    )
    for baseline in data["baseline_alignment"]:
        lines.append(
            f"| `{baseline['baseline']}` | `{baseline['expected_split']}` | "
            f"{baseline['audit_rows']} | {baseline['unique_windows']} | "
            f"{baseline['matches_expected_split']} |"
        )

    lines.extend(["", "## Freeze status", ""])
    if data["issues"]:
        lines.append("Freeze completed with issues:")
        lines.append("")
        for issue in data["issues"]:
            lines.append(f"- {issue}")
    else:
        lines.append("Freeze completed successfully. All listed baselines match their expected frozen split.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> int:
    source_files = {
        "window_index": {
            "path": to_rel(WINDOW_INDEX),
            "exists": WINDOW_INDEX.exists(),
            "sha256": sha256_file(WINDOW_INDEX) if WINDOW_INDEX.exists() else None,
        },
        "baseline_reference": {
            "path": to_rel(BASELINE_REFERENCE),
            "exists": BASELINE_REFERENCE.exists(),
            "sha256": sha256_file(BASELINE_REFERENCE) if BASELINE_REFERENCE.exists() else None,
        },
    }

    window_rows = read_csv(WINDOW_INDEX) if WINDOW_INDEX.exists() else []
    baseline_rows = read_csv(BASELINE_REFERENCE) if BASELINE_REFERENCE.exists() else []
    data: dict[str, Any] = {
        "generated_at_utc": now_iso(),
        "phase": "phase2",
        "dataset_policy": "Nezha only",
        "freeze_policy": "Use these window IDs and inherited baseline artifacts for Phase 2 comparisons.",
        "source_files": source_files,
        "window_sets": summarize_window_sets(window_rows),
        "baseline_alignment": summarize_baselines(baseline_rows, window_rows),
    }
    data["issues"] = validate_freeze(data)

    write_json(FREEZE_JSON, data)
    write_markdown(FREEZE_MD, data)
    return 1 if data["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(build())
