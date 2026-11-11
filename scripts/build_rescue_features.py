"""Rescue Score components for every window of a split (M7, QD-033). No LLM call, no label.

    py scripts/build_rescue_features.py --config eval/configs/m7_rescue_features_val.yaml

Windows (and the detector's promotion, anomaly score) come from a full run of the split
(`windows_run`); the alert set A from the pipeline's own decisions (`alerts_run`, CTAV).
Writes eval/results/<run_id>/rescue_features.parquet (one row per window: n_err,
lambda_log, phi_topo, delta_time, n_active) + summary.json + config.snapshot.yaml.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.rescue import load_features_config as load_config  # noqa: E402
from eval.harness.runner import RESULTS, _git_commit  # noqa: E402
from packages.graph.service_graph import load_graph  # noqa: E402
from packages.schemas.evidence import NezhaEvidenceStore  # noqa: E402
from packages.schemas.nezha import dataset_root  # noqa: E402
from services.detector.rescue import (  # noqa: E402
    Alert,
    ErrorLogRule,
    active_alerts,
    delta_time,
    lambda_log,
    phi_topo,
)


def _rows(run_id: str) -> list[dict[str, str]]:
    with (RESULTS / run_id / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def error_counts(
    windows: list[dict[str, Any]], rule: ErrorLogRule, window_seconds: float
) -> tuple[list[int], Counter[str]]:
    """N_err per window: error log lines of the window's pod with start <= ts < start + window_seconds."""
    by_pod: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for i, w in enumerate(windows):
        by_pod[w["pod"]].append((w["start"], i))
    starts = {pod: [s for s, _ in sorted(v)] for pod, v in by_pod.items()}
    index = {pod: [i for _, i in sorted(v)] for pod, v in by_pod.items()}
    counts = [0] * len(windows)
    stats: Counter[str] = Counter()
    span = timedelta(seconds=window_seconds)
    lo = min(w["start"] for w in windows) - timedelta(minutes=2)
    hi = max(w["start"] for w in windows) + span + timedelta(minutes=2)
    store = NezhaEvidenceStore(dataset_root(), cache_files=2)
    seen: set[tuple[str, str, str]] = set()  # the per-minute files overlap (evidence.clean)
    for file in store.files_for(lo, hi):
        if file.kind != "log":
            continue
        for doc in store.load_file(file):
            stats["log_lines"] += 1
            if not rule.matches(doc.severity, doc.message):
                continue
            key = (doc.ts.isoformat(), doc.pod, doc.message)
            if key in seen:
                continue
            seen.add(key)
            stats["error_lines"] += 1
            pod_starts = starts.get(doc.pod)
            if not pod_starts:
                stats["error_lines_no_window_pod"] += 1
                continue
            j = bisect.bisect_right(pod_starts, doc.ts) - 1
            if j >= 0 and doc.ts < pod_starts[j] + span:
                counts[index[doc.pod][j]] += 1
                stats["error_lines_in_window"] += 1
    return counts, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    out = RESULTS / config["run_id"]
    if out.exists():
        raise SystemExit(f"{out} already exists: results are never overwritten")
    started = time.perf_counter()

    rows = _rows(config["windows_run"])
    windows: list[dict[str, Any]] = [
        {
            "window_id": r["window_id"],
            "service": r["service"],
            "pod": r["pod"] or r["service"],
            "start": datetime.fromisoformat(r["window_ts"]),
            "is_candidate": int(r["is_candidate"]),
            "has_telemetry": int(r["has_telemetry"]),
            "anomaly_score": float(r["anomaly_score"] or 0.0),
        }
        for r in rows
    ]
    alert_rows = _rows(config["alerts_run"])
    if [r["window_id"] for r in alert_rows] != [w["window_id"] for w in windows]:
        raise ValueError("alerts_run and windows_run do not cover the same windows")
    alerts = sorted(
        (Alert(datetime.fromisoformat(r["window_ts"]), r["service"]) for r in alert_rows if r["decision"] == "alert"),
        key=lambda a: a.ts,
    )

    log_spec = config["log"]
    counts, stats = error_counts(windows, ErrorLogRule.from_config(log_spec), float(config["window_seconds"]))

    graph = load_graph(REPO / config.get("graph", "data/graph/service_graph.json"))
    dist_memo: dict[str, dict[str, int]] = {}

    def distance(a: str, b: str) -> int | None:
        if a not in dist_memo:
            dist_memo[a] = graph.distances(a) or {a: 0}
        return dist_memo[a].get(b)

    sigma = float(config["time"]["sigma_seconds"])
    active_seconds = float(config["time"]["active_seconds"])
    alert_ts = [a.ts for a in alerts]
    records = []
    for w, n_err in zip(windows, counts, strict=True):
        lo = bisect.bisect_left(alert_ts, w["start"] - timedelta(seconds=active_seconds))
        hi = bisect.bisect_right(alert_ts, w["start"])
        active = active_alerts(alerts[lo:hi], w["start"], active_seconds)
        records.append(
            {
                "window_id": w["window_id"],
                "service": w["service"],
                "pod": w["pod"],
                "window_ts": w["start"].isoformat(),
                "is_candidate": w["is_candidate"],
                "has_telemetry": w["has_telemetry"],
                "anomaly_score": w["anomaly_score"],
                "n_err": n_err,
                "lambda_log": lambda_log(n_err, float(log_spec["k_log"])),
                "phi_topo": phi_topo(w["service"], active, distance),
                "delta_time": delta_time(w["start"], active, sigma),
                "n_active": len(active),
            }
        )
    frame = pd.DataFrame.from_records(records)
    out.mkdir(parents=True)
    frame.to_parquet(out / "rescue_features.parquet", index=False)
    non_candidate = frame[frame["is_candidate"] == 0]
    summary = {
        "config": config,
        "windows": len(frame),
        "alerts_in_A": len(alerts),
        "log_stats": dict(stats),
        "nonzero": {c: int((non_candidate[c] > 0).sum()) for c in ("lambda_log", "phi_topo", "delta_time")},
        "non_candidate_windows": len(non_candidate),
        "quantiles_non_candidate": {
            c: [float(non_candidate[c].quantile(q)) for q in (0.5, 0.9, 0.99)]
            for c in ("lambda_log", "phi_topo", "delta_time")
        },
        "wall_seconds": round(time.perf_counter() - started, 1),
        "git_commit": _git_commit(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "config.snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "config"}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
