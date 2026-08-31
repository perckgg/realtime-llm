from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SERVICE_RE = re.compile(r"^(?P<service>.+?)(?:-[0-9a-f]{5,}|-[0-9]+)?(?:-[a-z0-9]{4,})?$")

NEZHA_FEATURE_COLUMNS = [
    "cpu",
    "memory",
    "network",
    "latency",
    "workload",
    "success_rate_drop",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the monitoring datasets used by the experiments.")
    parser.add_argument("--cloud-root", default="data/cloud-monitoring-dataset")
    parser.add_argument("--nezha-root", default="data/Nezha")
    parser.add_argument("--cloud-processed", default="cloud_monitor_setup/processed")
    parser.add_argument("--nezha-processed", default="nezha_setup/processed")
    parser.add_argument("--output-dir", default="outputs/dataset_analysis")
    parser.add_argument("--report-path", default="DATASET_REPORT.md")
    parser.add_argument(
        "--count-raw-event-rows",
        action="store_true",
        help="Count every raw Nezha log/trace/traceid row. This is slower on the full dataset.",
    )
    args = parser.parse_args()

    cloud_root = Path(args.cloud_root)
    nezha_root = Path(args.nezha_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cloud_monitoring": analyze_cloud_monitoring(cloud_root, Path(args.cloud_processed)),
        "nezha": analyze_nezha(nezha_root, Path(args.nezha_processed), count_raw_event_rows=args.count_raw_event_rows),
    }

    summary_path = output_dir / "dataset_analysis_summary.json"
    summary_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    report = render_report(analysis, summary_path)
    report_path = Path(args.report_path)
    report_path.write_text(report, encoding="utf-8")

    print(json.dumps({"summary": str(summary_path), "report": str(report_path)}, indent=2))


def analyze_cloud_monitoring(root: Path, processed_dir: Path) -> dict[str, Any]:
    data_root = root / "data" if (root / "data").exists() else root
    csv_paths = sorted(data_root.rglob("*.csv"))
    metadata_paths = sorted(data_root.rglob("*.csv-metadata.json"))

    domains: dict[str, dict[str, Any]] = {}
    overall = {
        "series_count": 0,
        "point_count": 0,
        "anomaly_point_count": 0,
        "skipped_point_count": 0,
        "value_count": 0,
        "value_sum": 0.0,
        "value_min": None,
        "value_max": None,
        "first_timestamp": None,
        "last_timestamp": None,
    }
    metadata_notes: list[str] = []

    for metadata_path in metadata_paths:
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for note in payload.get("notes", []):
            note_text = str(note).strip()
            if note_text and note_text not in metadata_notes:
                metadata_notes.append(note_text)

    for csv_path in csv_paths:
        domain = csv_path.parent.name
        domain_summary = domains.setdefault(
            domain,
            {
                "series_count": 0,
                "point_count": 0,
                "anomaly_point_count": 0,
                "skipped_point_count": 0,
                "value_count": 0,
                "value_sum": 0.0,
                "value_min": None,
                "value_max": None,
                "first_timestamp": None,
                "last_timestamp": None,
            },
        )
        series_stats = read_cloud_series(csv_path)
        merge_cloud_stats(overall, series_stats)
        merge_cloud_stats(domain_summary, series_stats)
        overall["series_count"] += 1
        domain_summary["series_count"] += 1

    for summary in [overall, *domains.values()]:
        summary["anomaly_rate"] = safe_ratio(summary["anomaly_point_count"], summary["point_count"])
        summary["value_mean"] = safe_ratio(summary["value_sum"], summary["value_count"])
        summary["first_timestamp"] = format_datetime(summary["first_timestamp"])
        summary["last_timestamp"] = format_datetime(summary["last_timestamp"])
        summary.pop("value_sum", None)
        summary.pop("value_count", None)

    processed_summary = load_json(processed_dir / "summary.json")
    return {
        "raw_root": str(root),
        "data_root": str(data_root),
        "inventory": file_inventory(root),
        "csv_files": len(csv_paths),
        "metadata_files": len(metadata_paths),
        "summary": overall,
        "domains": domains,
        "metadata_note_examples": metadata_notes[:6],
        "processed": analyze_processed_dataset(processed_dir),
        "processed_summary": processed_summary,
        "fit_for_experiment": [
            "Detector baseline and anomaly scoring",
            "Alert candidate generation from labeled time-series points",
            "Limited RAG/LLM evaluation because the dataset has metadata notes but no operational logs or traces",
        ],
    }


def read_cloud_series(path: Path) -> dict[str, Any]:
    stats = {
        "point_count": 0,
        "anomaly_point_count": 0,
        "skipped_point_count": 0,
        "value_count": 0,
        "value_sum": 0.0,
        "value_min": None,
        "value_max": None,
        "first_timestamp": None,
        "last_timestamp": None,
    }
    with path.open(newline="", encoding="utf-8-sig") as file:
        for raw in csv.DictReader(file):
            try:
                timestamp = parse_datetime(raw.get("TimeStamp", ""))
                value = float(raw.get("Value", ""))
                label = int(raw.get("Label", ""))
            except Exception:
                stats["skipped_point_count"] += 1
                continue
            stats["point_count"] += 1
            stats["anomaly_point_count"] += 1 if label == 1 else 0
            update_range(stats, "value", value)
            update_time_range(stats, timestamp)
    return stats


def merge_cloud_stats(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in ["point_count", "anomaly_point_count", "skipped_point_count", "value_count"]:
        target[key] += source[key]
    target["value_sum"] += source["value_sum"]
    merge_minmax(target, source, "value")
    merge_time_range(target, source)


def analyze_nezha(root: Path, processed_dir: Path, count_raw_event_rows: bool) -> dict[str, Any]:
    rca_root = root / "rca_data"
    construct_root = root / "construct_data"
    fault_windows = load_fault_windows(rca_root, before=timedelta(seconds=60), after=timedelta(seconds=360))
    fault_summary = summarize_faults(fault_windows)
    raw_metric_summary = summarize_nezha_raw_metrics(rca_root, fault_windows)
    raw_event_summary = summarize_nezha_event_files(root, count_rows=count_raw_event_rows)
    processed = analyze_processed_dataset(processed_dir)
    processed_details = analyze_nezha_processed(processed_dir)

    return {
        "raw_root": str(root),
        "inventory": file_inventory(root),
        "date_partitions": {
            "rca_data": sorted(path.name for path in rca_root.iterdir() if path.is_dir()) if rca_root.exists() else [],
            "construct_data": sorted(path.name for path in construct_root.iterdir() if path.is_dir()) if construct_root.exists() else [],
        },
        "faults": fault_summary,
        "raw_metrics": raw_metric_summary,
        "raw_events": raw_event_summary,
        "processed": processed,
        "processed_details": processed_details,
        "fit_for_experiment": [
            "Hybrid monitoring with metric detector + log/trace context retrieval",
            "LLM-as-a-Judge and local-first/API-fallback routing",
            "Ablation, streaming replay, context rescue, and retrieval-quality analysis",
        ],
    }


def load_fault_windows(root: Path, before: timedelta, after: timedelta) -> dict[str, list[dict[str, Any]]]:
    windows: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(root.glob("*/*-fault_list.json")):
        day = path.parent.name
        payload = load_json(path)
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
                        "service_id": service_from_pod(pod_id),
                        "inject_type": str(item["inject_type"]),
                    }
                )
        windows[day] = day_windows
    return windows


