from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.detectors.factory import build_detector
from src.ingestion.metric_loader import load_metrics
from src.models import MetricWindow
from src.preprocessing.metric_preprocessing import create_metric_windows


OUTPUT_COLUMNS = [
    "Domain",
    "Windows",
    "Candidates",
    "Precision",
    "Recall",
    "F1",
    "FPR",
    "FP",
    "FN",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Cloud Monitoring detector behavior by metric domain.")
    parser.add_argument("--config", default="cloud_monitor_setup/config/experiment_current.yaml")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--output-csv", default="reports/cloud_monitoring_domain_analysis.csv")
    parser.add_argument("--output-md", default="reports/cloud_monitoring_domain_analysis.md")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.threshold is not None:
        config = dict(config)
        config["detector"] = dict(config.get("detector", {}))
        config["detector"]["threshold"] = args.threshold

    records = load_metrics(config["data"]["metric_path"])
    windows = create_metric_windows(
        records,
        int(config["preprocessing"]["window_size"]),
        int(config["preprocessing"]["stride"]),
        str(config["preprocessing"]["normalization"]),
    )
    detector = build_detector(config.get("detector", {}), windows)

    rows = evaluate_domains(windows, detector)
    threshold = float(config.get("detector", {}).get("threshold", 0.0))
    write_csv(Path(args.output_csv), rows)
    write_markdown(Path(args.output_md), rows, threshold)
    print_table(rows)
    print(f"threshold={threshold:.2f}")
    print(f"wrote {args.output_csv} and {args.output_md}")


def evaluate_domains(windows: list[MetricWindow], detector: Any) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    for window in windows:
        predicted = detector.score(window).is_candidate
        truth = window.label == "true_alert"
        grouped[window.service_id].append((truth, predicted))

    rows = []
    for domain, decisions in sorted(grouped.items()):
        rows.append(summarize_domain(domain, decisions))
    return rows


def summarize_domain(domain: str, decisions: list[tuple[bool, bool]]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for truth, predicted in decisions:
        if truth and predicted:
            tp += 1
        elif not truth and predicted:
            fp += 1
        elif not truth and not predicted:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "Domain": domain,
        "Windows": len(decisions),
        "Candidates": tp + fp,
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1": round(f1, 4),
        "FPR": round(fpr, 4),
        "FP": fp,
        "FN": fn,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]], threshold: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Microsoft Cloud Monitoring Domain Analysis",
        "",
        f"Detector-only threshold: `{threshold:.2f}`",
        "",
        "| " + " | ".join(OUTPUT_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in OUTPUT_COLUMNS) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[column]) for column in OUTPUT_COLUMNS) + " |")
    lines.extend(
        [
            "",
            "Domains with no positive anomaly windows use `0.0` recall/F1 by denominator convention; use them only to inspect false-positive behavior.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_table(rows: list[dict[str, Any]]) -> None:
    print("\t".join(OUTPUT_COLUMNS))
    for row in rows:
        print("\t".join(str(row[column]) for column in OUTPUT_COLUMNS))


if __name__ == "__main__":
    main()
