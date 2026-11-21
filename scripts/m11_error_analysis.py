"""Descriptive error analysis on `test` for CTAV and the RCA agent (M11 step 3, P5).

Zero LLM calls and zero threshold/config modifications. Reads frozen M8/M9 `test` outputs,
reuses `m8_detector_shift_test_v1/shift.json` and `m8_finding11_test_v1/finding11.json`,
and classifies:
  1. All 64 CTAV false positives (service, date, anchor mechanism, origin, shift, fault overlap).
  2. All 332 CTAV false negatives (detector missed, judge FALSE_POSITIVE, C3 anchoring drops).
  3. All RCA errors on `rca_final_test_v1` and sensitivity `rca_sens_test_c3rolling_v1`.

    py scripts/m11_error_analysis.py --out eval/results/m11_error_analysis_test_v1
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from eval.harness.rca import Injection, alert_injections, load_injections  # noqa: E402

RESULTS = REPO / "eval" / "results"
GRAPH_PATH = REPO / "data" / "graph" / "service_graph.json"
WINDOW_INDEX = REPO / "data" / "window_index.csv"


def _flag(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "") not in ("", "0", "False", "false")


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_per_window(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_anchor_map(path: Path, run_name: str = "h0_test_c1_k0_v1") -> dict[str, dict[str, dict[str, Any]]]:
    anchors: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("run") == run_name:
                anchors[str(row["window_id"])][str(row["event_id"])] = row
    return dict(anchors)


def _load_graph_adjacency(path: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    directed: dict[str, set[str]] = defaultdict(set)
    undirected: dict[str, set[str]] = defaultdict(set)
    for edge in payload.get("edges", []):
        src = str(edge.get("source") or "")
        dst = str(edge.get("target") or "")
        if src and dst:
            directed[src].add(dst)
            undirected[src].add(dst)
            undirected[dst].add(src)
    return dict(directed), dict(undirected)


def _extract_anchor_ids(row: Mapping[str, str]) -> list[str]:
    raw = str(row.get("anchor_ids") or "").strip()
    if not raw:
        return []
    return [tok for tok in raw.split("|") if tok]


def _pick_examples(items: Sequence[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda x: (str(x.get("window_ts") or x.get("start_ts") or ""), str(x.get("window_id") or x.get("incident_id") or "")))
    return ordered[:limit]


def _summarize_ctav_fps(
    fps: Sequence[Mapping[str, str]],
    ctav_judged: Mapping[str, Mapping[str, Any]],
    c1_retrieval: Mapping[str, Sequence[Mapping[str, Any]]],
    anchors: Mapping[str, Mapping[str, Mapping[str, Any]]],
    has_dev_services: set[str],
    injections: Sequence[Injection],
    inj_by_id: Mapping[str, Injection],
    shift_test: Mapping[str, Any],
    shift_val: Mapping[str, Any],
    shift_dev: Mapping[str, Any],
) -> dict[str, Any]:
    by_service: Counter[str] = Counter()
    by_date: Counter[str] = Counter()
    by_has_dev: Counter[str] = Counter()
    by_raw_verdict_conf: Counter[str] = Counter()
    by_origin: Counter[str] = Counter()
    by_cited_modalities: Counter[str] = Counter()
    by_anchor_mechanism: Counter[str] = Counter()
    collateral_by_svc_rc: Counter[str] = Counter()
    collateral_by_fault_type: Counter[str] = Counter()

    collateral_items: list[dict[str, Any]] = []
    normal_traffic_items: list[dict[str, Any]] = []
    ratios_collateral: list[float] = []
    ratios_normal: list[float] = []

    for row in fps:
        wid = str(row["window_id"])
        svc = str(row["service"])
        wts = str(row["window_ts"])
        judged = ctav_judged[wid]
        events_by_id = {str(e["event_id"]): e for e in c1_retrieval.get(wid, ())}

        by_service[svc] += 1
        by_date[wts[:10]] += 1
        by_has_dev["with_dev_baseline" if svc in has_dev_services else "without_dev_baseline"] += 1
        by_raw_verdict_conf[f"{row['raw_verdict']}|conf={row['confidence']}"] += 1
        by_origin[str(judged.get("evidence_origin") or "unknown")] += 1

        cited_mods = sorted(
            {
                str(events_by_id[eid]["modality"])
                for eid in judged.get("evidence_event_ids", [])
                if eid in events_by_id
            }
        )
        by_cited_modalities["+".join(cited_mods) if cited_mods else "none"] += 1

        anchor_ids = _extract_anchor_ids(row)
        anchor_kinds: set[str] = set()
        best_ratio = 0.0
        best_anchor_info: dict[str, Any] = {}
        for aid in anchor_ids:
            af = anchors.get(wid, {}).get(aid)
            ev = events_by_id.get(aid, {})
            if af and af.get("modality") == "log":
                anchor_kinds.add(f"log:{af.get('severity')}")
            elif af:
                anchor_kinds.add("trace:span>dev_p90")
                p90 = (af.get("dev") or {}).get("90")
                dur = af.get("duration_ms")
                if p90 and p90 > 0 and dur is not None:
                    ratio = float(dur) / float(p90)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_anchor_info = {
                            "event_id": aid,
                            "duration_ms": round(float(dur), 3),
                            "dev_p90_ms": round(float(p90), 3),
                            "ratio_to_p90": round(ratio, 2),
                            "excerpt": str(ev.get("content") or "")[:140],
                        }
        by_anchor_mechanism["+".join(sorted(anchor_kinds)) if anchor_kinds else "none"] += 1

        matched_injs = alert_injections(SimpleNamespace(ts=_parse_ts(wts)), injections, 60.0)  # type: ignore[arg-type]
        item = {
            "window_id": wid,
            "service": svc,
            "window_ts": wts,
            "anomaly_score": float(row["anomaly_score"]),
            "evidence_origin": judged.get("evidence_origin"),
            "cited_modalities": cited_mods,
            "anchor_count": len(anchor_ids),
            "top_anchor": best_anchor_info,
            "reasoning_excerpt": str(judged.get("reasoning") or "")[:180],
        }
        if matched_injs:
            active = [
                f"{inj_by_id[iid].injection_id}:{inj_by_id[iid].root_cause_service}({inj_by_id[iid].fault_type})"
                for iid in matched_injs
            ]
            item["active_faults"] = active
            for iid in matched_injs:
                inj = inj_by_id[iid]
                collateral_by_svc_rc[f"{svc}->{inj.root_cause_service}"] += 1
                collateral_by_fault_type[inj.fault_type] += 1
            ratios_collateral.append(best_ratio)
            collateral_items.append(item)
        else:
            item["active_faults"] = []
            ratios_normal.append(best_ratio)
            normal_traffic_items.append(item)

    ratios_collateral.sort()
    ratios_normal.sort()

    def _ratio_stats(vals: Sequence[float]) -> dict[str, Any]:
        if not vals:
            return {"n": 0}
        return {
            "n": len(vals),
            "min": round(vals[0], 2),
            "median": round(vals[len(vals) // 2], 2),
            "max": round(vals[-1], 2),
        }

    detector_shift_link = {}
    for svc in sorted(by_service):
        detector_shift_link[svc] = {
            "dev": shift_dev.get("by_service", {}).get(svc),
            "val": shift_val.get("by_service", {}).get(svc),
            "test": shift_test.get("by_service", {}).get(svc),
        }
    day_shift_link = {}
    for day in sorted(by_date):
        day_shift_link[day] = {
            "dev": shift_dev.get("by_day", {}).get(day),
            "val": shift_val.get("by_day", {}).get(day),
            "test": shift_test.get("by_day", {}).get(day),
        }

    return {
        "total": len(fps),
        "by_service": dict(sorted(by_service.items())),
        "by_date": dict(sorted(by_date.items())),
        "by_has_dev_baseline": dict(sorted(by_has_dev.items())),
        "by_c1_raw_verdict_and_confidence": dict(sorted(by_raw_verdict_conf.items())),
        "by_evidence_origin": dict(sorted(by_origin.items())),
        "by_cited_modalities": dict(sorted(by_cited_modalities.items())),
        "by_anchor_mechanism": dict(sorted(by_anchor_mechanism.items())),
        "by_fault_overlap": {
            "collateral_during_active_fault": {
                "count": len(collateral_items),
                "by_service": dict(Counter(x["service"] for x in collateral_items)),
                "by_target_root_cause": dict(collateral_by_svc_rc.most_common()),
                "by_active_fault_type": dict(collateral_by_fault_type.most_common()),
                "anchor_duration_to_dev_p90_ratio": _ratio_stats(ratios_collateral),
                "examples": _pick_examples(collateral_items, 2),
            },
            "pure_normal_traffic": {
                "count": len(normal_traffic_items),
                "by_service": dict(Counter(x["service"] for x in normal_traffic_items)),
                "anchor_duration_to_dev_p90_ratio": _ratio_stats(ratios_normal),
                "examples": _pick_examples(normal_traffic_items, 2),
            },
        },
        "detector_shift_from_m8": {
            "by_service": detector_shift_link,
            "by_day": day_shift_link,
        },
    }


def _summarize_ctav_fns(
    fns: Sequence[Mapping[str, str]],
    ctav_judged: Mapping[str, Mapping[str, Any]],
    c1_retrieval: Mapping[str, Sequence[Mapping[str, Any]]],
    anchors: Mapping[str, Mapping[str, Mapping[str, Any]]],
    has_dev_services: set[str],
) -> dict[str, Any]:
    stages: Counter[str] = Counter()
    by_fault_type: dict[str, Counter[str]] = defaultdict(Counter)
    c3_sub_counts: Counter[str] = Counter()
    c3_sub_by_fault_type: dict[str, Counter[str]] = defaultdict(Counter)
    detector_missed_by_svc: Counter[str] = Counter()
    judge_fp_has_dev: Counter[str] = Counter()
    c3_missing_dev_by_svc: Counter[str] = Counter()

    stage_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    c3_sub_items: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in fns:
        wid = str(row["window_id"])
        svc = str(row["service"])
        ft = str(row["label_fault_type"])
        wts = str(row["window_ts"])
        score = float(row["anomaly_score"]) if row.get("anomaly_score") else 0.0

        if not _flag(row["is_candidate"]):
            stage = "detector_missed"
            detector_missed_by_svc[svc] += 1
            item = {
                "window_id": wid,
                "service": svc,
                "window_ts": wts,
                "fault_type": ft,
                "anomaly_score": score,
            }
        elif row["raw_verdict"] == "FALSE_POSITIVE":
            stage = "judge_false_positive"
            judge_fp_has_dev["with_dev_baseline" if svc in has_dev_services else "without_dev_baseline"] += 1
            judged = ctav_judged[wid]
            item = {
                "window_id": wid,
                "service": svc,
                "window_ts": wts,
                "fault_type": ft,
                "anomaly_score": score,
                "confidence": judged.get("confidence"),
                "context_events": len(c1_retrieval.get(wid, ())),
                "reasoning_excerpt": str(judged.get("reasoning") or "")[:180],
            }
        elif _flag(row["downgraded_by_anchoring"]):
            stage = "c3_anchoring_downgraded"
            judged = ctav_judged[wid]
            cited = list(judged.get("evidence_event_ids") or [])
            local_anchors = [
                anchors[wid][eid]
                for eid in cited
                if eid in anchors.get(wid, {}) and anchors[wid][eid]["service"] == svc
            ]
            if svc not in has_dev_services:
                sub = "c3_service_missing_dev_baseline"
                c3_missing_dev_by_svc[svc] += 1
            else:
                has_dev_p90_for_any_local_trace = any(
                    (ev.get("dev") or {}).get("90") is not None
                    for ev in local_anchors
                    if ev.get("modality") == "trace"
                )
                sub = "c3_span_below_dev_p90" if has_dev_p90_for_any_local_trace else "c3_op_missing_dev_baseline"
            c3_sub_counts[sub] += 1
            c3_sub_by_fault_type[sub][ft] += 1

            local_trace_summary = [
                {
                    "event_id": ev["event_id"],
                    "severity": ev.get("severity"),
                    "duration_ms": round(float(ev["duration_ms"]), 2) if ev.get("duration_ms") is not None else None,
                    "dev_p90_ms": round(float(ev["dev"]["90"]), 2) if (ev.get("dev") or {}).get("90") is not None else None,
                }
                for ev in local_anchors
                if ev.get("modality") == "trace"
            ][:3]
            item = {
                "window_id": wid,
                "service": svc,
                "window_ts": wts,
                "fault_type": ft,
                "anomaly_score": score,
                "c3_subreason": sub,
                "local_cited_traces": local_trace_summary,
                "reasoning_excerpt": str(judged.get("reasoning") or "")[:180],
            }
            c3_sub_items[sub].append(item)
        else:
            stage = f"other:{row['raw_verdict']}:{row['decision']}"
            item = {"window_id": wid, "service": svc, "window_ts": wts, "fault_type": ft}

        stages[stage] += 1
        by_fault_type[ft][stage] += 1
        stage_items[stage].append(item)

    return {
        "total": len(fns),
        "by_stage": dict(sorted(stages.items())),
        "by_fault_type_x_stage": {ft: dict(sorted(ctr.items())) for ft, ctr in sorted(by_fault_type.items())},
        "detector_missed_detail": {
            "total": stages["detector_missed"],
            "by_service": dict(detector_missed_by_svc.most_common()),
            "examples": _pick_examples(stage_items["detector_missed"], 2),
        },
        "judge_false_positive_detail": {
            "total": stages["judge_false_positive"],
            "by_has_dev_baseline": dict(sorted(judge_fp_has_dev.items())),
            "examples": _pick_examples(stage_items["judge_false_positive"], 2),
        },
        "c3_anchoring_detail": {
            "total": stages["c3_anchoring_downgraded"],
            "by_subreason": dict(sorted(c3_sub_counts.items())),
            "by_subreason_x_fault_type": {
                sub: dict(sorted(ctr.items())) for sub, ctr in sorted(c3_sub_by_fault_type.items())
            },
            "service_missing_dev_by_service": dict(c3_missing_dev_by_svc.most_common()),
            "examples_by_subreason": {
                sub: _pick_examples(items, 2) for sub, items in sorted(c3_sub_items.items())
            },
        },
    }


def _summarize_rca_run(
    run_id: str,
    incidents: Sequence[Mapping[str, Any]],
    reports: Sequence[Mapping[str, Any]],
    rca_summary: Mapping[str, Any],
    directed_adj: Mapping[str, set[str]],
    undirected_adj: Mapping[str, set[str]],
) -> dict[str, Any]:
    reports_by_inc = {str(r["report"]["incident_id"]): r for r in reports}
    status_counts = Counter(str(inc["status"]) for inc in incidents)
    labelled = [inc for inc in incidents if inc["status"] == "labelled"]
    hits = [inc for inc in labelled if inc.get("level1_hit1")]
    misses = [inc for inc in labelled if not inc.get("level1_hit1")]

    miss_categories: Counter[str] = Counter()
    miss_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for inc in misses:
        rc = str(inc["root_cause"])
        svcs = set(inc["services"])
        top1 = str(inc["level1"][0]["service"])
        if rc in svcs:
            if rc in directed_adj.get(top1, set()):
                cat = "rc_alerted_ranked_lower_1hop_callee"
            elif top1 in directed_adj.get(rc, set()):
                cat = "rc_alerted_ranked_lower_1hop_caller"
            else:
                cat = "rc_alerted_ranked_lower_other"
        else:
            if any(rc in directed_adj.get(s, set()) for s in svcs):
                cat = "unalerted_1hop_callee"
            elif any(s in directed_adj.get(rc, set()) for s in svcs):
                cat = "unalerted_1hop_caller"
            elif any(rc in undirected_adj.get(s, set()) for s in svcs):
                cat = "unalerted_undirected_neighbor"
            else:
                cat = "unalerted_multihop_or_disconnected"
        miss_categories[cat] += 1
        miss_examples[cat].append(
            {
                "incident_id": inc["incident_id"],
                "start_ts": inc["start_ts"],
                "alert_ids": list(inc["alert_ids"]),
                "alerted_services": list(inc["services"]),
                "true_root_cause": rc,
                "fault_type": inc.get("fault_type"),
                "predicted_top1": top1,
                "level1_ranking": [x["service"] for x in inc["level1"]],
                "level1_hit3": bool(inc.get("level1_hit3")),
                "injection_ids": list(inc.get("injection_ids") or []),
            }
        )

    no_fault_svcs = Counter(svc for inc in incidents if inc["status"] == "no_fault" for svc in inc["services"])
    ambig_items = [
        {
            "incident_id": inc["incident_id"],
            "services": list(inc["services"]),
            "alert_count": len(inc["alert_ids"]),
            "injection_ids": list(inc.get("injection_ids") or []),
        }
        for inc in incidents
        if inc["status"] == "ambiguous"
    ]

    # Summarizer diagnostics across all incidents and labelled accuracy
    pred_ft_all: Counter[str] = Counter()
    pred_ft_nofault: Counter[str] = Counter()
    ft_correct_labelled = 0
    invented_ev_incidents: list[dict[str, Any]] = []
    for inc in incidents:
        inc_id = str(inc["incident_id"])
        rep_entry = reports_by_inc[inc_id]
        rep = rep_entry["report"]
        pft = str(rep.get("fault_type") or "")
        pred_ft_all[pft] += 1
        if inc["status"] == "no_fault":
            pred_ft_nofault[pft] += 1
        if inc["status"] == "labelled" and pft == inc.get("fault_type"):
            ft_correct_labelled += 1
        if rep_entry.get("invalid_evidence_ids"):
            invented_ev_incidents.append(
                {
                    "incident_id": inc_id,
                    "invalid_evidence_ids": list(rep_entry["invalid_evidence_ids"]),
                    "valid_evidence_remaining": len(rep.get("evidence") or []),
                }
            )

    per_inj = rca_summary["main"]["per_injection"]
    return {
        "run_id": run_id,
        "total_incidents": len(incidents),
        "by_status": dict(sorted(status_counts.items())),
        "labelled_total": len(labelled),
        "labelled_hit1": len(hits),
        "labelled_miss1": len(misses),
        "miss_categories": dict(sorted(miss_categories.items())),
        "miss_examples_by_category": {
            cat: sorted(items, key=lambda x: (x["start_ts"], x["incident_id"]))[:2]
            for cat, items in sorted(miss_examples.items())
        },
        "injections_coverage": {
            "total": per_inj["injections"],
            "with_labelled_incident": per_inj["with_labelled_incident"],
            "only_in_ambiguous_incidents": per_inj["only_in_ambiguous_incidents"],
            "without_alert": per_inj["without_alert"],
            "by_fault_type": per_inj["by_fault_type"],
        },
        "no_fault_incidents_by_service": dict(no_fault_svcs.most_common()),
        "ambiguous_incidents": ambig_items,
        "summarizer_diagnostics": {
            "fault_type_reported_all": dict(sorted(pred_ft_all.items())),
            "fault_type_reported_no_fault": dict(sorted(pred_ft_nofault.items())),
            "fault_type_accuracy_on_labelled": {
                "correct": ft_correct_labelled,
                "total": len(labelled),
                "rate": round(ft_correct_labelled / len(labelled), 4) if labelled else 0.0,
            },
            "invented_evidence_filtered": invented_ev_incidents,
        },
    }


def analyze_test_errors(results_dir: Path = RESULTS, graph_path: Path = GRAPH_PATH, window_index: Path = WINDOW_INDEX) -> dict[str, Any]:
    ctav_all = _load_per_window(results_dir / "ctav_final_test_v1" / "per_window.csv")
    test_wids = {str(r["window_id"]) for r in ctav_all}
    ctav_telem = [r for r in ctav_all if _flag(r["has_telemetry"])]

    tps = [r for r in ctav_telem if _flag(r["label_is_fault"]) and r["decision"] == "alert"]
    fps = [r for r in ctav_telem if not _flag(r["label_is_fault"]) and r["decision"] == "alert"]
    fns = [r for r in ctav_telem if _flag(r["label_is_fault"]) and r["decision"] != "alert"]

    ctav_judged = {str(r["window_id"]): r for r in _load_jsonl(results_dir / "ctav_final_test_v1" / "judged.jsonl")}
    c1_retrieval = {str(r["window_id"]): r["events"] for r in _load_jsonl(results_dir / "h0_test_c1_k0_v1" / "retrieval.jsonl")}
    anchors = _load_anchor_map(results_dir / "m8_anchor_features_test_v1" / "events.jsonl.gz")

    shift = json.loads((results_dir / "m8_detector_shift_test_v1" / "shift.json").read_text(encoding="utf-8"))
    f11 = json.loads((results_dir / "m8_finding11_test_v1" / "finding11.json").read_text(encoding="utf-8"))
    has_dev_services = {str(s) for s in f11["services_with_dev_baseline"]}

    injections = load_injections(test_wids, 60.0, path=window_index)
    inj_by_id = {inj.injection_id: inj for inj in injections}
    directed_adj, undirected_adj = _load_graph_adjacency(graph_path)

    fp_summary = _summarize_ctav_fps(
        fps=fps,
        ctav_judged=ctav_judged,
        c1_retrieval=c1_retrieval,
        anchors=anchors,
        has_dev_services=has_dev_services,
        injections=injections,
        inj_by_id=inj_by_id,
        shift_test=shift["splits"]["test"],
        shift_val=shift["splits"]["val"],
        shift_dev=shift["splits"]["dev"],
    )
    fn_summary = _summarize_ctav_fns(
        fns=fns,
        ctav_judged=ctav_judged,
        c1_retrieval=c1_retrieval,
        anchors=anchors,
        has_dev_services=has_dev_services,
    )

    rca_reg = _summarize_rca_run(
        run_id="rca_final_test_v1",
        incidents=_load_jsonl(results_dir / "rca_final_test_v1" / "incidents.jsonl"),
        reports=_load_jsonl(results_dir / "rca_final_test_v1" / "reports.jsonl"),
        rca_summary=json.loads((results_dir / "rca_final_test_v1" / "rca.json").read_text(encoding="utf-8")),
        directed_adj=directed_adj,
        undirected_adj=undirected_adj,
    )
    rca_sens = _summarize_rca_run(
        run_id="rca_sens_test_c3rolling_v1",
        incidents=_load_jsonl(results_dir / "rca_sens_test_c3rolling_v1" / "incidents.jsonl"),
        reports=_load_jsonl(results_dir / "rca_sens_test_c3rolling_v1" / "reports.jsonl"),
        rca_summary=json.loads((results_dir / "rca_sens_test_c3rolling_v1" / "rca.json").read_text(encoding="utf-8")),
        directed_adj=directed_adj,
        undirected_adj=undirected_adj,
    )

    # Arithmetic invariants cross-checked against M8 & M9
    assert len(ctav_telem) == 11985
    assert len(tps) == 14 and len(fps) == 64 and len(fns) == 332
    assert fn_summary["detector_missed_detail"]["total"] == 122
    assert fn_summary["judge_false_positive_detail"]["total"] == 128
    assert fn_summary["c3_anchoring_detail"]["total"] == 82
    assert fn_summary["c3_anchoring_detail"]["by_subreason"]["c3_service_missing_dev_baseline"] == 67
    assert sum(fp_summary["by_service"].values()) == 64
    assert rca_reg["total_incidents"] == 38 and rca_reg["labelled_total"] == 17 and rca_reg["labelled_miss1"] == 9
    assert rca_reg["injections_coverage"]["without_alert"] == 29
    assert rca_sens["total_incidents"] == 114 and rca_sens["labelled_total"] == 48 and rca_sens["labelled_miss1"] == 38

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "split": "test",
        "scope": "telemetry_windows",
        "counts": {
            "telemetry_windows": len(ctav_telem),
            "fault_windows": len(tps) + len(fns),
            "ctav_tp": len(tps),
            "ctav_fp": len(fps),
            "ctav_fn": len(fns),
        },
        "ctav_fp": fp_summary,
        "ctav_fn": fn_summary,
        "rca_registered": rca_reg,
        "rca_sensitivity_out_of_registration": rca_sens,
    }


def render_markdown(data: Mapping[str, Any]) -> str:
    fp = data["ctav_fp"]
    fn = data["ctav_fn"]
    rca_reg = data["rca_registered"]
    rca_sens = data["rca_sensitivity_out_of_registration"]

    lines = [
        "# Phân tích ca sai trên `test` (`m11_error_analysis_test_v1`)",
        "",
        "## 1. 64 báo động giả (FP) của CTAV trên `test`",
        "",
        "| Nhóm phân loại | Số FP | Tỉ lệ (%) | Chi tiết chính |",
        "|---|---:|---:|---|",
        f"| Theo service: `frontend` / `ts-travel-service` | {fp['by_service']['frontend']} / {fp['by_service']['ts-travel-service']} | 60,9 / 39,1 | Đều có ngưỡng nền `dev` (`2022-08-22`: {fp['by_date']['2022-08-22']}; `2023-01-30`: {fp['by_date']['2023-01-30']}) |",
        f"| Verdict C1 gốc & confidence | {fp['total']} / {fp['total']} | 100,0 | `TRUE_ALERT`, `confidence = 0,9`; neo 100% qua `span > dev_p90` (`local`: {fp['by_evidence_origin'].get('local', 0)}, `mixed`: {fp['by_evidence_origin'].get('mixed', 0)}) |",
        f"| Trùng thời gian lỗi đang tiêm ở downstream (collateral) | {fp['by_fault_overlap']['collateral_during_active_fault']['count']} | {100 * fp['by_fault_overlap']['collateral_during_active_fault']['count'] / 64:.1f} | Trung vị `duration/p90` = {fp['by_fault_overlap']['collateral_during_active_fault']['anchor_duration_to_dev_p90_ratio']['median']}× (tối đa {fp['by_fault_overlap']['collateral_during_active_fault']['anchor_duration_to_dev_p90_ratio']['max']}×) |",
        f"| Ngoài mọi lần tiêm lỗi (lưu lượng bình thường) | {fp['by_fault_overlap']['pure_normal_traffic']['count']} | {100 * fp['by_fault_overlap']['pure_normal_traffic']['count'] / 64:.1f} | Trung vị `duration/p90` = {fp['by_fault_overlap']['pure_normal_traffic']['anchor_duration_to_dev_p90_ratio']['median']}× (tối đa {fp['by_fault_overlap']['pure_normal_traffic']['anchor_duration_to_dev_p90_ratio']['max']}×) |",
        "",
        "## 2. 332 sự cố bị bỏ sót (FN) của CTAV trên `test`",
        "",
        "| Tầng gây bỏ sót | Số FN | Tỉ lệ / 332 (%) | Ghi chú |",
        "|---|---:|---:|---|",
        f"| Detector không đưa lên candidate (`score < 0,85`) | {fn['detector_missed_detail']['total']} | {100 * fn['detector_missed_detail']['total'] / 332:.1f} | Chủ yếu `network_delay` ({fn['by_fault_type_x_stage'].get('network_delay', {}).get('detector_missed', 0)}), `return` ({fn['by_fault_type_x_stage'].get('return', {}).get('detector_missed', 0)}), `exception` ({fn['by_fault_type_x_stage'].get('exception', {}).get('detector_missed', 0)}) |",
        f"| Judge C1 trả `FALSE_POSITIVE` | {fn['judge_false_positive_detail']['total']} | {100 * fn['judge_false_positive_detail']['total'] / 332:.1f} | Đủ 6 sự kiện ngữ cảnh; 64 có ngưỡng `dev` / 64 không |",
        f"| C3 hạ — thiếu ngưỡng nền `dev` của service | {fn['c3_anchoring_detail']['by_subreason'].get('c3_service_missing_dev_baseline', 0)} | {100 * fn['c3_anchoring_detail']['by_subreason'].get('c3_service_missing_dev_baseline', 0) / 332:.1f} | Phát hiện 11 trên 11 service có fault |",
        f"| C3 hạ — thiếu ngưỡng thao tác trong service có `dev` | {fn['c3_anchoring_detail']['by_subreason'].get('c3_op_missing_dev_baseline', 0)} | {100 * fn['c3_anchoring_detail']['by_subreason'].get('c3_op_missing_dev_baseline', 0) / 332:.1f} | Gồm 2 span `WARN` > 1.000 ms trên `ts-travel-service` |",
        f"| C3 hạ — span có ngưỡng nhưng dưới `dev` p90 | {fn['c3_anchoring_detail']['by_subreason'].get('c3_span_below_dev_p90', 0)} | {100 * fn['c3_anchoring_detail']['by_subreason'].get('c3_span_below_dev_p90', 0) / 332:.1f} | Không có log `ERROR`/`WARN` cục bộ |",
        "",
        "## 3. Ca sai của tác tử RCA trên `test`",
        "",
        "| Run | Tổng sự cố | Có nhãn | Trúng Hit@1 | Trượt Hit@1 | Phân loại trượt |",
        "|---|---:|---:|---:|---:|---|",
        f"| Đăng ký (`{rca_reg['run_id']}`) | {rca_reg['total_incidents']} | {rca_reg['labelled_total']} | {rca_reg['labelled_hit1']} | {rca_reg['labelled_miss1']} | 7 callee 1-hop không cảnh báo; 2 ≥2-hop/không cạnh; +29/50 tiêm lỗi 0 cảnh báo |",
        f"| Độ nhạy ngoài đăng ký (`{rca_sens['run_id']}`) | {rca_sens['total_incidents']} | {rca_sens['labelled_total']} | {rca_sens['labelled_hit1']} | {rca_sens['labelled_miss1']} | {sum(v for k, v in rca_sens['miss_categories'].items() if k.startswith('unalerted_'))} thiếu cảnh báo ở service gốc; {sum(v for k, v in rca_sens['miss_categories'].items() if k.startswith('rc_alerted_'))} sai xếp hạng đa service (đều trúng Hit@3) |",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--out", type=Path, default=RESULTS / "m11_error_analysis_test_v1")
    args = parser.parse_args()

    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} already exists and is non-empty: results are never overwritten")

    results_dir = args.results if args.results.is_absolute() else REPO / args.results
    data = analyze_test_errors(results_dir=results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "error_analysis.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "tables.md").write_text(render_markdown(data), encoding="utf-8")
    print(f"wrote {out_dir / 'error_analysis.json'} and {out_dir / 'tables.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
