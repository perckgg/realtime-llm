from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.time_utils import parse_timestamp


def load_metrics(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            row["timestamp"] = parse_timestamp(row["timestamp"])
            for key in row:
                if key not in {"timestamp", "node_id", "service_id", "label", "inject_type"}:
                    row[key] = float(row[key])
            records.append(row)
    return sorted(records, key=lambda item: item["timestamp"])
