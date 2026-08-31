from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

DEFAULT_AUDITS = [
    (
        "phase4_hybrid_bm25_top6",
        "nezha_setup/outputs/phase4_benchmark/audit/hybrid_bm25_top6_audit.jsonl",
    ),
    (
        "phase5_context_rescue",
        "nezha_setup/outputs/phase5_context_rescue/audit/hybrid_audit.jsonl",
    ),
    (
        "real_llm_500w_cache_replay",
        "nezha_setup/outputs/real_llm_stratified/audit/"
        "gemini25_flash_lite_500w_budget_manual_review_cache_replay_audit.jsonl",
    ),
]

GROUP_COLUMNS = [
    "run",
    "group",
    "windows",
    "candidates",
    "routed",
    "manual_review",
    "tp",
    "fp",
    "tn",
    "fn",
    "precision",
    "recall",
    "f1",
    "fpr",
    "llm_calls",
    "context_coverage",
    "avg_context",
    "avg_anomaly_score",
]
POD_COLUMNS = [
    "run",
    "service_id",
    "node_id",
    "fault_type",
    "windows",
    "candidates",
    "routed",
    "manual_review",
    "tp",
    "fp",
    "tn",
    "fn",
    "precision",
    "recall",
    "f1",
    "fpr",
    "llm_calls",
    "avg_anomaly_score",
]
HOTSPOT_COLUMNS = [
    "run",
    "hotspot_type",
    "service_id",
    "node_id",
    "fault_type",
    "windows",
    "fp",
    "fn",
    "tp",
    "precision",
    "recall",
    "candidates",
    "manual_review",
    "top_final_decisions",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FP/FN analysis tables from existing audit JSONL logs.")
    parser.add_argument("--audit", action="append", default=[], help="label=path. Can be passed multiple times.")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--top-n", type=int, default=12)
    args = parser.parse_args()

    audit_specs = parse_audit_specs(args.audit) if args.audit else DEFAULT_AUDITS
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    all_fault_rows: list[dict[str, Any]] = []
    all_service_rows: list[dict[str, Any]] = []
    all_pod_rows: list[dict[str, Any]] = []
    all_hotspot_rows: list[dict[str, Any]] = []

    for run, rel_path in audit_specs:
        path = Path(rel_path)
        if not path.is_absolute():
            path = ROOT / path
        records = load_jsonl(path)
        if not records:
            continue
        all_fault_rows.extend(group_records(run, records, lambda record: str(record.get("fault_type") or "unknown")))
        all_service_rows.extend(group_records(run, records, lambda record: str(record.get("service_id") or "unknown")))
        all_pod_rows.extend(group_pods(run, records))
        all_hotspot_rows.extend(build_hotspots(run, records, args.top_n))

    write_csv(output_dir / "audit_failure_by_fault_type.csv", GROUP_COLUMNS, all_fault_rows)
    write_csv(output_dir / "audit_failure_by_service.csv", GROUP_COLUMNS, all_service_rows)
    write_csv(output_dir / "audit_failure_by_pod.csv", POD_COLUMNS, all_pod_rows)
    write_csv(output_dir / "audit_failure_hotspots.csv", HOTSPOT_COLUMNS, all_hotspot_rows)
    write_markdown_report(output_dir / "audit_failure_analysis.md", all_fault_rows, all_service_rows, all_pod_rows, all_hotspot_rows)
    print(f"wrote audit failure analysis to {output_dir}")


def parse_audit_specs(values: list[str]) -> list[tuple[str, str]]:
    specs = []
    for value in values:
        if "=" not in value:
            raise ValueError("--audit must use label=path")
        label, path = value.split("=", 1)
        specs.append((label.strip(), path.strip()))
    return specs


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def group_records(run: str, records: list[dict[str, Any]], key_fn: Any) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[key_fn(record)].append(record)
    return [
        {"run": run, "group": key, **summarize_records(group_records)}
        for key, group_records in sorted(groups.items())
    ]


def group_pods(run: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (
            str(record.get("service_id") or "unknown"),
            str(record.get("node_id") or "unknown"),
            str(record.get("fault_type") or "unknown"),
        )
        groups[key].append(record)

    rows = []
    for (service_id, node_id, fault_type), grouped in sorted(groups.items()):
        summary = summarize_records(grouped)
        rows.append(
            {
                "run": run,
                "service_id": service_id,
                "node_id": node_id,
                "fault_type": fault_type,
                **summary,
            }
        )
    rows.sort(key=lambda row: (int(row["fp"]) + int(row["fn"]), int(row["windows"])), reverse=True)
    return rows


def build_hotspots(run: str, records: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    pod_rows = group_pods(run, records)
    fp_rows = [
        hotspot_row(run, "fp_hotspot", row)
        for row in sorted(pod_rows, key=lambda item: (int(item["fp"]), int(item["windows"])), reverse=True)
        if int(row["fp"]) > 0
    ][:top_n]
    fn_rows = [
        hotspot_row(run, "fn_hotspot", row)
        for row in sorted(pod_rows, key=lambda item: (int(item["fn"]), int(item["windows"])), reverse=True)
        if int(row["fn"]) > 0
    ][:top_n]
    return fp_rows + fn_rows


def hotspot_row(run: str, hotspot_type: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run": run,
        "hotspot_type": hotspot_type,
        "service_id": row["service_id"],
        "node_id": row["node_id"],
        "fault_type": row["fault_type"],
        "windows": row["windows"],
        "fp": row["fp"],
        "fn": row["fn"],
        "tp": row["tp"],
        "precision": row["precision"],
        "recall": row["recall"],
        "candidates": row["candidates"],
        "manual_review": row["manual_review"],
        "top_final_decisions": row.get("top_final_decisions", ""),
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    decisions: Counter[str] = Counter()
    candidate_count = routed_count = manual_review_count = llm_calls = context_count = 0
    context_total = 0.0
    score_total = 0.0
    for record in records:
        truth = record.get("ground_truth") == "true_alert"
        predicted = record.get("final_decision") == "route_alert"
        if truth and predicted:
            tp += 1
        elif not truth and predicted:
            fp += 1
        elif not truth and not predicted:
            tn += 1
        else:
            fn += 1

        final_decision = str(record.get("final_decision") or "unknown")
        decisions[final_decision] += 1
        candidate_count += 1 if record.get("is_candidate") else 0
        routed_count += 1 if final_decision == "route_alert" else 0
        manual_review_count += 1 if final_decision == "manual_review" else 0
        llm_calls += 1 if record.get("llm_called") else 0
        retrieved = int(record.get("retrieved_context_count", 0) or 0)
        context_count += 1 if retrieved > 0 else 0
        context_total += retrieved
        score_total += float(record.get("anomaly_score", 0.0) or 0.0)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    windows = len(records)
    return {
        "windows": windows,
        "candidates": candidate_count,
        "routed": routed_count,
        "manual_review": manual_review_count,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "llm_calls": llm_calls,
        "context_coverage": round(context_count / windows, 4) if windows else 0.0,
        "avg_context": round(context_total / windows, 4) if windows else 0.0,
        "avg_anomaly_score": round(score_total / windows, 4) if windows else 0.0,
        "top_final_decisions": inline_counter(decisions),
    }


def inline_counter(counter: Counter[str], limit: int = 4) -> str:
    return ", ".join(f"{key}={value}" for key, value in counter.most_common(limit))


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_markdown_report(
    path: Path,
    fault_rows: list[dict[str, Any]],
    service_rows: list[dict[str, Any]],
    pod_rows: list[dict[str, Any]],
    hotspot_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# Audit Failure Analysis",
        "",
        "Derived from existing Nezha audit JSONL files only. No LLM/API call is made.",
        "",
        "Classification uses the existing evaluator rule: `ground_truth == true_alert` is positive and `final_decision == route_alert` is predicted positive.",
    ]
    lines.extend(markdown_section("## By Fault Type", GROUP_COLUMNS, fault_rows))
    lines.extend(markdown_section("## By Service", GROUP_COLUMNS, rank_failures(service_rows, 20)))
    lines.extend(markdown_section("## FP/FN Hotspots", HOTSPOT_COLUMNS, hotspot_rows))
    lines.extend(markdown_section("## Top Pod Failure Rows", POD_COLUMNS, rank_failures(pod_rows, 30)))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rank_failures(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (int(row.get("fp", 0)) + int(row.get("fn", 0)), int(row.get("windows", 0))), reverse=True)[:limit]


def markdown_section(title: str, columns: list[str], rows: list[dict[str, Any]]) -> list[str]:
    output = ["", title, "", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        output.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return output


if __name__ == "__main__":
    main()
