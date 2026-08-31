from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SUMMARY_PATH = ROOT / "cloud_monitor_setup" / "processed" / "summary.json"
DETECTOR_RESULT_PATH = ROOT / "cloud_monitor_setup" / "outputs" / "current_results" / "detector_only_results.json"
THRESHOLD_SWEEP_PATH = REPORTS / "cloud_monitoring_threshold_sweep.csv"
DOMAIN_ANALYSIS_PATH = REPORTS / "cloud_monitoring_domain_analysis.csv"


METRIC_COLUMNS = [
    "mode",
    "evaluated_windows",
    "candidate_alerts",
    "routed_alerts",
    "precision",
    "recall",
    "f1",
    "false_positive_rate",
    "tp",
    "fp",
    "tn",
    "fn",
    "llm_calls",
    "llm_calls_avoided",
    "input_tokens",
    "output_tokens",
    "avg_detector_latency_ms",
    "avg_retrieval_latency_ms",
    "avg_llm_latency_ms",
    "avg_end_to_end_latency_ms",
    "false_positive_reduction_vs_detector",
]


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    dataset_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    detector_payload = json.loads(DETECTOR_RESULT_PATH.read_text(encoding="utf-8"))
    detector_summary = detector_payload["summary"]
    write_metrics_csv(detector_summary)
    write_report(dataset_summary, detector_summary)


def write_metrics_csv(detector_summary: dict[str, Any]) -> None:
    path = REPORTS / "cloud_monitoring_experiment_metrics.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                column: detector_summary.get(column, "") if column != "mode" else "detector_only"
                for column in METRIC_COLUMNS
            }
        )


