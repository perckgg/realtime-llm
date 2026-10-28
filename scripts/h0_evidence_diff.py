"""So sánh bằng chứng giữa hai run H0 (QĐ-026): vì sao C1-paper khác BM25 khi không có lân cận?

    py scripts/h0_evidence_diff.py --a h0_val_bm25_v3 --b h0_val_c1_k0_v1 --out h0_val_evidence_diff_v1

Chỉ đọc `per_window.csv` + `retrieval.jsonl` của hai run (không gọi LLM). Trên candidate có
telemetry, theo nhãn: tỷ lệ prompt có bằng chứng, số event, tỷ lệ trace, tỷ lệ bằng chứng lân
cận, trung vị |t_e − t_0|, verdict thô, quyết định; số event trùng giữa hai run; và FP (alert
trên cửa sổ bình thường) có nằm gần một cửa sổ sự cố (cùng service / bất kỳ service) không.
Ghi `eval/results/<out>/evidence_diff.json` (thư mục phải chưa tồn tại).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "eval" / "results"


def _windows(run: str) -> pd.DataFrame:
    df = pd.read_csv(RESULTS / run / "per_window.csv", dtype={"window_id": str})
    df["ts"] = pd.to_datetime(df["window_ts"])
    return df.set_index("window_id")


def _retrieval(run: str) -> dict[str, list[dict]]:
    out = {}
    with (RESULTS / run / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            out[row["window_id"]] = row["events"]
    return out


def _evidence_stats(windows: pd.DataFrame, events: dict[str, list[dict]], ids: list[str]) -> dict:
    sub = windows.loc[ids]
    picked = [(w, e) for w in ids for e in events.get(w, [])]
    dt = [abs((pd.Timestamp(e["ts"]) - windows.at[w, "ts"]).total_seconds()) for w, e in picked]
    return {
        "candidates": len(ids),
        "with_evidence": int((sub["context_events"] > 0).sum()),
        "mean_events": round(float(sub["context_events"].mean()), 3),
        "trace_share": round(sum(e["modality"] == "trace" for _, e in picked) / len(picked), 4) if picked else None,
        "neighbor_share": round(sum(e["origin"] != "local" for _, e in picked) / len(picked), 4) if picked else None,
        "median_abs_dt_s": round(statistics.median(dt), 1) if dt else None,
        "raw_verdict": {str(k): int(v) for k, v in sub["raw_verdict"].value_counts().items()},
        "decision": {str(k): int(v) for k, v in sub["decision"].value_counts().items()},
    }


def _near_fault(windows: pd.DataFrame, ids: list[str], seconds: int, same_service: bool) -> float | None:
    if not ids:
        return None
    faults = windows[windows["label_is_fault"] == 1]
    hits = 0
    for w in ids:
        f = faults[faults["service"] == windows.at[w, "service"]] if same_service else faults
        gap = (f["ts"] - windows.at[w, "ts"]).abs().dt.total_seconds()
        hits += bool(np.any(gap <= seconds))
    return round(hits / len(ids), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, help="run tham chiếu (vd. BM25)")
    parser.add_argument("--b", required=True, help="run so sánh (vd. C1-paper)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out_dir = RESULTS / args.out
    if out_dir.exists():
        sys.exit(f"{out_dir} already exists: results are never overwritten, use a new name")

    report: dict = {"a": args.a, "b": args.b, "runs": {}}
    wa, wb = _windows(args.a), _windows(args.b)
    ea, eb = _retrieval(args.a), _retrieval(args.b)
    cand = wa[(wa["is_candidate"] == 1) & (wa["has_telemetry"] == 1)]
    for run, windows, events in ((args.a, wa, ea), (args.b, wb, eb)):
        entry: dict = {}
        for label, name in ((0, "normal"), (1, "fault")):
            entry[name] = _evidence_stats(windows, events, list(cand.index[cand["label_is_fault"] == label]))
        normal = windows.loc[cand.index[cand["label_is_fault"] == 0]]
        groups = {"fp_alert": list(normal.index[normal["decision"] == "alert"]),
                  "normal_not_alert": list(normal.index[normal["decision"] != "alert"])}
        entry["near_fault"] = {
            g: {"n": len(ids),
                "same_service_10min": _near_fault(windows, ids, 600, True),
                "any_service_2min": _near_fault(windows, ids, 120, False),
                "any_service_5min": _near_fault(windows, ids, 300, False)}
            for g, ids in groups.items()
        }
        report["runs"][run] = entry

    both = [w for w in cand.index if ea.get(w) and eb.get(w)]
    overlap = [len({e["event_id"] for e in ea[w]} & {e["event_id"] for e in eb[w]}) for w in both]
    report["overlap"] = {
        "prompts_both_with_evidence": len(both),
        "mean_shared_events": round(statistics.mean(overlap), 3) if overlap else None,
        "identical_event_sets": sum({e["event_id"] for e in ea[w]} == {e["event_id"] for e in eb[w]} for w in both),
    }
    out_dir.mkdir(parents=True)
    (out_dir / "evidence_diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
