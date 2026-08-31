from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Any

from src.evaluation.metrics import summarize


def write_result(
    mode: str,
    records: list[dict[str, Any]],
    output_dir: str,
    config: dict[str, Any] | None = None,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary = summarize(records)
    if config is not None:
        _add_cost_estimate(summary, config)
    path = output_path / f"{mode}_results.json"
    path.write_text(json.dumps({"mode": mode, "summary": summary, "records": records}, indent=2), encoding="utf-8")
    _write_summary_markdown(output_path / f"{mode}_summary.md", mode, summary)
    _write_summary_csv(output_path / f"{mode}_summary.csv", mode, summary)
    _write_group_csv(output_path / f"{mode}_by_service.csv", "service_id", summary.get("by_service", {}))
    _write_group_csv(output_path / f"{mode}_by_fault_type.csv", "fault_type", summary.get("by_fault_type", {}))
    if config is not None:
        snapshot_path = output_path / f"{mode}_config_snapshot.json"
        snapshot_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def _write_summary_markdown(path: Path, mode: str, summary: dict[str, Any]) -> None:
    lines = [
        f"# Experiment Summary: {mode}",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        if isinstance(value, dict):
            value = f"see `{path.stem.replace('_summary', '')}_by_{key.removeprefix('by_')}.csv`"
        lines.append(f"| `{key}` | {value} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_csv(path: Path, mode: str, summary: dict[str, Any]) -> None:
    scalar_summary = {key: value for key, value in summary.items() if not isinstance(value, dict)}
    keys = ["mode", *scalar_summary.keys()]
    values = [mode, *[scalar_summary[key] for key in scalar_summary]]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(keys)
        writer.writerow(values)


def _write_group_csv(path: Path, group_key_name: str, groups: dict[str, dict[str, Any]]) -> None:
    metric_keys = [
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "tp",
        "fp",
        "tn",
        "fn",
        "windows",
        "candidate_alerts",
        "llm_calls",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[group_key_name, *metric_keys])
        writer.writeheader()
        for group_key, metrics in groups.items():
            writer.writerow({group_key_name: group_key, **{key: metrics.get(key, 0) for key in metric_keys}})


def _add_cost_estimate(summary: dict[str, Any], config: dict[str, Any]) -> None:
    llm_config = config.get("llm", {})
    input_rate = float(llm_config.get("input_cost_per_1m_tokens", 0.0) or 0.0)
    output_rate = float(llm_config.get("output_cost_per_1m_tokens", 0.0) or 0.0)
    input_tokens = float(summary.get("input_tokens", 0))
    output_tokens = float(summary.get("output_tokens", 0))
    summary["llm_cost_pricing_source"] = str(llm_config.get("cost_pricing_source", "not_configured"))
    summary["estimated_input_cost_usd"] = round((input_tokens / 1_000_000) * input_rate, 8)
    summary["estimated_output_cost_usd"] = round((output_tokens / 1_000_000) * output_rate, 8)
    summary["estimated_llm_cost_usd"] = round(
        summary["estimated_input_cost_usd"] + summary["estimated_output_cost_usd"],
        8,
    )
