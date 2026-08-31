from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.detectors.factory import build_detector
from src.ingestion.metric_loader import load_metrics
from src.preprocessing.metric_preprocessing import create_metric_windows


DEFAULT_THRESHOLDS = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
OUTPUT_COLUMNS = [
    "Threshold",
    "Windows",
    "Candidates",
    "Precision",
    "Recall",
    "F1",
    "FPR",
    "TP",
    "FP",
    "FN",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run detector threshold sweep on Microsoft cloud monitoring data.")
    parser.add_argument("--config", default="cloud_monitor_setup/config/experiment_current.yaml")
    parser.add_argument("--output-csv", default="reports/cloud_monitoring_threshold_sweep.csv")
    parser.add_argument("--output-md", default="reports/cloud_monitoring_threshold_sweep.md")
    parser.add_argument("--thresholds", nargs="+", type=float, default=DEFAULT_THRESHOLDS)
    args = parser.parse_args()

    config = load_config(args.config)
    records = load_metrics(config["data"]["metric_path"])
    windows = create_metric_windows(
        records,
        int(config["preprocessing"]["window_size"]),
        int(config["preprocessing"]["stride"]),
        str(config["preprocessing"]["normalization"]),
    )

    rows = [evaluate_threshold(config, windows, threshold) for threshold in args.thresholds]
    write_csv(Path(args.output_csv), rows)
    write_markdown(Path(args.output_md), rows)
    print_table(rows)
    print(f"wrote {args.output_csv} and {args.output_md}")


def evaluate_threshold(config: dict[str, Any], windows: list[Any], threshold: float) -> dict[str, Any]:
    detector_config = dict(config.get("detector", {}))
    detector_config["threshold"] = threshold
    detector = build_detector(detector_config, windows)

    tp = fp = tn = fn = 0
    for window in windows:
        predicted = detector.score(window).is_candidate
        truth = window.label == "true_alert"
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
        "Threshold": f"{threshold:.2f}",
        "Windows": len(windows),
        "Candidates": tp + fp,
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1": round(f1, 4),
        "FPR": round(fpr, 4),
        "TP": tp,
        "FP": fp,
        "FN": fn,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Microsoft Cloud Monitoring Detector Threshold Sweep",
        "",
        "| " + " | ".join(OUTPUT_COLUMNS) + " |",
        "| " + " | ".join("---" for _ in OUTPUT_COLUMNS) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[column]) for column in OUTPUT_COLUMNS) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_table(rows: list[dict[str, Any]]) -> None:
    print("\t".join(OUTPUT_COLUMNS))
    for row in rows:
        print("\t".join(str(row[column]) for column in OUTPUT_COLUMNS))


if __name__ == "__main__":
    main()
