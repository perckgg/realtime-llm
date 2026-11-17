"""Deterministic rule-based selector for M10-D demo walkthrough cases (QĐ-048).

Picks real, reproducible window/alert/incident IDs from committed eval & pipeline
artifacts (`seed=42` default) for Steps 2, 3, and 4 of `08-research-direction.md` §6,
including V48 `(b') + (a')`:
- Step 2 (`c3_downgrade`): Normal window on `pipeline_test_v2` where raw LLM verdict
  was `TRUE_ALERT` but C3 dev-p90 anchoring downgraded it to `UNCERTAIN`.
- Step 3 (`topo_rescue_network_delay`): Fault window with `network_delay` on
  `pipeline_test_v2` missed by BM25 (`h0_test_bm25_v1`) and confirmed by CTAV.
- Step 4 (`incident_cascade`):
  - Primary `(b')`: Multi-service labelled cascade hit from `pipeline_sens_test_v1`
    (`c3_rolling_baseline` sensitivity run, clearly marked out-of-registration).
  - Limitation `(a')`: Registered `pipeline_val_v2` cascade split (`2023-01-30#009`)
    across two single-service incidents where intermediate hop lacked a confirmed alert.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "eval" / "results"
DEFAULT_OUTPUT = RESULTS_DIR / "m10_demo_cases_v1" / "demo_cases.json"


def _load_per_window(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["window_id"]: row for row in csv.DictReader(handle)}


def _load_judged(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                out[str(row["window_id"])] = row
    return out


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _pick_c3_downgrade(results_root: Path, rng: random.Random) -> dict[str, Any]:
    ctav_dir = results_root / "ctav_final_test_v1"
    pw = _load_per_window(ctav_dir / "per_window.csv")
    judged = _load_judged(ctav_dir / "judged.jsonl")

    pool: list[dict[str, Any]] = []
    for wid, row in pw.items():
        if (
            row.get("label_is_fault") == "0"
            and row.get("judged") == "1"
            and row.get("raw_verdict") == "TRUE_ALERT"
            and row.get("verdict") == "UNCERTAIN"
            and row.get("downgraded_by_anchoring") == "1"
            and row.get("downgraded_by_evidence_rule") == "0"
            and row.get("downgraded_by_gating") == "0"
            and row.get("routing_tier") == "2"
        ):
            j = judged.get(wid)
            if not j or not j.get("evidence_event_ids") or not j.get("reasoning"):
                continue
            pool.append(
                {
                    "run_id": "pipeline_test_v2",
                    "window_id": wid,
                    "alert_id": str(j["alert_id"]),
                    "service": row["service"],
                    "ts": row["window_ts"],
                    "anomaly_score": float(row["anomaly_score"]),
                    "raw_verdict": row["raw_verdict"],
                    "verdict": row["verdict"],
                    "confidence": float(row["confidence"]),
                    "threshold_applied": float(row["threshold_applied"]),
                    "evidence_origin": str(j.get("evidence_origin", "")),
                    "evidence_event_count": len(j["evidence_event_ids"]),
                    "downgraded_by_anchoring": True,
                    "reasoning": str(j["reasoning"]),
                }
            )

    pool.sort(key=lambda item: (item["ts"], item["window_id"]))
    if not pool:
        raise RuntimeError("No C3 anchoring downgrade candidates found in ctav_final_test_v1")

    chosen = rng.choice(pool)
    return {
        "step": 2,
        "title": "False alarm candidate downgraded from TRUE_ALERT to UNCERTAIN by CTAV C3 anchoring",
        "pool_size": len(pool),
        "primary": chosen,
        "ui_path": f"/alerts/{chosen['alert_id']}?run_id=pipeline_test_v2",
    }


def _pick_topo_rescue_network_delay(results_root: Path, rng: random.Random) -> dict[str, Any]:
    bm25_dir = results_root / "h0_test_bm25_v1"
    ctav_dir = results_root / "ctav_final_test_v1"
    bm25_pw = _load_per_window(bm25_dir / "per_window.csv")
    bm25_judged = _load_judged(bm25_dir / "judged.jsonl")
    ctav_pw = _load_per_window(ctav_dir / "per_window.csv")
    ctav_judged = _load_judged(ctav_dir / "judged.jsonl")

    pool: list[dict[str, Any]] = []
    for wid, c_row in ctav_pw.items():
        b_row = bm25_pw.get(wid)
        if not b_row:
            continue
        if (
            c_row.get("label_is_fault") == "1"
            and c_row.get("label_fault_type") == "network_delay"
            and c_row.get("verdict") == "TRUE_ALERT"
            and c_row.get("decision") == "alert"
            and c_row.get("routing_tier") == "2"
            and b_row.get("judged") == "1"
            and b_row.get("verdict") != "TRUE_ALERT"
        ):
            cj = ctav_judged[wid]
            bj = bm25_judged[wid]
            pool.append(
                {
                    "run_id": "pipeline_test_v2",
                    "window_id": wid,
                    "alert_id": str(cj["alert_id"]),
                    "bm25_alert_id": str(bj["alert_id"]),
                    "service": c_row["service"],
                    "ts": c_row["window_ts"],
                    "anomaly_score": float(c_row["anomaly_score"]),
                    "label_fault_type": c_row["label_fault_type"],
                    "label_root_cause": c_row["label_root_cause"],
                    "bm25_verdict": b_row["verdict"],
                    "bm25_confidence": float(b_row["confidence"]),
                    "bm25_reasoning": str(bj.get("reasoning", "")),
                    "ctav_verdict": c_row["verdict"],
                    "ctav_confidence": float(c_row["confidence"]),
                    "ctav_evidence_origin": str(cj.get("evidence_origin", "")),
                    "ctav_evidence_event_count": len(cj.get("evidence_event_ids") or []),
                    "ctav_reasoning": str(cj.get("reasoning", "")),
                }
            )

    pool.sort(key=lambda item: (item["ts"], item["window_id"]))
    if not pool:
        raise RuntimeError("No network_delay BM25-miss + CTAV-hit cases found on test split")

    chosen = rng.choice(pool)
    return {
        "step": 3,
        "title": "network_delay missed by BM25, confirmed by CTAV topology retrieval",
        "pool_size": len(pool),
        "primary": chosen,
        "all_candidates": pool,
        "val_note": (
            "On val (ctav_final_val_v1), CTAV retained 0 network_delay alerts confirmed by C1 "
            "(Finding 10); on test (ctav_final_test_v1), CTAV retained 2 network_delay alerts "
            "that BM25 missed."
        ),
        "ui_path": f"/alerts/{chosen['alert_id']}?run_id=pipeline_test_v2",
    }


def _pick_incident_cascade(
    results_root: Path,
    rng: random.Random,
    *,
    primary_confirmed_alerts: int,
    sens_confirmed_alerts: int,
) -> dict[str, Any]:
    sens_dir = results_root / "pipeline_sens_test_v1"
    ref_dir = results_root / "rca_sens_test_c3rolling_v1"
    val_dir = results_root / "pipeline_val_v2"

    sens_incidents = _load_jsonl(sens_dir / "incidents.jsonl")
    ref_incidents = _load_jsonl(ref_dir / "incidents.jsonl")
    ref_by_alerts = {tuple(row["alert_ids"]): str(row["incident_id"]) for row in ref_incidents}

    sens_reports = {
        str(row["report"]["incident_id"]): row["report"]
        for row in _load_jsonl(sens_dir / "reports.jsonl")
        if row.get("report") is not None
    }

    pool: list[dict[str, Any]] = []
    for inc in sens_incidents:
        if (
            inc.get("status") == "labelled"
            and len(inc.get("services") or []) >= 2
            and inc.get("level1_hit1") is True
        ):
            rep = sens_reports.get(str(inc["incident_id"]), {})
            pool.append(
                {
                    "run_id": "pipeline_sens_test_v1",
                    "incident_id": str(inc["incident_id"]),
                    "reference_incident_id": ref_by_alerts.get(tuple(inc["alert_ids"]), ""),
                    "services": list(inc["services"]),
                    "alert_ids": list(inc["alert_ids"]),
                    "start_ts": str(inc["start_ts"]),
                    "end_ts": str(inc["end_ts"]),
                    "fault_type": inc.get("fault_type"),
                    "root_cause": inc.get("root_cause"),
                    "level1": list(inc["level1"]),
                    "level1_hit1": bool(inc["level1_hit1"]),
                    "baseline": list(inc.get("baseline") or []),
                    "graph_edges_used": list((inc.get("grouping_reason") or {}).get("graph_edges_used") or []),
                    "report_confidence": rep.get("confidence"),
                    "report_root_cause_service": rep.get("root_cause_service"),
                    "report_propagation_path": rep.get("propagation_path"),
                    "report_top_action": ((rep.get("suggested_actions") or [{}])[0]).get("description"),
                }
            )

    pool.sort(key=lambda item: (item["start_ts"], item["incident_id"]))
    if not pool:
        raise RuntimeError("No labelled multi-service cascade hit found in pipeline_sens_test_v1")

    chosen = rng.choice(pool)

    # V48 (a') limitation on registered val split: cascade injection split into single-service incidents.
    val_incidents = _load_jsonl(val_dir / "incidents.jsonl")
    by_inj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for inc in val_incidents:
        if inc.get("status") == "labelled" and len(inc.get("injection_ids") or []) == 1:
            by_inj[str(inc["injection_ids"][0])].append(inc)

    split_cascades: list[dict[str, Any]] = []
    for inj_id, items in sorted(by_inj.items()):
        distinct_services = {svc for item in items for svc in item.get("services") or []}
        if len(items) >= 2 and len(distinct_services) >= 2:
            split_cascades.append(
                {
                    "run_id": "pipeline_val_v2",
                    "injection_id": inj_id,
                    "fault_type": items[0].get("fault_type"),
                    "root_cause": items[0].get("root_cause"),
                    "split_incidents": [
                        {
                            "incident_id": str(item["incident_id"]),
                            "services": list(item["services"]),
                            "alert_ids": list(item["alert_ids"]),
                            "start_ts": str(item["start_ts"]),
                            "level1_hit1": item.get("level1_hit1"),
                        }
                        for item in items
                    ],
                }
            )

    return {
        "step": 4,
        "title": "Cascade incident grouping & root-cause localization (V48 (b') + (a'))",
        "out_of_registration_sensitivity": True,
        "sensitivity_banner": (
            f"pipeline_sens_test_v1 replays the out-of-registration sensitivity variant "
            f"c3_rolling_baseline ({sens_confirmed_alerts} alerts); primary H5 evaluation on "
            f"rca_final_test_v1 (pipeline_test_v2, {primary_confirmed_alerts} alerts) yielded "
            "zero multi-service cascade incidents."
        ),
        "pool_size": len(pool),
        "primary": chosen,
        "all_candidates": pool,
        "ui_path": f"/incidents/{chosen['incident_id']}?run_id=pipeline_sens_test_v1",
        "registered_val_limitation": split_cascades[0] if split_cascades else None,
        "all_registered_val_splits": split_cascades,
    }


def pick_demo_cases(results_root: Path = RESULTS_DIR, *, seed: int = 42) -> dict[str, Any]:
    runtime_test = json.loads((results_root / "pipeline_test_v2" / "runtime.json").read_text(encoding="utf-8"))
    runtime_val = json.loads((results_root / "pipeline_val_v2" / "runtime.json").read_text(encoding="utf-8"))
    runtime_sens = json.loads((results_root / "pipeline_sens_test_v1" / "runtime.json").read_text(encoding="utf-8"))

    rng = random.Random(seed)
    step2 = _pick_c3_downgrade(results_root, rng)
    step3 = _pick_topo_rescue_network_delay(results_root, rng)
    step4 = _pick_incident_cascade(
        results_root,
        rng,
        primary_confirmed_alerts=int(runtime_test["counts"]["confirmed_alerts"]),
        sens_confirmed_alerts=int(runtime_sens["counts"]["confirmed_alerts"]),
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "selection_policy": "deterministic rule-based filtering + random.Random(seed)",
        "runs": {
            "primary_test": {
                "run_id": runtime_test["run_id"],
                "candidates_loaded": runtime_test["counts"]["candidates_loaded"],
                "confirmed_alerts": runtime_test["counts"]["confirmed_alerts"],
                "incidents": runtime_test["counts"]["incidents"],
            },
            "primary_val": {
                "run_id": runtime_val["run_id"],
                "candidates_loaded": runtime_val["counts"]["candidates_loaded"],
                "confirmed_alerts": runtime_val["counts"]["confirmed_alerts"],
                "incidents": runtime_val["counts"]["incidents"],
            },
            "sensitivity_test": {
                "run_id": runtime_sens["run_id"],
                "ctav_variant": runtime_sens.get("ctav_variant"),
                "candidates_loaded": runtime_sens["counts"]["candidates_loaded"],
                "confirmed_alerts": runtime_sens["counts"]["confirmed_alerts"],
                "incidents": runtime_sens["counts"]["incidents"],
            },
        },
        "steps": {
            "step1_timeline": {
                "step": 1,
                "title": "Timeline overview of candidate triage and routing tiers",
                "run_id": "pipeline_test_v2",
                "ui_path": "/?run_id=pipeline_test_v2",
            },
            "step2_c3_downgrade": step2,
            "step3_topo_rescue_network_delay": step3,
            "step4_incident_cascade": step4,
            "step5_comparison": {
                "step": 5,
                "title": "H0-H5 experiment comparison tables with bootstrap 95% CIs",
                "ui_path": "/compare",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick deterministic M10-D demo cases.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--results-root", type=Path, default=RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = pick_demo_cases(results_root=args.results_root, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(
        "step2:",
        payload["steps"]["step2_c3_downgrade"]["primary"]["alert_id"],
        "| step3:",
        payload["steps"]["step3_topo_rescue_network_delay"]["primary"]["alert_id"],
        "| step4:",
        payload["steps"]["step4_incident_cascade"]["primary"]["incident_id"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
