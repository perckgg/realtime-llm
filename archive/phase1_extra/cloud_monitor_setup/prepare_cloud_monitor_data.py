from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.time_utils import isoformat, parse_timestamp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default="data/cloud-monitoring-dataset/data")
    parser.add_argument("--output-dir", default="cloud_monitor_setup/processed")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metric_rows: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []
    summary = {
        "dataset_root": str(dataset_root),
        "series_count": 0,
        "point_count": 0,
        "anomaly_point_count": 0,
        "skipped_point_count": 0,
        "domains": {},
    }

    for csv_path in sorted(dataset_root.rglob("*.csv")):
        domain = csv_path.parent.name
        series_id = csv_path.stem
        rows, skipped_count = _read_series(csv_path)
        if not rows:
            continue
        values = [row["value"] for row in rows]
        deltas = [0.0]
        deltas.extend(abs(values[index] - values[index - 1]) for index in range(1, len(values)))
        value_scores = _robust_zscores(values)
        delta_scores = _robust_zscores(deltas)

        for row, value_z, delta_z in zip(rows, value_scores, delta_scores):
            label = "true_alert" if row["label"] == 1 else "normal"
            metric_rows.append(
                {
                    "timestamp": isoformat(row["timestamp"]),
                    "node_id": series_id,
                    "service_id": domain,
                    "value": row["value"],
                    "value_z": round(value_z, 6),
                    "abs_delta_z": round(delta_z, 6),
                    "label": label,
                }
            )

        anomaly_count = sum(1 for row in rows if row["label"] == 1)
        summary["series_count"] += 1
        summary["point_count"] += len(rows)
        summary["skipped_point_count"] += skipped_count
        summary["anomaly_point_count"] += anomaly_count
        domain_summary = summary["domains"].setdefault(
            domain,
            {"series_count": 0, "point_count": 0, "anomaly_point_count": 0, "skipped_point_count": 0},
        )
        domain_summary["series_count"] += 1
        domain_summary["point_count"] += len(rows)
        domain_summary["anomaly_point_count"] += anomaly_count
        domain_summary["skipped_point_count"] += skipped_count

        log_rows.append(_metadata_context(csv_path, rows[0]["timestamp"], domain, series_id))

    _write_metrics(output_dir / "metrics.csv", metric_rows)
    _write_jsonl(output_dir / "logs.jsonl", log_rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _read_series(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    skipped_count = 0
    with path.open(newline="", encoding="utf-8-sig") as file:
        for raw in csv.DictReader(file):
            if not raw.get("TimeStamp") or not raw.get("Value") or not raw.get("Label"):
                skipped_count += 1
                continue
            rows.append(
                {
                    "timestamp": parse_timestamp(raw["TimeStamp"].strip('"')),
                    "value": float(raw["Value"]),
                    "label": int(raw["Label"]),
                }
            )
    return sorted(rows, key=lambda row: row["timestamp"]), skipped_count


def _robust_zscores(values: list[float]) -> list[float]:
    if not values:
        return []
    median = statistics.median(values)
    deviations = [abs(value - median) for value in values]
    mad = statistics.median(deviations)
    scale = 1.4826 * mad
    if scale == 0:
        scale = statistics.pstdev(values) or 1.0
    return [(value - median) / scale for value in values]


def _metadata_context(csv_path: Path, timestamp, domain: str, series_id: str) -> dict[str, Any]:
    metadata_path = csv_path.with_name(f"{csv_path.name}-metadata.json")
    notes: list[str] = []
    description = ""
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        raw_notes = metadata.get("notes", [])
        notes = [str(note) for note in raw_notes]
        description = str(metadata.get("schema:description", ""))
    message = " ".join(part for part in [description, *notes] if part).strip()
    if not message:
        message = f"Microsoft cloud monitoring time series metadata for {domain}/{series_id}."
    return {
        "timestamp": isoformat(timestamp),
        "node_id": series_id,
        "service_id": domain,
        "pod_id": "",
        "severity": "INFO",
        "event_type": "dataset_metadata",
        "source": "metadata",
        "message": message,
    }


def _write_metrics(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["timestamp", "node_id", "service_id", "value", "value_z", "abs_delta_z", "label"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