def write_report(dataset_summary: dict[str, Any], detector: dict[str, Any]) -> None:
    lines = [
        "# Microsoft Cloud Monitoring Dataset Experiment",
        "",
        "This report documents when the Microsoft cloud-monitoring-dataset is used, how it was adapted to the pipeline, and what detector-only metrics were collected. This dataset is not used for RAG or external LLM/API evaluation.",
        "",
        "## 1. Dataset Role",
        "",
        "The Microsoft dataset is used as a metric-only anomaly detection benchmark. It contains time-series metric values and point labels, but it does not contain operational logs/traces comparable to Nezha. Therefore, it is only appropriate for validating preprocessing, windowing, and detector baseline behavior.",
        "",
        "In the thesis, this dataset should be introduced before the Nezha hybrid RAG experiments as an initial metric-stream feasibility dataset. It should not be used for RAG/API experiments because the generated `logs.jsonl` only contains metadata context extracted from dataset metadata files, and the detector produces too many candidates for practical external API judging.",
        "",
        "## 2. Prepared Data Summary",
        "",
        f"- Source root: `{dataset_summary.get('dataset_root')}`",
        f"- Time series count: {dataset_summary.get('series_count')}",
        f"- Metric points: {dataset_summary.get('point_count')}",
        f"- Anomaly points: {dataset_summary.get('anomaly_point_count')}",
        f"- Skipped points: {dataset_summary.get('skipped_point_count')}",
        "",
        "| Domain | Series | Points | Anomaly points | Skipped points |",
        "|---|---:|---:|---:|---:|",
    ]
    for domain, summary in sorted(dict(dataset_summary.get("domains", {})).items()):
        lines.append(
            "| {domain} | {series_count} | {point_count} | {anomaly_point_count} | {skipped_point_count} |".format(
                domain=domain,
                series_count=summary.get("series_count", ""),
                point_count=summary.get("point_count", ""),
                anomaly_point_count=summary.get("anomaly_point_count", ""),
                skipped_point_count=summary.get("skipped_point_count", ""),
            )
        )

    lines.extend(
        [
            "",
            "## 3. Experiment Setup",
            "",
            "| Item | Value |",
            "|---|---|",
            "| Config | `cloud_monitor_setup/config/experiment_current.yaml` |",
            "| Processed metrics | `cloud_monitor_setup/processed/metrics.csv` |",
            "| Metadata context | not used in reported results; `logs.jsonl` is metadata-only legacy context |",
            "| Window size / stride | 3600s / 3600s |",
            "| Detector | `feature_pressure`, threshold 0.85 |",
            "| LLM provider | not used |",
            "| Detector-only output | `cloud_monitor_setup/outputs/current_results/detector_only_results.json` |",
            "| Detector-only audit | `cloud_monitor_setup/outputs/current_audit/detector_only_audit.jsonl` |",
            "| Threshold sweep | `reports/cloud_monitoring_threshold_sweep.csv` |",
            "| Domain analysis | `reports/cloud_monitoring_domain_analysis.csv` |",
            "",
            "The feature set prepared for the detector includes raw value, robust value z-score, and absolute delta z-score. A window is labeled `true_alert` if any point inside the one-hour window is labeled anomalous.",
            "",
            "## 4. Results",
            "",
            "| Mode | Windows | Candidates | Routed | Precision | Recall | F1 | FPR | TP | FP | TN | FN | LLM calls | Calls avoided |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    lines.append(
        "| {mode} | {evaluated_windows} | {candidate_alerts} | {routed_alerts} | {precision} | {recall} | {f1} | {false_positive_rate} | {tp} | {fp} | {tn} | {fn} | {llm_calls} | {llm_calls_avoided} |".format(
            mode="detector_only",
            evaluated_windows=value(detector, "evaluated_windows"),
            candidate_alerts=value(detector, "candidate_alerts"),
            routed_alerts=value(detector, "routed_alerts"),
            precision=value(detector, "precision"),
            recall=value(detector, "recall"),
            f1=value(detector, "f1"),
            false_positive_rate=value(detector, "false_positive_rate"),
            tp=value(detector, "tp"),
            fp=value(detector, "fp"),
            tn=value(detector, "tn"),
            fn=value(detector, "fn"),
            llm_calls=value(detector, "llm_calls"),
            llm_calls_avoided=value(detector, "llm_calls_avoided"),
        )
    )

    append_csv_section(
        lines,
        "## 5. Threshold Sweep",
        THRESHOLD_SWEEP_PATH,
        "Threshold 0.85 remains the initial balance point: lower thresholds keep more recall but create more candidates; higher thresholds reduce candidates/FPR but lose recall.",
    )
    append_csv_section(
        lines,
        "## 6. Domain Analysis",
        DOMAIN_ANALYSIS_PATH,
        "Domains with no positive anomaly windows use `0.0` recall/F1 by denominator convention; use them only to inspect false-positive behavior.",
    )

    lines.extend(
        [
            "",
            "## 7. Interpretation",
            "",
            f"- `detector_only` evaluated {value(detector, 'evaluated_windows')} one-hour windows and generated {value(detector, 'candidate_alerts')} candidate alerts. It achieved recall {value(detector, 'recall')} but low precision {value(detector, 'precision')}, showing that the metric detector is sensitive enough to catch many anomaly windows but produces many false positives.",
            f"- The detector produced {value(detector, 'candidate_alerts')} candidates from {value(detector, 'evaluated_windows')} windows. This candidate volume is too large for direct external API judging in this thesis setup.",
            "- Detector behavior is uneven by domain. High-FPR domains such as `mongodb-machine-rps`, `mongodb-application-rps`, and `data-ingress-rate` explain much of the false-positive burden.",
            "- The key result collected from this dataset is the detector baseline: it quantifies how many metric windows become alert candidates before the experiment moves to Nezha for log/trace context and LLM judging.",
            "- Legacy mock LLM/RAG plumbing outputs may exist under `cloud_monitor_setup/outputs`, but they are intentionally excluded from this report because this dataset cannot support meaningful RAG evaluation.",
            "",
            "## 8. Thesis Usage Guidance",
            "",
            "- Use Microsoft cloud-monitoring-dataset in the report as the first metric-only feasibility dataset.",
            "- Use it to explain preprocessing, robust z-score/delta features, one-hour windowing, anomaly labels, detector recall, and false-positive burden.",
            "- Then transition to Nezha for the main hybrid RAG/LLM evaluation because Nezha provides logs/traces/fault labels.",
            "- Do not use this dataset for RAG/API evaluation, since it does not provide real operational log/trace evidence and generates too many candidates.",
            "",
            "## 9. Reproduction Commands",
            "",
            "```powershell",
            "py cloud_monitor_setup/prepare_cloud_monitor_data.py",
            "py experiments/run_baseline.py --config cloud_monitor_setup/config/experiment_current.yaml --mode detector_only",
            "py -B experiments/run_cloud_threshold_sweep.py",
            "py -B experiments/run_cloud_domain_analysis.py",
            "py -B scripts/summarize_cloud_monitoring_experiment.py",
            "```",
        ]
    )
    (REPORTS / "cloud_monitoring_experiment_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_csv_section(lines: list[str], title: str, path: Path, note: str) -> None:
    if not path.exists():
        return
    rows = read_csv(path)
    if not rows:
        return
    headers = list(rows[0].keys())
    lines.extend(
        [
            "",
            title,
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
    )
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    lines.extend(["", note])


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def value(row: dict[str, Any], key: str) -> str:
    raw = row.get(key, "")
    if isinstance(raw, float):
        return f"{raw:.4f}".rstrip("0").rstrip(".")
    return str(raw)


if __name__ == "__main__":
    main()
