from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[2]
OUT_PHASE1 = ROOT / "outputs" / "phase1"
OUT_PHASE2 = ROOT / "outputs" / "phase2"

DATASET_NAME = "IntelligentDDS/Nezha"

PHASE1_DOCS = [
    "EXPERIMENT_REPORT_FOR_SUBMISSION.md",
    "DATASET_REPORT.md",
    "reports/audit_failure_analysis.md",
    "reports/audit_failure_by_fault_type.csv",
    "reports/audit_failure_by_service.csv",
    "reports/audit_failure_by_pod.csv",
    "reports/audit_failure_hotspots.csv",
    "reports/consolidated_experiment_metrics.csv",
    "reports/evaluation_criteria_mapping.md",
    "reports/tradeoff_analysis_table.md",
    "reports/experiment_summary_no_rerun.md",
    "reports/thesis_insert_sections.md",
]

PHASE1_OUTPUT_ROOTS = [
    "nezha_setup/outputs/phase3_smoke/ablation",
    "nezha_setup/outputs/phase4_benchmark/results",
    "nezha_setup/outputs/phase5_context_rescue/results",
    "nezha_setup/outputs/real_llm_stratified",
    "nezha_setup/outputs/local_first_ollama_smoke",
    "nezha_setup/outputs/**/audit",
]

REQUIRED_FAULT_TYPES = [
    "network_delay",
    "cpu_contention",
    "cpu_consumed",
    "exception",
    "return",
    "none",
]


@dataclass
class BaselineRef:
    name: str
    audit_path: str
    summary_csv: str
    summary_md: str


