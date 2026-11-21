from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib.image as mpimg


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.phase2.generate_paper_outputs import validate_baseline_reference
from src.phase2.retrieval.fusion_ranker import clamp01, graph_sim


HARD_STOP_IDS = {
    "baseline_reproducibility",
    "window_split_consistency",
    "audit_schema_validation",
    "score_final_bounds",
    "cache_api_separation",
}
REQUIRED_AUDIT_FIELDS = {
    "window_id",
    "ground_truth",
    "fault_type",
    "is_candidate",
    "final_decision",
    "fallback_status",
    "llm_called",
    "actual_api_calls",
    "cache_hits",
}
PAPER_TABLES = [
    "main_result_table.csv",
    "fault_type_breakdown.csv",
    "ablation_table.csv",
    "cost_latency_table.csv",
]
PAPER_FIGURES = [
    "f1_comparison.png",
    "context_coverage_comparison.png",
    "network_delay_recall.png",
    "alpha_beta_gamma_ablation.png",
    "service_graph_example.png",
]


@dataclass(frozen=True)
class GateCheck:
    check_id: str
    description: str
    status: str
    hard_stop: bool
    details: str
    evidence: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Phase 2 Step 9 reproducibility and claim-safety gate."
    )
    parser.add_argument(
        "--output-dir",
        default="outputs\\phase2\\quality_gate",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = absolute(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checks = run_checks()
    hard_stop_failures = [
        check.check_id
        for check in checks
        if check.hard_stop and check.status != "pass"
    ]
    failures = [check.check_id for check in checks if check.status != "pass"]
    status = "pass" if not failures else "fail"
    report = {
        "step": 9,
        "status": status,
        "paper_result_table_finalizable": not hard_stop_failures,
        "hard_stop_failures": hard_stop_failures,
        "failed_checks": failures,
        "checks": [asdict(check) for check in checks],
    }
    json_path = output_dir / "step9_quality_gate_report.json"
    csv_path = output_dir / "step9_quality_gate_report.csv"
    md_path = output_dir / "step9_quality_gate_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_csv(csv_path, checks)
    write_markdown(md_path, report, checks)
    print(json.dumps(report, indent=2))
    return 0 if status == "pass" else 1


def run_checks() -> list[GateCheck]:
    return [
        check_paper_outputs(),
        check_provenance(),
        check_baseline_reproducibility(),
        check_window_split_consistency(),
        check_debug_exclusion(),
        check_context_rescue_label(),
        check_score_final_bounds(),
        check_graph_infinity(),
        check_cache_api_separation(),
        check_manual_review_semantics(),
        check_claim_boundaries(),
        check_window_labels(),
        check_key_configs(),
        check_audit_schema(),
    ]


def check_paper_outputs() -> GateCheck:
    expected = [
        *(ROOT / "outputs/phase2/paper_tables" / name for name in PAPER_TABLES),
        *(ROOT / "outputs/phase2/figures" / name for name in PAPER_FIGURES),
    ]
    missing = [relative(path) for path in expected if not path.exists()]
    invalid_images = []
    for path in expected:
        if path.suffix != ".png" or not path.exists():
            continue
        image = mpimg.imread(path)
        if image.shape[0] < 500 or image.shape[1] < 700:
            invalid_images.append(f"{relative(path)}:{image.shape}")
    passed = not missing and not invalid_images
    return gate(
        "paper_outputs_location",
        "All four paper tables and five figures exist under outputs/phase2.",
        passed,
        f"missing={missing}; invalid_images={invalid_images}",
        [relative(path) for path in expected],
    )


def check_provenance() -> GateCheck:
    missing_sources: list[str] = []
    evidence: list[str] = []
    for table_name in PAPER_TABLES:
        table_path = ROOT / "outputs/phase2/paper_tables" / table_name
        for row in read_csv(table_path):
            source = row.get("source", "")
            if not source:
                missing_sources.append(f"{table_name}:missing source")
                continue
            source_path = absolute(source)
            if not source_path.exists():
                missing_sources.append(source)
            evidence.append(source)

    view_b_path = ROOT / "outputs/phase2/step7_view_b/step7_view_b_report.json"
    if not view_b_path.exists():
        missing_sources.append(relative(view_b_path))
    else:
        report = read_json(view_b_path)
        for variant in report.get("variants", []):
            for artifact_name, artifact_path in variant.get("artifacts", {}).items():
                if artifact_name == "cache_jsonl":
                    continue
                path = absolute(artifact_path)
                if not path.exists():
                    missing_sources.append(str(path))
                evidence.append(relative(path))
    return gate(
        "result_provenance",
        "Every paper result traces to a source artifact and View B traces to audit/config/summary.",
        not missing_sources,
        f"missing_sources={sorted(set(missing_sources))}",
        sorted(set(evidence)),
    )


def check_baseline_reproducibility() -> GateCheck:
    errors: list[str] = []
    reference_path = ROOT / "outputs/phase2/baseline_reference.csv"
    try:
        validate_baseline_reference(reference_path)
    except (ValueError, OSError) as exc:
        errors.append(str(exc))

    for row in read_csv(ROOT / "outputs/phase2/paper_tables/main_result_table.csv"):
        if row["comparison_view"] != "architecture_reference":
            continue
        source = read_single_row(absolute(row["source"]))
        comparisons = {
            "precision": "precision",
            "recall": "recall",
            "f1": "f1",
            "fpr": "false_positive_rate",
        }
        for table_field, source_field in comparisons.items():
            if not close(row[table_field], source[source_field]):
                errors.append(
                    f"{row['method']} {table_field}: table={row[table_field]} "
                    f"source={source[source_field]}"
                )
    return gate(
        "baseline_reproducibility",
        "Architecture-reference metrics match baseline_reference source summaries.",
        not errors,
        f"errors={errors}",
        [relative(reference_path)],
    )


def check_window_split_consistency() -> GateCheck:
    errors: list[str] = []
    freeze = read_json(ROOT / "outputs/phase2/input_freeze.json")
    expected = freeze["window_sets"]["paper_500"]
    for regime in ["operational_budget_120", "quality_full_budget"]:
        report = read_json(
            ROOT
            / "outputs/phase2/step7_rerun"
            / regime
            / "step7_view_a_report.json"
        )
        split_report = report["split_reports"][0]
        if split_report["rows"] != expected["rows"]:
            errors.append(f"View A {regime} row mismatch")
        if split_report["window_id_sha256"] != expected["window_id_sha256"]:
            errors.append(f"View A {regime} hash mismatch")
    view_b = read_json(ROOT / "outputs/phase2/step7_view_b/step7_view_b_report.json")
    protocol = view_b["protocol"]
    if protocol["windows"] != expected["rows"]:
        errors.append("View B row mismatch")
    if protocol["window_id_sha256"] != expected["window_id_sha256"]:
        errors.append("View B hash mismatch")
    return gate(
        "window_split_consistency",
        "BM25, topology and all View B methods use the frozen paper_500 window set.",
        not errors,
        f"errors={errors}",
        [
            "outputs/phase2/input_freeze.json",
            "outputs/phase2/step7_view_b/step7_view_b_report.json",
        ],
    )


def check_debug_exclusion() -> GateCheck:
    violations: list[str] = []
    for table_name in PAPER_TABLES:
        for row in read_csv(ROOT / "outputs/phase2/paper_tables" / table_name):
            source = row.get("source", "").lower()
            if "debug" in source or "smoke" in source:
                violations.append(f"{table_name}:{source}")
    return gate(
        "debug_smoke_exclusion",
        "Paper tables exclude debug and smoke artifacts.",
        not violations,
        f"violations={violations}",
        [f"outputs/phase2/paper_tables/{name}" for name in PAPER_TABLES],
    )


def check_context_rescue_label() -> GateCheck:
    violations = []
    paths = [
        ROOT / "outputs/phase2/paper_tables/main_result_table.csv",
        ROOT / "outputs/phase2/paper_tables/fault_type_breakdown.csv",
        ROOT / "outputs/phase2/paper_tables/cost_latency_table.csv",
        ROOT / "outputs/phase2/step7_view_b/step7_view_b_report.csv",
    ]
    seen = 0
    for path in paths:
        for row in read_csv(path):
            method = row.get("method", "")
            if "Context Rescue" not in method:
                continue
            seen += 1
            if row.get("architecture_enhanced", "").lower() != "true":
                violations.append(f"{relative(path)}:{method}")
    return gate(
        "context_rescue_label",
        "Context Rescue is always labeled architecture-enhanced.",
        seen > 0 and not violations,
        f"rows_checked={seen}; violations={violations}",
        [relative(path) for path in paths],
    )


def check_score_final_bounds() -> GateCheck:
    paths = score_artifact_paths()
    invalid: list[str] = []
    values_checked = 0
    for path in paths:
        for line_number, record in enumerate(read_jsonl(path), start=1):
            for value in score_values(record):
                values_checked += 1
                if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                    invalid.append(f"{relative(path)}:{line_number}:{value}")
    return gate(
        "score_final_bounds",
        "All recorded score_final values are finite and within [0,1].",
        values_checked > 0 and not invalid,
        f"values_checked={values_checked}; invalid={invalid[:10]}",
        [relative(path) for path in paths],
    )


def check_graph_infinity() -> GateCheck:
    errors = []
    if graph_sim(None) != 0.0:
        errors.append("graph_sim(None) != 0")
    if clamp01(float("inf")) != 0.0:
        errors.append("clamp01(inf) != 0")
    components_checked = 0
    for path in score_artifact_paths():
        for record in read_jsonl(path):
            for component in record.get("retrieved_context_score_components", []):
                if component.get("graph_distance") is None:
                    components_checked += 1
                    if float(component.get("graph_sim", 0.0)) != 0.0:
                        errors.append(f"{relative(path)} has non-zero unreachable GraphSim")
    return gate(
        "graph_infinity_handling",
        "Unreachable graph distance maps to GraphSim=0.",
        not errors,
        f"unreachable_components_checked={components_checked}; errors={errors[:10]}",
        ["src/phase2/retrieval/fusion_ranker.py"],
    )


def check_cache_api_separation() -> GateCheck:
    cost_rows = read_csv(ROOT / "outputs/phase2/paper_tables/cost_latency_table.csv")
    required = {"llm_calls", "actual_api_calls", "cache_hits", "cache_hit_rate"}
    errors = []
    if not cost_rows or not required.issubset(cost_rows[0]):
        errors.append("cost table missing cache/API columns")
    audit_paths = decision_audit_paths()
    records_checked = 0
    for path in audit_paths:
        for line_number, record in enumerate(read_jsonl(path), start=1):
            records_checked += 1
            actual = int(record.get("actual_api_calls", 0))
            cache_hits = int(record.get("cache_hits", 0))
            if actual and cache_hits:
                errors.append(f"{relative(path)}:{line_number}:actual_and_cache")
    return gate(
        "cache_api_separation",
        "Logical calls, actual API calls and cache hits are stored separately.",
        not errors,
        f"records_checked={records_checked}; errors={errors[:10]}",
        [
            "outputs/phase2/paper_tables/cost_latency_table.csv",
            *[relative(path) for path in audit_paths],
        ],
    )


def check_manual_review_semantics() -> GateCheck:
    errors = []
    manual_reviews = 0
    for path in decision_audit_paths():
        for line_number, record in enumerate(read_jsonl(path), start=1):
            if record.get("final_decision") == "manual_review":
                manual_reviews += 1
            if (
                record.get("fallback_status") == "llm_budget_exhausted"
                and record.get("final_decision") == "route_alert"
            ):
                errors.append(f"{relative(path)}:{line_number}:budget routed")
    return gate(
        "manual_review_semantics",
        "Manual review remains abstention and budget exhaustion never routes an alert.",
        manual_reviews > 0 and not errors,
        f"manual_reviews_checked={manual_reviews}; errors={errors}",
        [relative(path) for path in decision_audit_paths()],
    )


def check_claim_boundaries() -> GateCheck:
    report_path = ROOT / "EXPERIMENT_REPORT_FOR_SUBMISSION.md"
    text = report_path.read_text(encoding="utf-8").lower()
    required_phrases = [
        "not as proof that topology-aware fusion generally improves final diagnosis",
        "full root cause analysis",
        "generalization beyond nezha",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in text]
    forbidden_assertions = [
        "achieves full root cause analysis",
        "production-ready autonomous remediation",
        "superior to all rag variants",
    ]
    present_forbidden = [phrase for phrase in forbidden_assertions if phrase in text]
    return gate(
        "claim_boundaries",
        "Submission text preserves RCA, production-readiness and generalization boundaries.",
        not missing and not present_forbidden,
        f"missing_required={missing}; forbidden_assertions={present_forbidden}",
        [relative(report_path)],
    )


def check_window_labels() -> GateCheck:
    errors = []
    for table_name in PAPER_TABLES:
        path = ROOT / "outputs/phase2/paper_tables" / table_name
        rows = read_csv(path)
        if not rows or "split" not in rows[0]:
            errors.append(f"{table_name}:missing split column")
            continue
        for index, row in enumerate(rows, start=2):
            if not row.get("split"):
                errors.append(f"{table_name}:{index}:empty split")
    return gate(
        "table_window_labels",
        "Every paper table row identifies its window set.",
        not errors,
        f"errors={errors}",
        [f"outputs/phase2/paper_tables/{name}" for name in PAPER_TABLES],
    )


def check_key_configs() -> GateCheck:
    required = [
        ROOT / "outputs/phase2/input_freeze.json",
        ROOT / "outputs/phase2/retrieval/phase2_retrieval_run_config.json",
        ROOT / "outputs/phase2/ablation/ablation_selected_settings.json",
    ]
    for regime in ["operational_budget_120", "quality_full_budget"]:
        for variant in ["hybrid_bm25_top6", "topology_aware_fusion_top6"]:
            required.append(
                ROOT
                / "outputs/phase2/step7_rerun"
                / regime
                / "results"
                / f"step7_view_a_{regime}_paper_500_{variant}_config_snapshot.json"
            )
    view_b = read_json(ROOT / "outputs/phase2/step7_view_b/step7_view_b_report.json")
    for variant in view_b["variants"]:
        config_path = variant["artifacts"].get("config_snapshot")
        if config_path:
            required.append(absolute(config_path))
    missing = [relative(path) for path in required if not path.exists()]
    return gate(
        "key_configs_stored",
        "Frozen inputs and key retrieval/LLM configs are stored with results.",
        not missing,
        f"missing={missing}",
        [relative(path) for path in required],
    )


def check_audit_schema() -> GateCheck:
    errors = []
    records_checked = 0
    for path in decision_audit_paths():
        for line_number, record in enumerate(read_jsonl(path), start=1):
            records_checked += 1
            missing = REQUIRED_AUDIT_FIELDS - set(record)
            if missing:
                errors.append(
                    f"{relative(path)}:{line_number}:missing={sorted(missing)}"
                )
            if record.get("final_decision") not in {
                "route_alert",
                "suppress",
                "manual_review",
            }:
                errors.append(
                    f"{relative(path)}:{line_number}:invalid final_decision"
                )
    return gate(
        "audit_schema_validation",
        "Decision audit JSONL records contain the required schema and valid decisions.",
        records_checked > 0 and not errors,
        f"records_checked={records_checked}; errors={errors[:10]}",
        [relative(path) for path in decision_audit_paths()],
    )


def gate(
    check_id: str,
    description: str,
    passed: bool,
    details: str,
    evidence: list[str],
) -> GateCheck:
    return GateCheck(
        check_id=check_id,
        description=description,
        status="pass" if passed else "fail",
        hard_stop=check_id in HARD_STOP_IDS,
        details=details,
        evidence=evidence,
    )


def score_artifact_paths() -> list[Path]:
    paths = [
        ROOT / "outputs/phase2/retrieval/topk_contexts.jsonl",
        ROOT / "outputs/phase2/retrieval/topk_contexts_debug.jsonl",
        ROOT / "outputs/phase2/ablation/ablation_topk_contexts.jsonl",
    ]
    paths.extend(
        sorted(
            (ROOT / "outputs/phase2/step7_rerun").glob("*/*/*.jsonl")
        )
    )
    paths.extend(
        sorted((ROOT / "outputs/phase2/step7_view_b/audit").glob("*.jsonl"))
    )
    return [path for path in paths if path.exists()]


def decision_audit_paths() -> list[Path]:
    paths = sorted(
        (ROOT / "outputs/phase2/step7_rerun").glob("*/audit/*.jsonl")
    )
    paths.extend(
        sorted((ROOT / "outputs/phase2/step7_view_b/audit").glob("*.jsonl"))
    )
    return paths


def score_values(value: Any, key: str | None = None) -> Iterable[float]:
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            yield from score_values(child_value, child_key)
    elif isinstance(value, list):
        if key == "score_final":
            for item in value:
                if isinstance(item, (int, float)):
                    yield float(item)
        else:
            for item in value:
                yield from score_values(item, key)
    elif key == "score_final" and isinstance(value, (int, float)):
        yield float(value)


def close(left: str, right: str, tolerance: float = 1e-6) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_single_row(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    if len(rows) != 1:
        raise ValueError(f"Expected one row in {path}, found {len(rows)}")
    return rows[0]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc


def write_csv(path: Path, checks: list[GateCheck]) -> None:
    rows = [
        {
            **asdict(check),
            "evidence": ";".join(check.evidence),
        }
        for check in checks
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    path: Path,
    report: dict[str, Any],
    checks: list[GateCheck],
) -> None:
    lines = [
        "# Step 9 Quality Gate Report",
        "",
        f"- Overall status: **{report['status'].upper()}**",
        f"- Paper result table finalizable: `{report['paper_result_table_finalizable']}`",
        f"- Hard-stop failures: `{report['hard_stop_failures']}`",
        "",
        "| Check | Status | Hard stop | Details |",
        "|---|---|---:|---|",
    ]
    for check in checks:
        lines.append(
            f"| `{check.check_id}` | **{check.status.upper()}** | "
            f"{str(check.hard_stop).lower()} | {check.details.replace('|', '/')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def absolute(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate
        posix = candidate.as_posix()
        for marker in ("outputs/phase2", "nezha_setup"):
            idx = posix.find(marker)
            if idx != -1:
                remapped = ROOT / posix[idx:]
                if remapped.exists():
                    return remapped
        return candidate
    return ROOT / candidate


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        posix = path.as_posix()
        for marker in ("outputs/phase2", "nezha_setup"):
            idx = posix.find(marker)
            if idx != -1:
                return posix[idx:]
        return posix


if __name__ == "__main__":
    raise SystemExit(main())
