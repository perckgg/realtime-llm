"""Finding 11 on a split: what the missing `dev` span baselines cost CTAV (M8, V31). No LLM call.

    py scripts/m8_finding11.py --ctav ctav_final_test_v1 --c1 h0_test_c1_k0_v1 --out m8_finding11_test_v1

C3 can only anchor a span on a service that has a `dev` p90 threshold (data/span_baseline.parquet).
For the windows with telemetry of the split, grouped by whether the alert's service has any `dev`
threshold, this reports: services, fault windows, detector candidates, C1 and CTAV true / false
positives, recall of both, and how many C1 alerts on fault windows C3 downgraded. Descriptive
only -- nothing is tuned. Writes `finding11.json` and `tables.md` to eval/results/<out>/.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.runner import RESULTS, _git_commit  # noqa: E402


def _flag(value: str) -> bool:
    return value not in ("", "0", "False", "false")


def _rows(run_id: str) -> list[dict[str, str]]:
    with (RESULTS / run_id / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyse(ctav: list[dict[str, str]], c1: list[dict[str, str]], covered: set[str]) -> dict[str, Any]:
    if [r["window_id"] for r in ctav] != [r["window_id"] for r in c1]:
        raise ValueError("the CTAV run and the C1 run do not cover the same windows")
    groups: dict[str, dict[str, Any]] = {
        name: {"services": set(), "fault_services": set(), "windows": 0, "fault": 0, "normal": 0, "fault_candidates": 0,
               "c1_tp": 0, "ctav_tp": 0, "c1_fp": 0, "ctav_fp": 0, "c1_tp_downgraded_by_anchoring": 0}
        for name in ("with_dev_baseline", "without_dev_baseline")
    }  # fmt: skip
    per_service: dict[str, dict[str, int]] = defaultdict(lambda: {"fault": 0, "c1_tp": 0, "ctav_tp": 0})
    for a, b in zip(ctav, c1, strict=True):
        if not _flag(a["has_telemetry"]):
            continue
        g = groups["with_dev_baseline" if a["service"] in covered else "without_dev_baseline"]
        fault = _flag(a["label_is_fault"])
        c1_alert, ctav_alert = b["decision"] == "alert", a["decision"] == "alert"
        g["services"].add(a["service"])
        g["windows"] += 1
        g["fault" if fault else "normal"] += 1
        if fault:
            g["fault_services"].add(a["service"])
            g["fault_candidates"] += _flag(a["is_candidate"])
            g["c1_tp"] += c1_alert
            g["ctav_tp"] += ctav_alert
            g["c1_tp_downgraded_by_anchoring"] += c1_alert and _flag(a["downgraded_by_anchoring"])
            s = per_service[a["service"]]
            s["fault"] += 1
            s["c1_tp"] += c1_alert
            s["ctav_tp"] += ctav_alert
        else:
            g["c1_fp"] += c1_alert
            g["ctav_fp"] += ctav_alert
    out: dict[str, Any] = {"groups": {}, "fault_services": {}}
    for name, g in groups.items():
        entry = {k: v for k, v in g.items() if not isinstance(v, set)}
        entry["services"] = sorted(g["services"])
        entry["fault_services"] = sorted(g["fault_services"])
        entry["c1_recall"] = g["c1_tp"] / g["fault"] if g["fault"] else None
        entry["ctav_recall"] = g["ctav_tp"] / g["fault"] if g["fault"] else None
        out["groups"][name] = entry
    for service, s in sorted(per_service.items()):
        out["fault_services"][service] = {**s, "has_dev_baseline": service in covered}
    total_fault = sum(g["fault"] for g in groups.values())
    lost = groups["without_dev_baseline"]
    out["summary"] = {
        "fault_windows": total_fault,
        "fault_windows_without_dev_baseline": lost["fault"],
        "c1_tp_without_dev_baseline": lost["c1_tp"],
        "ctav_tp_without_dev_baseline": lost["ctav_tp"],
        # recall points CTAV cannot reach because C3 has no threshold there (C1 alerts it loses)
        "recall_lost_vs_c1_without_dev_baseline": (lost["c1_tp"] - lost["ctav_tp"]) / total_fault if total_fault else None,
    }
    return out


def _f(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}".replace(".", ",")


def tables(report: dict[str, Any], split: str) -> str:
    out = [f"**Bảng F11-1. Phát hiện 11 trên `{split}` (cửa sổ có telemetry), theo việc service của cảnh báo có ngưỡng `dev` hay không.**", "",
           "| | Có ngưỡng `dev` | Không có ngưỡng `dev` |", "|---|---:|---:|"]
    a, b = report["groups"]["with_dev_baseline"], report["groups"]["without_dev_baseline"]

    def line(name: str, key: str) -> None:
        out.append(f"| {name} | {a[key]} | {b[key]} |")

    out.append(f"| Service | {len(a['services'])} | {len(b['services'])} |")
    out.append(f"| Service có fault | {len(a['fault_services'])} | {len(b['fault_services'])} |")
    for name, key in (("Cửa sổ", "windows"), ("Fault", "fault"), ("Fault là candidate", "fault_candidates"),
                      ("C1: TP", "c1_tp"), ("CTAV: TP", "ctav_tp"), ("C1 TP bị C3 hạ", "c1_tp_downgraded_by_anchoring"),
                      ("C1: FP", "c1_fp"), ("CTAV: FP", "ctav_fp")):  # fmt: skip
        line(name, key)
    out.append(f"| Recall C1 | {_f(a['c1_recall'])} | {_f(b['c1_recall'])} |")
    out.append(f"| Recall CTAV | {_f(a['ctav_recall'])} | {_f(b['ctav_recall'])} |")
    s = report["summary"]
    out += ["", f"Recall CTAV mất so với C1 ở nhóm không có ngưỡng `dev`: {_f(s['recall_lost_vs_c1_without_dev_baseline'])} "
            f"({s['c1_tp_without_dev_baseline']} − {s['ctav_tp_without_dev_baseline']} TP trên {s['fault_windows']} fault).", "",
            f"**Bảng F11-2. Fault theo service trên `{split}`.**", "", "| Service | Ngưỡng `dev` | Fault | C1 TP | CTAV TP |", "|---|---|---:|---:|---:|"]
    for service, e in report["fault_services"].items():
        out.append(f"| {service} | {'có' if e['has_dev_baseline'] else '**không**'} | {e['fault']} | {e['c1_tp']} | {e['ctav_tp']} |")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ctav", required=True)
    parser.add_argument("--c1", required=True)
    parser.add_argument("--baseline", default="data/span_baseline.parquet")
    parser.add_argument("--split", default="test")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    out_dir = RESULTS / args.out
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten")
    covered = set(pd.read_parquet(REPO / args.baseline)["service"].unique())
    report = analyse(_rows(args.ctav), _rows(args.c1), covered)
    report.update({"created_at": datetime.now(UTC).isoformat(), "git_commit": _git_commit(), "split": args.split,
                   "inputs": {"ctav": args.ctav, "c1": args.c1, "baseline": args.baseline},
                   "services_with_dev_baseline": sorted(covered)})
    out_dir.mkdir(parents=True)
    (out_dir / "finding11.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text = tables(report, args.split)
    (out_dir / "tables.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