BASELINE_REFS: List[BaselineRef] = [
    BaselineRef(
        name="detector_only",
        audit_path="nezha_setup/outputs/phase4_benchmark/audit/detector_only_audit.jsonl",
        summary_csv="nezha_setup/outputs/phase4_benchmark/results/detector_only_summary.csv",
        summary_md="nezha_setup/outputs/phase4_benchmark/results/detector_only_summary.md",
    ),
    BaselineRef(
        name="llm_without_rag",
        audit_path="nezha_setup/outputs/phase4_benchmark/audit/llm_without_rag_audit.jsonl",
        summary_csv="nezha_setup/outputs/phase4_benchmark/results/llm_without_rag_summary.csv",
        summary_md="nezha_setup/outputs/phase4_benchmark/results/llm_without_rag_summary.md",
    ),
    BaselineRef(
        name="hybrid_bm25_top6",
        audit_path="nezha_setup/outputs/phase4_benchmark/audit/hybrid_bm25_top6_audit.jsonl",
        summary_csv="nezha_setup/outputs/phase4_benchmark/results/hybrid_bm25_top6_summary.csv",
        summary_md="nezha_setup/outputs/phase4_benchmark/results/hybrid_bm25_top6_summary.md",
    ),
    BaselineRef(
        name="hybrid_bm25_top10",
        audit_path="nezha_setup/outputs/phase4_benchmark/audit/hybrid_bm25_top10_audit.jsonl",
        summary_csv="nezha_setup/outputs/phase4_benchmark/results/hybrid_bm25_top10_summary.csv",
        summary_md="nezha_setup/outputs/phase4_benchmark/results/hybrid_bm25_top10_summary.md",
    ),
    BaselineRef(
        name="phase5_context_rescue",
        audit_path="nezha_setup/outputs/phase5_context_rescue/audit/hybrid_audit.jsonl",
        summary_csv="nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.csv",
        summary_md="nezha_setup/outputs/phase5_context_rescue/results/hybrid_summary.md",
    ),
    BaselineRef(
        name="real_llm_500w_cache_replay",
        audit_path="nezha_setup/outputs/real_llm_stratified/audit/gemini25_flash_lite_500w_budget_manual_review_cache_replay_audit.jsonl",
        summary_csv="nezha_setup/outputs/real_llm_stratified/results/gemini25_flash_lite_500w_budget_manual_review_cache_replay_summary.csv",
        summary_md="nezha_setup/outputs/real_llm_stratified/results/gemini25_flash_lite_500w_budget_manual_review_cache_replay_summary.md",
    ),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def unique_windows(rows: Iterable[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for row in rows:
        window_id = row.get("window_id")
        if not window_id or window_id in seen:
            continue
        seen.add(window_id)
        out.append(row)
    return out


def pick_debug_50(rows_500: List[Dict]) -> List[Dict]:
    by_fault = defaultdict(list)
    for row in rows_500:
        by_fault[row.get("fault_type", "none")].append(row)
    for group in by_fault.values():
        group.sort(
            key=lambda r: (
                float(r.get("anomaly_score") or 0.0),
                str(r.get("window_id") or ""),
            ),
            reverse=True,
        )

    selected = []
    selected_ids = set()

    # Ensure required fault-type coverage first (up to 2 each where available)
    for fault in REQUIRED_FAULT_TYPES:
        for row in by_fault.get(fault, [])[:2]:
            wid = row.get("window_id")
            if wid and wid not in selected_ids:
                selected.append(row)
                selected_ids.add(wid)

    if len(selected) >= 50:
        return selected[:50]

    # Fill remainder by highest anomaly score globally.
    global_sorted = sorted(
        rows_500,
        key=lambda r: (
            float(r.get("anomaly_score") or 0.0),
            str(r.get("window_id") or ""),
        ),
        reverse=True,
    )
    for row in global_sorted:
        wid = row.get("window_id")
        if not wid or wid in selected_ids:
            continue
        selected.append(row)
        selected_ids.add(wid)
        if len(selected) >= 50:
            break
    return selected


def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def to_rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def build() -> None:
    OUT_PHASE1.mkdir(parents=True, exist_ok=True)
    OUT_PHASE2.mkdir(parents=True, exist_ok=True)

    source_300 = ROOT / "nezha_setup" / "outputs" / "phase5_context_rescue" / "audit" / "hybrid_audit.jsonl"
    source_500 = (
        ROOT
        / "nezha_setup"
        / "outputs"
        / "real_llm_stratified"
        / "audit"
        / "gemini25_flash_lite_500w_budget_manual_review_cache_replay_audit.jsonl"
    )

    rows_300 = unique_windows(read_jsonl(source_300))
    rows_500 = unique_windows(read_jsonl(source_500))
    rows_50 = pick_debug_50(rows_500)

    window_rows: List[Dict] = []
    split_rows = [("debug_50", rows_50, source_500), ("paper_300", rows_300, source_300), ("paper_500", rows_500, source_500)]
    for split, rows, source in split_rows:
        for idx, row in enumerate(rows, start=1):
            window_rows.append(
                {
                    "dataset": DATASET_NAME,
                    "split": split,
                    "window_index": idx,
                    "window_id": row.get("window_id", ""),
                    "alert_id": row.get("alert_id", ""),
                    "service_id": row.get("service_id", ""),
                    "node_id": row.get("node_id", ""),
                    "fault_type": row.get("fault_type", ""),
                    "ground_truth": row.get("ground_truth", ""),
                    "anomaly_score": row.get("anomaly_score", ""),
                    "source_audit_path": to_rel(source),
                }
            )

    write_csv(
        OUT_PHASE2 / "window_index.csv",
        window_rows,
        [
            "dataset",
            "split",
            "window_index",
            "window_id",
            "alert_id",
            "service_id",
            "node_id",
            "fault_type",
            "ground_truth",
            "anomaly_score",
            "source_audit_path",
        ],
    )

    baseline_rows = []
    manifest_baselines = []
    for ref in BASELINE_REFS:
        audit_abs = ROOT / ref.audit_path
        summary_csv_abs = ROOT / ref.summary_csv
        summary_md_abs = ROOT / ref.summary_md
        baseline_rows.append(
            {
                "baseline": ref.name,
                "audit_path": ref.audit_path,
                "audit_rows": line_count(audit_abs),
                "summary_csv": ref.summary_csv,
                "summary_md": ref.summary_md,
                "exists_audit": audit_abs.exists(),
                "exists_summary_csv": summary_csv_abs.exists(),
                "exists_summary_md": summary_md_abs.exists(),
            }
        )
        manifest_baselines.append(
            {
                "name": ref.name,
                "audit_path": ref.audit_path,
                "audit_rows": line_count(audit_abs),
                "summary_csv": ref.summary_csv,
                "summary_md": ref.summary_md,
            }
        )

    write_csv(
        OUT_PHASE2 / "baseline_reference.csv",
        baseline_rows,
        [
            "baseline",
            "audit_path",
            "audit_rows",
            "summary_csv",
            "summary_md",
            "exists_audit",
            "exists_summary_csv",
            "exists_summary_md",
        ],
    )

    split_stats = {}
    for split_name, rows in [("debug_50", rows_50), ("paper_300", rows_300), ("paper_500", rows_500)]:
        split_stats[split_name] = {
            "windows": len(rows),
            "fault_type_counts": dict(sorted(Counter((r.get("fault_type") or "none") for r in rows).items())),
            "ground_truth_counts": dict(sorted(Counter((r.get("ground_truth") or "unknown") for r in rows).items())),
        }

    source_docs = [{"path": doc, "exists": (ROOT / doc).exists()} for doc in PHASE1_DOCS]
    output_roots = [{"path": p, "exists": bool(list(ROOT.glob(p)))} for p in PHASE1_OUTPUT_ROOTS]

    manifest = {
        "generated_at_utc": now_iso(),
        "phase": "phase2",
        "dataset_policy": "Nezha only",
        "window_policy": "stratified_50_300_500",
        "budget_policy": "decision.llm_budget_exhausted_action=manual_review",
        "decision_guard": "require_evidence_for_true_alert=true",
        "source_of_truth": {
            "documents": source_docs,
            "phase1_output_roots": output_roots,
        },
        "baselines_inherited": manifest_baselines,
        "window_sets": split_stats,
    }
    write_json(OUT_PHASE2 / "audit_manifest.json", manifest)

    legacy_index = {
        "generated_at_utc": now_iso(),
        "description": "Index of pre-Phase2 outputs retained for Phase1 reproducibility.",
        "roots": output_roots,
    }
    write_json(OUT_PHASE1 / "legacy_output_index.json", legacy_index)


if __name__ == "__main__":
    build()
