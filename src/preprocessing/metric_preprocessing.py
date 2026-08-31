from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from src.models import MetricWindow
from src.time_utils import isoformat


META_FIELDS = {"timestamp", "node_id", "service_id", "label", "inject_type"}


def create_metric_windows(
    records: list[dict[str, Any]],
    window_size_seconds: int,
    stride_seconds: int,
    normalization: str,
) -> list[MetricWindow]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["node_id"], record["service_id"])].append(record)

    windows: list[MetricWindow] = []
    for (node_id, service_id), group in groups.items():
        group = sorted(group, key=lambda item: item["timestamp"])
        if not group:
            continue
        start = group[0]["timestamp"]
        last = group[-1]["timestamp"]
        feature_names = [key for key in group[0] if key not in META_FIELDS]
        left = 0
        right = 0
        while start <= last:
            end = start + timedelta(seconds=window_size_seconds)
            while left < len(group) and group[left]["timestamp"] < start:
                left += 1
            while right < len(group) and group[right]["timestamp"] < end:
                right += 1
            rows = group[left:right]
            if rows:
                matrix = [[float(row[name]) for name in feature_names] for row in rows]
                features = normalize(matrix, normalization)
                label = _window_label([str(row.get("label", "normal")) for row in rows])
                fault_type = _window_fault_type([str(row.get("inject_type", "none")) for row in rows])
                windows.append(
                    MetricWindow(
                        window_id=f"{node_id}-{service_id}-{isoformat(start)}-{isoformat(end)}",
                        start_time=start,
                        end_time=end,
                        node_id=node_id,
                        service_id=service_id,
                        features=features,
                        feature_names=feature_names,
                        label=label,
                        fault_type=fault_type,
                        raw_features=matrix,
                    )
                )
            start = start + timedelta(seconds=stride_seconds)
    return windows


def normalize(matrix: list[list[float]], method: str) -> list[list[float]]:
    if not matrix:
        return []
    columns = list(zip(*matrix))
    normalized_columns: list[list[float]] = []
    for column in columns:
        values = list(column)
        if method == "minmax":
            low = min(values)
            high = max(values)
            denom = high - low or 1.0
            normalized_columns.append([(value - low) / denom for value in values])
        else:
            mean = statistics.fmean(values)
            stdev = statistics.pstdev(values) or 1.0
            normalized_columns.append([(value - mean) / stdev for value in values])
    return [list(row) for row in zip(*normalized_columns)]


def raw_metric_snapshot(window: MetricWindow) -> dict[str, float]:
    source = window.raw_features or window.features
    if not source:
        return {}
    last_row = source[-1]
    return {name: round(value, 4) for name, value in zip(window.feature_names, last_row)}


def _window_label(labels: list[str]) -> str:
    counts = Counter(labels)
    if counts.get("true_alert", 0) > 0:
        return "true_alert"
    if counts.get("false_positive", 0) > 0:
        return "false_positive"
    return "normal"


def _window_fault_type(fault_types: list[str]) -> str:
    candidates = [fault_type for fault_type in fault_types if fault_type and fault_type != "none"]
    if not candidates:
        return "none"
    counts = Counter(candidates)
    return counts.most_common(1)[0][0]