def summarize_faults(fault_windows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_day: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    by_service: Counter[str] = Counter()
    by_pod: Counter[str] = Counter()
    first_timestamp = None
    last_timestamp = None
    for day, windows in fault_windows.items():
        by_day[day] += len(windows)
        for window in windows:
            by_type[window["inject_type"]] += 1
            by_service[window["service_id"]] += 1
            by_pod[window["pod_id"]] += 1
            first_timestamp, last_timestamp = minmax_datetime(first_timestamp, last_timestamp, window["timestamp"])
    return {
        "fault_count": sum(by_day.values()),
        "by_day": dict(sorted(by_day.items())),
        "by_inject_type": dict(by_type.most_common()),
        "top_services": dict(by_service.most_common(12)),
        "top_pods": dict(by_pod.most_common(12)),
        "first_timestamp": format_datetime(first_timestamp),
        "last_timestamp": format_datetime(last_timestamp),
        "label_window": {"same_pod": True, "before_seconds": 60, "after_seconds": 360},
    }


def summarize_nezha_raw_metrics(root: Path, fault_windows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    files = sorted(root.glob("*/metric/*_metric.csv"))
    summary = {
        "metric_files": len(files),
        "metric_rows": 0,
        "metric_labeled_rows": 0,
        "metric_skipped_rows": 0,
        "services": Counter(),
        "pods": Counter(),
        "feature_stats": {
            "cpu": numeric_stats(),
            "memory": numeric_stats(),
            "network": numeric_stats(),
            "latency": numeric_stats(),
            "workload": numeric_stats(),
            "success_rate_drop": numeric_stats(),
        },
        "first_timestamp": None,
        "last_timestamp": None,
    }
    for path in files:
        day = path.parent.parent.name
        with path.open(newline="", encoding="utf-8-sig") as file:
            for raw in csv.DictReader(file):
                try:
                    timestamp = datetime.fromtimestamp(int(float(raw["TimeStamp"])), tz=timezone.utc)
                    pod_id = raw.get("PodName") or path.name.removesuffix("_metric.csv")
                    service_id = service_from_pod(pod_id)
                    features = nezha_metric_features(raw)
                except Exception:
                    summary["metric_skipped_rows"] += 1
                    continue
                summary["metric_rows"] += 1
                summary["services"][service_id] += 1
                summary["pods"][pod_id] += 1
                summary["metric_labeled_rows"] += 1 if in_fault_window(timestamp, pod_id, fault_windows.get(day, [])) else 0
                summary["first_timestamp"], summary["last_timestamp"] = minmax_datetime(
                    summary["first_timestamp"], summary["last_timestamp"], timestamp
                )
                for key, value in features.items():
                    update_numeric_stats(summary["feature_stats"][key], value)

    return {
        "metric_files": summary["metric_files"],
        "metric_rows": summary["metric_rows"],
        "metric_labeled_rows": summary["metric_labeled_rows"],
        "metric_label_rate": safe_ratio(summary["metric_labeled_rows"], summary["metric_rows"]),
        "metric_skipped_rows": summary["metric_skipped_rows"],
        "service_count": len(summary["services"]),
        "pod_count": len(summary["pods"]),
        "top_services_by_rows": dict(summary["services"].most_common(12)),
        "top_pods_by_rows": dict(summary["pods"].most_common(12)),
        "feature_stats": {key: finalize_numeric_stats(value) for key, value in summary["feature_stats"].items()},
        "first_timestamp": format_datetime(summary["first_timestamp"]),
        "last_timestamp": format_datetime(summary["last_timestamp"]),
    }


def summarize_nezha_event_files(root: Path, count_rows: bool) -> dict[str, Any]:
    groups = {
        "rca_log": root / "rca_data" / "*" / "log" / "*_log.csv",
        "rca_trace": root / "rca_data" / "*" / "trace" / "*_trace.csv",
        "rca_traceid": root / "rca_data" / "*" / "traceid" / "*_traceid.csv",
        "construct_log": root / "construct_data" / "*" / "log" / "*_log.csv",
        "construct_trace": root / "construct_data" / "*" / "trace" / "*_trace.csv",
        "construct_traceid": root / "construct_data" / "*" / "traceid" / "*_traceid.csv",
    }
    result: dict[str, Any] = {}
    for name, pattern_path in groups.items():
        files = sorted(root.glob(str(pattern_path.relative_to(root))))
        bytes_total = sum(path.stat().st_size for path in files)
        item = {"files": len(files), "bytes": bytes_total, "mb": round(bytes_total / 1_048_576, 3)}
        if count_rows:
            item["rows"] = sum(count_csv_rows(path) for path in files)
        result[name] = item
    result["raw_event_rows_counted"] = count_rows
    return result


def analyze_processed_dataset(processed_dir: Path) -> dict[str, Any]:
    metrics_path = processed_dir / "metrics.csv"
    logs_path = processed_dir / "logs.jsonl"
    summary_path = processed_dir / "summary.json"
    return {
        "path": str(processed_dir),
        "exists": processed_dir.exists(),
        "summary": load_json(summary_path) if summary_path.exists() else {},
        "metrics": summarize_csv_file(metrics_path),
        "logs": summarize_jsonl_file(logs_path),
    }


def analyze_nezha_processed(processed_dir: Path) -> dict[str, Any]:
    metrics_path = processed_dir / "metrics.csv"
    logs_path = processed_dir / "logs.jsonl"
    labels: Counter[str] = Counter()
    inject_types: Counter[str] = Counter()
    services: Counter[str] = Counter()
    event_types: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    if metrics_path.exists():
        with metrics_path.open(newline="", encoding="utf-8-sig") as file:
            for row in csv.DictReader(file):
                labels[str(row.get("label", ""))] += 1
                inject_types[str(row.get("inject_type", ""))] += 1
                services[str(row.get("service_id", ""))] += 1
    if logs_path.exists():
        with logs_path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                event_types[str(row.get("event_type", ""))] += 1
                sources[str(row.get("source", ""))] += 1
                severities[str(row.get("severity", ""))] += 1
    return {
        "metric_labels": dict(labels.most_common()),
        "metric_inject_types": dict(inject_types.most_common()),
        "metric_top_services": dict(services.most_common(12)),
        "context_event_types": dict(event_types.most_common()),
        "context_sources": dict(sources.most_common()),
        "context_severities": dict(severities.most_common()),
    }


def summarize_csv_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        rows = sum(1 for _ in reader)
    return {"exists": True, "rows": rows, "columns": columns, "bytes": path.stat().st_size}


def summarize_jsonl_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    rows = 0
    keys: Counter[str] = Counter()
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            rows += 1
            try:
                payload = json.loads(line)
            except Exception:
                continue
            keys.update(payload.keys())
    return {"exists": True, "rows": rows, "keys": list(keys.keys()), "bytes": path.stat().st_size}


def file_inventory(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    files = [path for path in root.rglob("*") if path.is_file()]
    by_suffix: Counter[str] = Counter(path.suffix.lower() or "<none>" for path in files)
    bytes_total = sum(path.stat().st_size for path in files)
    return {
        "exists": True,
        "file_count": len(files),
        "bytes": bytes_total,
        "mb": round(bytes_total / 1_048_576, 3),
        "by_suffix": dict(by_suffix.most_common()),
    }


def render_report(analysis: dict[str, Any], summary_path: Path) -> str:
    cloud = analysis["cloud_monitoring"]
    nezha = analysis["nezha"]
    cloud_summary = cloud["summary"]
    cloud_processed = cloud["processed"]["summary"]
    nezha_faults = nezha["faults"]
    nezha_metrics = nezha["raw_metrics"]
    nezha_processed_summary = nezha["processed"]["summary"]

    sections = [
        "# Dataset Analysis Report",
        "",
        f"Generated at: `{analysis['generated_at']}`",
        f"Machine-readable summary: `{summary_path.as_posix()}`",
        "",
        "## 1. Scope",
        "",
        "Report này phân tích 2 dataset đang dùng trong thí nghiệm hybrid monitoring:",
        "",
        "- Microsoft `cloud-monitoring-dataset`: time-series metric có nhãn anomaly.",
        "- `IntelligentDDS/Nezha`: metric, log, trace, traceid và danh sách fault injection.",
        "",
        "## 2. High-level comparison",
        "",
        markdown_table(
            ["Dataset", "Raw focus", "Processed rows", "Positive labels/events", "Vai trò tốt nhất"],
            [
                [
                    "Microsoft cloud-monitoring",
                    f"{cloud['csv_files']} series CSV, {cloud['metadata_files']} metadata files",
                    fmt_int(cloud_processed.get("point_count", cloud_summary["point_count"])),
                    fmt_int(cloud_processed.get("anomaly_point_count", cloud_summary["anomaly_point_count"])),
                    "Detector baseline, anomaly scoring, alert candidate generation",
                ],
                [
                    "Nezha",
                    f"{nezha_metrics['metric_files']} metric CSV + log/trace files",
                    fmt_int(nezha_processed_summary.get("metric_rows", nezha_metrics["metric_rows"])),
                    fmt_int(nezha_processed_summary.get("context_events", 0)),
                    "Hybrid metric + RAG + LLM judge, streaming replay, context rescue",
                ],
            ],
        ),
        "",
        "## 3. Microsoft cloud-monitoring-dataset",
        "",
        f"Raw path: `{cloud['data_root']}`",
        "",
        markdown_table(
            ["Metric", "Value"],
            [
                ["Series CSV", fmt_int(cloud["csv_files"])],
                ["Metadata JSON", fmt_int(cloud["metadata_files"])],
                ["Valid points", fmt_int(cloud_summary["point_count"])],
                ["Anomaly points", fmt_int(cloud_summary["anomaly_point_count"])],
                ["Anomaly rate", fmt_pct(cloud_summary["anomaly_rate"])],
                ["Skipped points", fmt_int(cloud_summary["skipped_point_count"])],
                ["Time range", f"{cloud_summary['first_timestamp']} -> {cloud_summary['last_timestamp']}"],
                ["Value min / mean / max", f"{fmt_float(cloud_summary['value_min'])} / {fmt_float(cloud_summary['value_mean'])} / {fmt_float(cloud_summary['value_max'])}"],
            ],
        ),
        "",
        "Domain breakdown:",
        "",
        markdown_table(
            ["Domain", "Series", "Points", "Anomalies", "Anomaly rate"],
            [
                [
                    domain,
                    fmt_int(item["series_count"]),
                    fmt_int(item["point_count"]),
                    fmt_int(item["anomaly_point_count"]),
                    fmt_pct(item["anomaly_rate"]),
                ]
                for domain, item in sorted(cloud["domains"].items())
            ],
        ),
        "",
        "Nhận xét:",
        "",
        "- Dataset này mạnh ở phần time-series anomaly detection vì mỗi điểm metric đã có label.",
        "- Context dùng cho RAG chỉ đến từ metadata notes, không phải log/trace vận hành thật.",
        "- Vì vậy dataset này phù hợp để đo detector, threshold, false positive reduction sơ bộ; không nên là dataset chính để đánh giá khả năng giải thích RCA bằng LLM.",
        "",
        "## 4. Nezha Dataset",
        "",
        f"Raw path: `{nezha['raw_root']}`",
        "",
        markdown_table(
            ["Metric", "Value"],
            [
                ["RCA date partitions", ", ".join(nezha["date_partitions"]["rca_data"])],
                ["Construct date partitions", ", ".join(nezha["date_partitions"]["construct_data"])],
                ["Fault count", fmt_int(nezha_faults["fault_count"])],
                ["Fault time range", f"{nezha_faults['first_timestamp']} -> {nezha_faults['last_timestamp']}"],
                ["Raw metric files", fmt_int(nezha_metrics["metric_files"])],
                ["Raw metric rows", fmt_int(nezha_metrics["metric_rows"])],
                ["Metric rows inside fault windows", fmt_int(nezha_metrics["metric_labeled_rows"])],
                ["Metric positive rate", fmt_pct(nezha_metrics["metric_label_rate"])],
                ["Services / pods", f"{fmt_int(nezha_metrics['service_count'])} / {fmt_int(nezha_metrics['pod_count'])}"],
            ],
        ),
        "",
        "Fault injection breakdown:",
        "",
        markdown_table(
            ["Inject type", "Faults"],
            [[key, fmt_int(value)] for key, value in nezha_faults["by_inject_type"].items()],
        ),
        "",
        "Processed data đang được pipeline dùng:",
        "",
        markdown_table(
            ["Artifact", "Rows", "Schema"],
            [
                [
                    "metrics.csv",
                    fmt_int(nezha["processed"]["metrics"].get("rows", 0)),
                    ", ".join(nezha["processed"]["metrics"].get("columns", [])),
                ],
                [
                    "logs.jsonl",
                    fmt_int(nezha["processed"]["logs"].get("rows", 0)),
                    ", ".join(nezha["processed"]["logs"].get("keys", [])),
                ],
            ],
        ),
        "",
        "Processed label/context breakdown:",
        "",
        markdown_table(
            ["Group", "Distribution"],
            [
                ["Metric labels", inline_dict(nezha["processed_details"]["metric_labels"])],
                ["Inject types", inline_dict(nezha["processed_details"]["metric_inject_types"])],
                ["Context event types", inline_dict(nezha["processed_details"]["context_event_types"])],
                ["Context sources", inline_dict(nezha["processed_details"]["context_sources"])],
                ["Context severities", inline_dict(nezha["processed_details"]["context_severities"])],
            ],
        ),
        "",
        "Nhận xét:",
        "",
        "- Nezha là dataset sát kiến trúc nghiên cứu nhất vì có đủ metric, fault list, log và trace.",
        "- Nhãn `true_alert` hiện được tạo từ fault injection theo cùng pod trong cửa sổ -60s đến +360s.",
        "- Context RAG hiện là log/trace được lọc quanh fault window, giới hạn tối đa theo fault/source để tránh prompt quá dài.",
        "- Tỷ lệ positive metric thấp, nên detector và gate cần được đánh giá kỹ bằng recall/FPR thay vì chỉ accuracy.",
        "",
        "## 5. Current data flow in this repo",
        "",
        "```text",
        "Raw dataset",
        "  -> prepare_cloud_monitor_data.py / prepare_nezha_data.py",
        "  -> processed metrics.csv + logs.jsonl + summary.json",
        "  -> src preprocessing + detector",
        "  -> alert candidates",
        "  -> retriever over logs/context",
        "  -> local-first/API fallback LLM judge",
        "  -> audit + evaluation report",
        "```",
        "",
        "## 6. Recommendations",
        "",
        "- Dùng Nezha làm dataset chính cho các phase hybrid, RAG, local-first LLM judge và streaming replay.",
        "- Dùng Microsoft cloud-monitoring để kiểm tra detector baseline, calibration threshold và stress test nhiều time series.",
        "- Với Nezha, nên tiếp tục thêm báo cáo coverage: candidate có lấy đúng context gần fault không, và API fallback có cải thiện decision ở nhóm `uncertain` không.",
        "- Nếu cần benchmark lớn hơn, chạy script này với `--count-raw-event-rows` để thống kê đầy đủ raw log/trace rows; mặc định report ưu tiên nhanh và tập trung vào dữ liệu processed thật sự đang dùng.",
        "",
        "## 7. Re-run",
        "",
        "```powershell",
        "py experiments/analyze_datasets.py",
        "```",
        "",
        "Optional full raw row count:",
        "",
        "```powershell",
        "py experiments/analyze_datasets.py --count-raw-event-rows",
        "```",
        "",
    ]
    return "\n".join(sections)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(escape_md(str(value)) for value in row) + " |")
    return "\n".join(lines)


def escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def inline_dict(value: dict[str, Any], limit: int = 8) -> str:
    items = list(value.items())[:limit]
    return ", ".join(f"{key}={fmt_int(val) if isinstance(val, int) else val}" for key, val in items) or "n/a"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_datetime(value: str) -> datetime:
    text = value.strip().strip('"')
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def update_range(stats: dict[str, Any], prefix: str, value: float) -> None:
    if not math.isfinite(value):
        return
    stats[f"{prefix}_count"] += 1
    stats[f"{prefix}_sum"] += value
    current_min = stats[f"{prefix}_min"]
    current_max = stats[f"{prefix}_max"]
    stats[f"{prefix}_min"] = value if current_min is None else min(current_min, value)
    stats[f"{prefix}_max"] = value if current_max is None else max(current_max, value)


def update_time_range(stats: dict[str, Any], timestamp: datetime) -> None:
    first, last = minmax_datetime(stats["first_timestamp"], stats["last_timestamp"], timestamp)
    stats["first_timestamp"] = first
    stats["last_timestamp"] = last


def merge_minmax(target: dict[str, Any], source: dict[str, Any], prefix: str) -> None:
    for suffix, reducer in [("min", min), ("max", max)]:
        key = f"{prefix}_{suffix}"
        if source[key] is None:
            continue
        target[key] = source[key] if target[key] is None else reducer(target[key], source[key])


def merge_time_range(target: dict[str, Any], source: dict[str, Any]) -> None:
    first = source["first_timestamp"]
    last = source["last_timestamp"]
    if first is not None:
        target["first_timestamp"] = first if target["first_timestamp"] is None else min(target["first_timestamp"], first)
    if last is not None:
        target["last_timestamp"] = last if target["last_timestamp"] is None else max(target["last_timestamp"], last)


def minmax_datetime(first: datetime | None, last: datetime | None, value: datetime) -> tuple[datetime, datetime]:
    return (value if first is None else min(first, value), value if last is None else max(last, value))


def format_datetime(value: datetime | None) -> str:
    return value.isoformat() if value is not None else "n/a"


def numeric_stats() -> dict[str, Any]:
    return {"count": 0, "sum": 0.0, "min": None, "max": None}


def update_numeric_stats(stats: dict[str, Any], value: float) -> None:
    if not math.isfinite(value):
        return
    stats["count"] += 1
    stats["sum"] += value
    stats["min"] = value if stats["min"] is None else min(stats["min"], value)
    stats["max"] = value if stats["max"] is None else max(stats["max"], value)


def finalize_numeric_stats(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": stats["count"],
        "min": stats["min"],
        "mean": safe_ratio(stats["sum"], stats["count"]),
        "max": stats["max"],
    }


def nezha_metric_features(raw: dict[str, str]) -> dict[str, float]:
    network_receive = parse_float(raw.get("NetworkReceiveBytes"))
    network_transmit = parse_float(raw.get("NetworkTransmitBytes"))
    latency_seconds = max(
        parse_float(raw.get("PodClientLatencyP90(s)")),
        parse_float(raw.get("PodServerLatencyP90(s)")),
        parse_float(raw.get("PodClientLatencyP95(s)")),
        parse_float(raw.get("PodServerLatencyP95(s)")),
        parse_float(raw.get("PodClientLatencyP99(s)")),
        parse_float(raw.get("PodServerLatencyP99(s)")),
    )
    success_rate = parse_float(raw.get("PodSuccessRate(%)"), default=100.0)
    return {
        "cpu": parse_float(raw.get("CpuUsageRate(%)")),
        "memory": parse_float(raw.get("MemoryUsageRate(%)")),
        "network": network_receive + network_transmit,
        "latency": latency_seconds * 1000.0,
        "workload": parse_float(raw.get("PodWorkload(Ops)")),
        "success_rate_drop": max(0.0, 100.0 - success_rate),
    }


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value in {None, ""}:
        return default
    parsed = float(value)
    return parsed if math.isfinite(parsed) else default


def in_fault_window(timestamp: datetime, pod_id: str, windows: list[dict[str, Any]]) -> bool:
    return any(pod_id == window["pod_id"] and window["start"] <= timestamp <= window["end"] for window in windows)


def service_from_pod(pod_id: str) -> str:
    pod_id = pod_id.removesuffix("_metric.csv")
    match = SERVICE_RE.match(pod_id)
    return match.group("service") if match else pod_id


def count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        return max(0, sum(1 for _ in reader) - 1)


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


def fmt_float(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
