"""Map GD1 Phase 4 windows to GD2 window_ids (M2, gate G-port, QD-012).

GD1 (legacy/src/preprocessing/metric_preprocessing.py) builds one window per
pod per minute covering [T, T+120 s) (window_size 120, stride 60) from the
epoch `TimeStamp` column; GD2 has one window per metric sample covering
[t, t+60 s) (QD-003). GD1's window starts are a fixed grid (first sample + k x
60 s), not the sample times, so when Nezha's sampling drifts by a second the
grid and the samples no longer line up exactly. A GD1 window holds the samples
with T <= t < T+120 (GD1 `create_metric_windows`); it is mapped to the GD2
window of the **last** of those samples -- the sample GD1 shows the judge
(`raw_metric_snapshot` takes the last row) and, with GD2's buffer_size 2, the
GD2 window whose detector history covers the same two samples. This is the
"one-step offset" the roadmap asks to record; `offset_sec` = t - T (60 when the
grid and samples agree).

GD2 windows are read with `time_source="epoch"`, the clock GD1 used, so both
sides use the same timestamps.

Output (committed, small): eval/configs/gd1_phase4_windows.csv, one row per
GD1 window used by Phase 4 --
role "warmup" for the first 1,000 GD1 windows (detector fit,
`fit_strategy: warmup`), "evaluated" for the first 300 (= `paper_300`); the
first 300 are both.

    py scripts/map_gd1_windows.py
"""

from __future__ import annotations

import csv
import os
import sys
from bisect import bisect_left
from collections import Counter
from datetime import timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEGACY = REPO / "legacy"
sys.path.insert(0, str(REPO))

from packages.schemas.loaders import iter_telemetry_windows
from packages.schemas.nezha import load_known_services, make_window_id, pod_to_service

OUT = REPO / "eval" / "configs" / "gd1_phase4_windows.csv"
WARMUP, EVALUATED = 1000, 300
FIELDS = [
    "gd1_index",
    "gd1_window_id",
    "role",
    "pod",
    "service",
    "gd1_start",
    "gd2_window_id",
    "gd2_start",
    "offset_sec",
    "samples_in_gd1_window",
    "gd1_label",
    "gd1_fault_type",
    "gd2_is_fault",
    "gd2_fault_type",
]


def gd1_windows() -> list:
    cwd = os.getcwd()
    os.chdir(LEGACY)
    sys.path.insert(0, str(LEGACY))
    try:
        from src.config import load_config
        from src.ingestion.metric_loader import load_metrics
        from src.preprocessing.metric_preprocessing import create_metric_windows

        config = load_config("nezha_setup/config/experiment_phase4_benchmark.yaml")
        pre = config["preprocessing"]
        windows = create_metric_windows(
            load_metrics(config["data"]["metric_path"]),
            int(pre["window_size"]),
            int(pre["stride"]),
            str(pre["normalization"]),
        )
        return windows[:WARMUP]
    finally:
        sys.path.remove(str(LEGACY))
        os.chdir(cwd)


def main() -> int:
    gd1 = gd1_windows()
    known = load_known_services(REPO / "data" / "Nezha")
    pods = {w.node_id for w in gd1}
    by_pod: dict[str, list] = {}
    for w in iter_telemetry_windows(time_source="epoch"):
        if w.pod in pods:
            by_pod.setdefault(w.pod, []).append(w)
    for series in by_pod.values():
        series.sort(key=lambda w: w.start_ts)
    starts = {pod: [w.start_ts for w in series] for pod, series in by_pod.items()}
    rows = []
    for index, window in enumerate(gd1):
        service = pod_to_service(window.node_id, known)[0]
        series = by_pod.get(window.node_id, [])
        lo = bisect_left(starts.get(window.node_id, []), window.start_time)
        hi = bisect_left(starts.get(window.node_id, []), window.start_time + timedelta(seconds=120))
        target = series[hi - 1] if hi > lo else None
        rows.append(
            {
                "gd1_index": index,
                "gd1_window_id": window.window_id,
                "role": "warmup+evaluated" if index < EVALUATED else "warmup",
                "pod": window.node_id,
                "service": service,
                "gd1_start": window.start_time.isoformat(),
                "gd2_window_id": target.window_id if target else "",
                "gd2_start": target.start_ts.isoformat() if target else "",
                "offset_sec": int((target.start_ts - window.start_time).total_seconds()) if target else "",
                "samples_in_gd1_window": hi - lo,
                "gd1_label": window.label,
                "gd1_fault_type": window.fault_type,
                "gd2_is_fault": int(bool(target and target.label and target.label.is_fault)),
                "gd2_fault_type": (target.label.fault_type if target and target.label else ""),
            }
        )
        if target is not None:
            assert target.window_id == make_window_id(service, window.node_id, target.start_ts)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    evaluated = rows[:EVALUATED]
    summary = {
        "rows": len(rows),
        "missing": sum(r["gd2_window_id"] == "" for r in rows),
        "offset_sec": dict(Counter(r["offset_sec"] for r in rows)),
        "samples_per_window": dict(Counter(r["samples_in_gd1_window"] for r in rows)),
        "evaluated_gd1_faults": sum(r["gd1_label"] == "true_alert" for r in evaluated),
        "evaluated_gd2_faults": sum(r["gd2_is_fault"] for r in evaluated),
        "evaluated_label_disagreements": sum(
            (r["gd1_label"] == "true_alert") != bool(r["gd2_is_fault"]) for r in evaluated
        ),
        "warmup_pods": len({r["pod"] for r in rows}),
    }
    print(f"wrote {OUT}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
