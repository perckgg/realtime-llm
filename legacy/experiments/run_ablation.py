from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.evaluation.metrics import false_positive_reduction, summarize
from src.main import run_pipeline


VARIANTS = {
    "detector_only": {"mode": "detector_only"},
    "llm_without_rag": {"mode": "llm_without_rag"},
    "hybrid": {"mode": "hybrid"},
    "hybrid_no_gate": {"mode": "hybrid", "llm_gate_enabled": False},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="nezha_setup/config/experiment_nezha_smoke.yaml")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--variants", default="detector_only,llm_without_rag,hybrid,hybrid_no_gate")
    args = parser.parse_args()

    base_config = load_config(args.config)
    output_root = Path(args.output_dir or Path(base_config["evaluation"]["output_dir"]).parent / "ablation")
    audit_root = output_root / "audit"
    output_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, dict[str, Any]] = {}
    for variant in _requested_variants(args.variants):
        variant_config = _variant_config(base_config, variant, output_root, audit_root)
        run_mode = VARIANTS[variant]["mode"]
        records, _ = run_pipeline(variant_config, run_mode, output_mode=variant)
        summaries[variant] = summarize(records)

    detector_summary = summaries.get("detector_only", {})
    for summary in summaries.values():
        summary["false_positive_reduction_vs_detector"] = false_positive_reduction(detector_summary, summary)

    (output_root / "ablation_report.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    _write_csv(output_root / "ablation_summary.csv", summaries)
    _write_markdown(output_root / "ablation_summary.md", summaries)
    print(json.dumps(summaries, indent=2))


def _requested_variants(value: str) -> list[str]:
    variants = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [variant for variant in variants if variant not in VARIANTS]
    if unknown:
        raise ValueError(f"Unknown ablation variants: {', '.join(unknown)}")
    return variants


def _variant_config(
    base_config: dict[str, Any],
    variant: str,
    output_root: Path,
    audit_root: Path,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config.setdefault("experiment", {})["name"] = f"{base_config.get('experiment', {}).get('name', 'experiment')}_{variant}"
    config.setdefault("evaluation", {})["output_dir"] = str(output_root)
    config.setdefault("evaluation", {})["audit_dir"] = str(audit_root)
    if VARIANTS[variant].get("llm_gate_enabled") is False:
        config.setdefault("llm_gate", {})["enabled"] = False
    return config


def _write_csv(path: Path, summaries: dict[str, dict[str, Any]]) -> None:
    keys = [
        "variant",
        "evaluated_windows",
        "candidate_alerts",
        "routed_alerts",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "false_positive_reduction_vs_detector",
        "llm_calls",
        "llm_calls_avoided",
        "avg_retrieval_latency_ms",
        "avg_llm_latency_ms",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        for variant, summary in summaries.items():
            writer.writerow({"variant": variant, **{key: summary.get(key, 0) for key in keys if key != "variant"}})


def _write_markdown(path: Path, summaries: dict[str, dict[str, Any]]) -> None:
    lines = [
        "# Ablation Study Summary",
        "",
        "| Variant | Windows | Candidates | Precision | Recall | F1 | FPR | FP Reduction | LLM Calls |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in summaries.items():
        lines.append(
            "| {variant} | {windows} | {candidates} | {precision} | {recall} | {f1} | {fpr} | {fp_reduction} | {llm_calls} |".format(
                variant=variant,
                windows=summary.get("evaluated_windows", 0),
                candidates=summary.get("candidate_alerts", 0),
                precision=summary.get("precision", 0),
                recall=summary.get("recall", 0),
                f1=summary.get("f1", 0),
                fpr=summary.get("false_positive_rate", 0),
                fp_reduction=summary.get("false_positive_reduction_vs_detector", 0),
                llm_calls=summary.get("llm_calls", 0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
