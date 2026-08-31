from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.time_utils import isoformat, parse_timestamp


FEATURE_COLUMNS = [
    "cpu",
    "memory",
    "network",
    "latency",
    "workload",
    "success_rate_drop",
]

SERVICE_RE = re.compile(r"^(?P<service>.+?)(?:-[0-9a-f]{5,}|-[0-9]+)?(?:-[a-z0-9]{4,})?$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default="data/Nezha")
    parser.add_argument("--output-dir", default="nezha_setup/processed")
    parser.add_argument("--fault-before-seconds", type=int, default=60)
    parser.add_argument("--fault-after-seconds", type=int, default=360)
    parser.add_argument("--context-before-seconds", type=int, default=300)
    parser.add_argument("--context-after-seconds", type=int, default=600)
    parser.add_argument("--max-context-events-per-fault", type=int, default=80)
    parser.add_argument("--include-construct-data", action="store_true")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fault_windows = _load_fault_windows(
        dataset_root / "rca_data",
        before=timedelta(seconds=args.fault_before_seconds),
        after=timedelta(seconds=args.fault_after_seconds),
    )
    metric_rows, metric_summary = _convert_metrics(dataset_root / "rca_data", fault_windows)
    context_windows = _expand_fault_windows(
        fault_windows,
        before=timedelta(seconds=args.context_before_seconds),
        after=timedelta(seconds=args.context_after_seconds),
    )
    log_rows, log_summary = _convert_logs_and_traces(
        dataset_root / "rca_data",
        context_windows,
        max_events_per_fault=args.max_context_events_per_fault,
    )

    if args.include_construct_data:
        construct_logs, construct_summary = _convert_logs_and_traces(
            dataset_root / "construct_data",
            None,
            max_events_per_fault=args.max_context_events_per_fault,
        )
        log_rows.extend(construct_logs)
        log_summary["construct_context_events"] = construct_summary["context_events"]

    _write_csv(output_dir / "metrics.csv", metric_rows)
    _write_jsonl(output_dir / "logs.jsonl", log_rows)

    summary = {
        "dataset_root": str(dataset_root),
        "fault_count": sum(len(items) for items in fault_windows.values()),
        **metric_summary,
        **log_summary,
        "feature_columns": FEATURE_COLUMNS,
        "label_rule": {
            "same_pod": True,
            "before_seconds": args.fault_before_seconds,
            "after_seconds": args.fault_after_seconds,
        },
        "context_filter_rule": {
            "near_fault_windows": True,
            "before_seconds": args.context_before_seconds,
            "after_seconds": args.context_after_seconds,
            "max_context_events_per_fault_per_source": args.max_context_events_per_fault,
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _load_fault_windows(root: Path, before: timedelta, after: timedelta) -> dict[str, list[dict[str, Any]]]:
    windows: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(root.glob("*/*-fault_list.json")):
        day = path.parent.name
        payload = json.loads(path.read_text(encoding="utf-8"))
        day_windows: list[dict[str, Any]] = []
        for items in payload.values():
            for item in items:
                timestamp = datetime.fromtimestamp(int(item["inject_timestamp"]), tz=timezone.utc)
                pod_id = str(item["inject_pod"])
                day_windows.append(
                    {
                        "start": timestamp - before,
                        "end": timestamp + after,
                        "timestamp": timestamp,
                        "pod_id": pod_id,
                        "service_id": _service_from_pod(pod_id),
                        "inject_type": str(item["inject_type"]),
                    }
                )
        windows[day] = day_windows
    return windows


def _expand_fault_windows(
    fault_windows: dict[str, list[dict[str, Any]]],
    before: timedelta,
    after: timedelta,
) -> dict[str, list[dict[str, Any]]]:
    expanded: dict[str, list[dict[str, Any]]] = {}
    for day, windows in fault_windows.items():
        expanded[day] = [
            {
                "key": f"{day}-{index}-{window['pod_id']}-{window['inject_type']}",
                "start": window["timestamp"] - before,
                "end": window["timestamp"] + after,
                "pod_id": window["pod_id"],
                "service_id": window["service_id"],
            }
            for index, window in enumerate(windows)
        ]
    return expanded


def _convert_metrics(root: Path, fault_windows: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    files = 0
    skipped = 0
    labeled = 0
    for path in sorted(root.glob("*/metric/*_metric.csv")):
        day = path.parent.parent.name
        files += 1
        with path.open(newline="", encoding="utf-8-sig") as file:
            for raw in csv.DictReader(file):
                try:
                    timestamp = datetime.fromtimestamp(int(float(raw["TimeStamp"])), tz=timezone.utc)
                    pod_id = raw.get("PodName") or _pod_from_metric_path(path)
                    service_id = _service_from_pod(pod_id)
                    features = _metric_features(raw)
                except Exception:
                    skipped += 1
                    continue
                label, inject_type = _metric_label(timestamp, pod_id, fault_windows.get(day, []))
                if label == "true_alert":
                    labeled += 1
                rows.append(
                    {
                        "timestamp": isoformat(timestamp),
                        "node_id": pod_id,
                        "service_id": service_id,
                        **features,
                        "label": label,
                        "inject_type": inject_type,
                    }
                )
    return rows, {"metric_files": files, "metric_rows": len(rows), "metric_labeled_rows": labeled, "metric_skipped_rows": skipped}


def _metric_features(raw: dict[str, str]) -> dict[str, float]:
    network_receive = _float(raw.get("NetworkReceiveBytes"))
    network_transmit = _float(raw.get("NetworkTransmitBytes"))
    latency_seconds = max(
        _float(raw.get("PodClientLatencyP90(s)")),
        _float(raw.get("PodServerLatencyP90(s)")),
        _float(raw.get("PodClientLatencyP95(s)")),
        _float(raw.get("PodServerLatencyP95(s)")),
        _float(raw.get("PodClientLatencyP99(s)")),
        _float(raw.get("PodServerLatencyP99(s)")),
    )
    success_rate = _float(raw.get("PodSuccessRate(%)"), default=100.0)
    return {
        "cpu": _float(raw.get("CpuUsageRate(%)")),
        "memory": _float(raw.get("MemoryUsageRate(%)")),
        "network": network_receive + network_transmit,
        "latency": latency_seconds * 1000.0,
        "workload": _float(raw.get("PodWorkload(Ops)")),
        "success_rate_drop": max(0.0, 100.0 - success_rate),
    }


def _convert_logs_and_traces(
    root: Path,
    context_windows: dict[str, list[dict[str, Any]]] | None,
    max_events_per_fault: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events: list[dict[str, Any]] = []
    log_count = 0
    trace_count = 0
    kept_by_key: dict[tuple[str, str], int] = {}
    for path in sorted(root.glob("*/log/*_log.csv")):
        day = path.parent.parent.name
        with path.open(newline="", encoding="utf-8-sig") as file:
            for raw in csv.DictReader(file):
                event = _log_event(raw, day)
                if event is not None:
                    match_key = _context_match(event, day, context_windows)
                    if match_key is None:
                        continue
                    if not _allow_context_event(kept_by_key, match_key, "log", max_events_per_fault):
                        continue
                    events.append(event)
                    log_count += 1
    for path in sorted(root.glob("*/trace/*_trace.csv")):
        day = path.parent.parent.name
        with path.open(newline="", encoding="utf-8-sig") as file:
            for raw in csv.DictReader(file):
                event = _trace_event(raw, day)
                if event is not None:
                    match_key = _context_match(event, day, context_windows)
                    if match_key is None:
                        continue
                    if not _allow_context_event(kept_by_key, match_key, "trace", max_events_per_fault):
                        continue
                    events.append(event)
                    trace_count += 1
    return events, {"log_events": log_count, "trace_events": trace_count, "context_events": len(events)}


def _context_match(
    event: dict[str, Any],
    day: str,
    context_windows: dict[str, list[dict[str, Any]]] | None,
) -> str | None:
    if context_windows is None:
        return "construct"
    timestamp = parse_timestamp(event["timestamp"])
    for window in context_windows.get(day, []):
        same_service = event["service_id"] == window["service_id"]
        same_pod = event.get("pod_id") == window["pod_id"] or event.get("node_id") == window["pod_id"]
        if (same_service or same_pod) and window["start"] <= timestamp <= window["end"]:
            return str(window["key"])
    return None


def _allow_context_event(
    kept_by_key: dict[tuple[str, str], int],
    match_key: str,
    source: str,
    max_events_per_fault: int,
) -> bool:
    key = (match_key, source)
    count = kept_by_key.get(key, 0)
    if count >= max_events_per_fault:
        return False
    kept_by_key[key] = count + 1
    return True


def _log_event(raw: dict[str, str], day: str) -> dict[str, Any] | None:
    try:
        timestamp = parse_timestamp(raw["Timestamp"])
        pod_id = raw.get("PodName") or "unknown"
        service_id = _service_from_pod(pod_id)
        parsed = _parse_log_payload(raw.get("Log", ""))
        severity = str(parsed.get("severity") or "INFO").upper()
        message = str(parsed.get("message") or parsed.get("log") or raw.get("Log", ""))[:1000]
    except Exception:
        return None
    return {
        "doc_id": f"log-{day}-{raw.get('TraceID', '')}-{raw.get('SpanID', '')}-{raw.get('TimeUnixNano', '')}",
        "timestamp": isoformat(timestamp),
        "node_id": pod_id,
        "service_id": service_id,
        "pod_id": pod_id,
        "severity": severity,
        "event_type": "application_log",
        "source": "nezha_log",
        "message": message,
    }


def _trace_event(raw: dict[str, str], day: str) -> dict[str, Any] | None:
    try:
        start_ns = int(raw["StartTimeUnixNano"])
        end_ns = int(raw["EndTimeUnixNano"])
        timestamp = datetime.fromtimestamp(start_ns / 1_000_000_000, tz=timezone.utc)
        duration_ms = (end_ns - start_ns) / 1_000_000
        pod_id = raw.get("PodName") or "unknown"
        service_id = _service_from_pod(pod_id)
        operation = raw.get("OperationName", "unknown")
    except Exception:
        return None
    severity = "WARN" if duration_ms >= 1000 else "INFO"
    return {
        "doc_id": f"trace-{day}-{raw.get('TraceID', '')}-{raw.get('SpanID', '')}",
        "timestamp": isoformat(timestamp),
        "node_id": pod_id,
        "service_id": service_id,
        "pod_id": pod_id,
        "severity": severity,
        "event_type": "trace_span",
        "source": "nezha_trace",
        "message": f"Trace span {operation} on {pod_id} duration_ms={duration_ms:.3f}",
    }


def _parse_log_payload(value: str) -> dict[str, Any]:
    try:
        outer = json.loads(value)
        inner = outer.get("log", "")
        if isinstance(inner, str):
            return json.loads(inner.strip())
        if isinstance(inner, dict):
            return inner
    except Exception:
        return {}
    return {}


def _metric_label(timestamp: datetime, pod_id: str, windows: list[dict[str, Any]]) -> tuple[str, str]:
    for window in windows:
        if pod_id == window["pod_id"] and window["start"] <= timestamp <= window["end"]:
            return "true_alert", window["inject_type"]
    return "normal", "none"


def _pod_from_metric_path(path: Path) -> str:
    return path.name.removesuffix("_metric.csv")


def _service_from_pod(pod_id: str) -> str:
    pod_id = pod_id.removesuffix("_metric.csv")
    match = SERVICE_RE.match(pod_id)
    return match.group("service") if match else pod_id


def _float(value: str | None, default: float = 0.0) -> float:
    if value in {None, ""}:
        return default
    parsed = float(value)
    return parsed if math.isfinite(parsed) else default


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["timestamp", "node_id", "service_id", *FEATURE_COLUMNS, "inject_type", "label"]
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
