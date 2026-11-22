"""Blind sample for manual diagnostic-quality grading (M11 step 1, P5; 02 SS4.4). No LLM call.

    py scripts/m11_sample_incidents.py --rca-run rca_final_test_v1 \
        --ctav-run ctav_final_test_v1 --c1-run h0_test_c1_k0_v1 \
        --n 30 --seed 42 --out eval/manual/diagnostic_quality

Draws `n` incidents uniformly without replacement from the RCA run sorted by `incident_id`
using `random.Random(seed).sample(...)`. Because the order is a uniform permutation of the
sample without peeking at labels, the first 15 rows (`sample_no = 1..15`) form a valid
unbiased simple random sample of size 15 on their own (QĐ-037 / 04 §9 priority 3).

Writes two UTF-8-BOM CSV files (never overwrites existing files):
- `<out>.csv`     -- blind grading sheet (reports, cited evidence, alert/judge summaries,
                     and empty `root_cause_score`, `evidence_score`, `action_score`, `note`).
- `<out>.key.csv` -- ground-truth key (`status`, `true_root_cause`, `true_fault_type`,
                     `graph_relation`, `objective_rc_score`, `invalid_evidence_ids`).
                     Do NOT open before grading is finished.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "eval" / "results"
DEFAULT_GRAPH = REPO / "data" / "graph" / "service_graph.json"

BLIND_FIELDS = [
    "sample_no",
    "incident_id",
    "start_ts",
    "end_ts",
    "alert_count",
    "services",
    "alerts_summary",
    "judge_reasonings",
    "predicted_root_cause",
    "predicted_fault_type",
    "confidence",
    "propagation_path",
    "cited_evidence",
    "suggested_actions",
    "root_cause_score",
    "evidence_score",
    "action_score",
    "note",
]

KEY_FIELDS = [
    "sample_no",
    "incident_id",
    "status",
    "injection_ids",
    "true_root_cause",
    "true_fault_type",
    "predicted_root_cause",
    "predicted_fault_type",
    "level1_hit1",
    "level1_hit3",
    "graph_relation",
    "objective_rc_score",
    "invalid_evidence_ids_count",
    "invalid_evidence_ids",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_directed_graph(path: Path) -> dict[str, set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    adj: dict[str, set[str]] = defaultdict(set)
    for edge in payload.get("edges", []):
        src = edge.get("source")
        dst = edge.get("target")
        if src and dst:
            adj[str(src)].add(str(dst))
    return dict(adj)


def classify_graph_relation(
    predicted: str | None,
    true_rc: str | None,
    directed_adj: Mapping[str, set[str]],
) -> tuple[str, str]:
    """Return `(graph_relation, objective_rc_score)` according to 02 §4.4 (0/1/2 scale)."""
    if not true_rc:
        return ("NO_GROUND_TRUTH", "")
    if not predicted:
        return ("FAR_OR_DISCONNECTED", "0")
    if predicted == true_rc:
        return ("EXACT", "2")
    if true_rc in directed_adj.get(predicted, set()):
        return ("1hop_callee", "1")
    if predicted in directed_adj.get(true_rc, set()):
        return ("1hop_caller", "1")
    return ("FAR_OR_DISCONNECTED", "0")


def draw_incidents(
    incidents: Sequence[Mapping[str, Any]],
    n: int,
    seed: int,
) -> list[Mapping[str, Any]]:
    """Draw `n` incidents uniformly without replacement from sorted `incident_id`s."""
    ordered = sorted(incidents, key=lambda row: str(row["incident_id"]))
    if n <= 0 or n > len(ordered):
        raise ValueError(f"Requested n={n}, but only {len(ordered)} incidents exist")
    return random.Random(seed).sample(ordered, n)


def _window_id_from_alert_id(alert_id: str) -> str:
    head = alert_id.split(":", 1)[0]
    return head.removeprefix("cand-")


def _format_alerts_summary(
    alert_ids: Sequence[str],
    judged_by_alert: Mapping[str, Mapping[str, Any]],
    per_window_by_id: Mapping[str, Mapping[str, str]],
) -> tuple[str, str]:
    alert_records: list[tuple[str, str, str, str, str, str]] = []
    for aid in alert_ids:
        judged = judged_by_alert.get(aid, {})
        wid = str(judged.get("window_id") or _window_id_from_alert_id(aid))
        pw = per_window_by_id.get(wid, {})
        ts = str(pw.get("window_ts") or judged.get("ts") or "")
        svc = str(pw.get("service") or judged.get("service") or "")
        score = str(pw.get("anomaly_score") or "")
        top_feat = str(pw.get("top_features") or "")
        reasoning = str(judged.get("reasoning") or "").replace("\n", " ").strip()
        alert_records.append((ts, wid, svc, score, top_feat, reasoning))

    alert_records.sort(key=lambda item: (item[0], item[1]))
    alerts_lines = [
        f"{ts} | {svc} | score={score} | top={top_feat} [{wid}]"
        for ts, wid, svc, score, top_feat, _ in alert_records
    ]
    reasoning_lines = [
        f"[{wid} | {svc}] {reasoning}"
        for _, wid, svc, _, _, reasoning in alert_records
    ]
    return "\n".join(alerts_lines), "\n".join(reasoning_lines)


def _format_evidence(evidence: Sequence[Mapping[str, Any]]) -> str:
    lines = []
    for idx, ev in enumerate(evidence, start=1):
        excerpt = str(ev.get("excerpt") or "").replace("\n", " ").strip()
        lines.append(
            f"[{idx}] ({ev.get('modality', '')}|{ev.get('service', '')}|{ev.get('ts', '')}) "
            f"{excerpt} [id={ev.get('event_id', '')}]"
        )
    return "\n".join(lines)


def _format_actions(actions: Sequence[Mapping[str, Any]]) -> str:
    lines = []
    for act in actions:
        desc = str(act.get("description") or "").replace("\n", " ").strip()
        lines.append(f"[{act.get('priority', '')}] {desc}")
    return "\n".join(lines)


def build_sample_rows(
    incidents: Sequence[Mapping[str, Any]],
    reports_by_incident: Mapping[str, Mapping[str, Any]],
    judged_by_alert: Mapping[str, Mapping[str, Any]],
    per_window_by_id: Mapping[str, Mapping[str, str]],
    directed_adj: Mapping[str, set[str]],
    n: int = 30,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    drawn = draw_incidents(incidents, n=n, seed=seed)
    blind_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []

    for sample_no, inc in enumerate(drawn, start=1):
        inc_id = str(inc["incident_id"])
        rep_entry = reports_by_incident.get(inc_id)
        if rep_entry is None:
            raise KeyError(f"Missing DiagnosticReport for incident {inc_id}")
        report = rep_entry["report"]

        alerts_summary, judge_reasonings = _format_alerts_summary(
            inc["alert_ids"], judged_by_alert, per_window_by_id
        )
        pred_rc = str(report.get("root_cause_service") or "")
        pred_ft = str(report.get("fault_type") or "")
        true_rc = inc.get("root_cause")
        true_ft = inc.get("fault_type")
        graph_rel, obj_rc = classify_graph_relation(pred_rc, true_rc, directed_adj)
        inv_ids = list(rep_entry.get("invalid_evidence_ids") or [])

        blind_rows.append(
            {
                "sample_no": sample_no,
                "incident_id": inc_id,
                "start_ts": inc["start_ts"],
                "end_ts": inc["end_ts"],
                "alert_count": len(inc["alert_ids"]),
                "services": "|".join(inc["services"]),
                "alerts_summary": alerts_summary,
                "judge_reasonings": judge_reasonings,
                "predicted_root_cause": pred_rc,
                "predicted_fault_type": pred_ft,
                "confidence": report.get("confidence", ""),
                "propagation_path": " -> ".join(report.get("propagation_path") or []),
                "cited_evidence": _format_evidence(report.get("evidence") or []),
                "suggested_actions": _format_actions(report.get("suggested_actions") or []),
                "root_cause_score": "",
                "evidence_score": "",
                "action_score": "",
                "note": "",
            }
        )
        key_rows.append(
            {
                "sample_no": sample_no,
                "incident_id": inc_id,
                "status": inc.get("status", ""),
                "injection_ids": "|".join(inc.get("injection_ids") or []),
                "true_root_cause": true_rc or "",
                "true_fault_type": true_ft or "",
                "predicted_root_cause": pred_rc,
                "predicted_fault_type": pred_ft,
                "level1_hit1": inc.get("level1_hit1", ""),
                "level1_hit3": inc.get("level1_hit3", ""),
                "graph_relation": graph_rel,
                "objective_rc_score": obj_rc,
                "invalid_evidence_ids_count": len(inv_ids),
                "invalid_evidence_ids": "|".join(inv_ids),
            }
        )
    return blind_rows, key_rows


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--rca-run", default="rca_final_test_v1")
    parser.add_argument("--ctav-run", default="ctav_final_test_v1")
    parser.add_argument("--c1-run", default="h0_test_c1_k0_v1")
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("eval/manual/diagnostic_quality"))
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    args = parser.parse_args()

    prefix = args.out if args.out.is_absolute() else REPO / args.out
    blind_path = prefix.with_name(prefix.name + ".csv")
    key_path = prefix.with_name(prefix.name + ".key.csv")
    for path in (blind_path, key_path):
        if path.exists():
            raise SystemExit(f"{path} already exists: manual samples are never overwritten")

    rca_dir = RESULTS / args.rca_run
    incidents = load_jsonl(rca_dir / "incidents.jsonl")
    reports_by_incident = {
        str(row["report"]["incident_id"]): row
        for row in load_jsonl(rca_dir / "reports.jsonl")
    }
    judged_by_alert = {
        str(row["alert_id"]): row
        for row in load_jsonl(RESULTS / args.ctav_run / "judged.jsonl")
    }
    with (RESULTS / args.c1_run / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        per_window_by_id = {row["window_id"]: row for row in csv.DictReader(handle)}

    directed_adj = load_directed_graph(args.graph if args.graph.is_absolute() else REPO / args.graph)
    blind_rows, key_rows = build_sample_rows(
        incidents=incidents,
        reports_by_incident=reports_by_incident,
        judged_by_alert=judged_by_alert,
        per_window_by_id=per_window_by_id,
        directed_adj=directed_adj,
        n=args.n,
        seed=args.seed,
    )

    prefix.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(blind_path, BLIND_FIELDS, blind_rows)
    _write_csv(key_path, KEY_FIELDS, key_rows)
    print(f"wrote {blind_path} ({len(blind_rows)} incidents) and {key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
