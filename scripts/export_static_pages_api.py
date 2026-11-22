"""Export verified M8/M9/M10 pipeline runs to a static JSON API mirror for GitHub Pages.

    py scripts/export_static_pages_api.py --out services/web/public/static-api

Reads strictly from frozen result artifacts under `eval/results/` and `data/graph/`
(0 live LLM API calls, 0 Docker/ClickHouse/PostgreSQL dependency) and emits JSON files
conforming 100% to `services/api/schemas.py` (`services/web/src/api/types.ts`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast

import yaml

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from packages.graph.service_graph import ServiceGraph, load_graph
from packages.schemas.models import DiagnosticReport
from services.api.readers import (
    C1_FUSION_WEIGHTS,
    DEFAULT_DETECTOR_THRESHOLD,
    _edges_used_count,
    _extract_window_id,
    _infer_strategy,
    _normalize_origin,
    _normalize_verdict,
    _sanitize_debug,
    get_run_metrics,
)
from services.api.schemas import (
    AlertDetailResponse,
    AlertResponse,
    ContextEventResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphRole,
    GroupingReasonResponse,
    IncidentDetailResponse,
    IncidentResponse,
    MetricPointResponse,
    RunResponse,
    SearchScopeEntryResponse,
    WindowLabelResponse,
)
from services.rca_agent.pipeline import (
    LoadedAlerts,
    load_alerts,
    load_alerts_from_ctav_variant,
)

DEFAULT_RUN_IDS = ("pipeline_test_v2", "pipeline_val_v2", "pipeline_sens_test_v1")
RESULTS_DIR = REPO / "eval" / "results"
DEMO_CASES_PATH = RESULTS_DIR / "m10_demo_cases_v1" / "demo_cases.json"


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw).astimezone(UTC)


def _write_json(path: Path, payload: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(raw, encoding="utf-8")
    return len(raw.encode("utf-8"))


def _collect_demo_window_ids(demo_cases: Mapping[str, Any]) -> set[str]:
    """Collect every window_id mentioned anywhere in demo_cases.json."""
    out: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, Mapping):
            wid = node.get("window_id")
            if isinstance(wid, str) and wid:
                out.add(wid)
            aid = node.get("alert_id")
            if isinstance(aid, str) and aid:
                out.add(_extract_window_id(aid))
            for val in node.values():
                _walk(val)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(demo_cases)
    return out


def _eval_row_to_alert(row: Mapping[str, Any]) -> AlertResponse:
    strategy = str(row.get("retrieval_strategy") or "hybrid_bm25_graph")
    verdict = _normalize_verdict(str(row.get("verdict") or "UNCERTAIN"))
    raw_verdict = _normalize_verdict(str(row.get("raw_verdict") or ""), fallback=verdict)
    is_fault = bool(row.get("label_is_fault"))
    raw_ft = str(row.get("label_fault_type") or "")
    fault_type = raw_ft if is_fault and raw_ft not in ("", "none", "normal") else None
    raw_rc = str(row.get("label_root_cause") or "")
    root_cause = raw_rc if is_fault and raw_rc else None
    window_id = str(row["window_id"])
    window_ts = row["window_ts"]
    ts = _utc(window_ts) if isinstance(window_ts, datetime) else _parse_ts(str(window_ts))

    return AlertResponse(
        alert_id=f"cand-{window_id}:{strategy}:r0",
        candidate_id=f"cand-{window_id}",
        window_id=window_id,
        run_id=str(row["run_id"]),
        service=str(row["service"]),
        ts=ts,
        anomaly_score=float(row["anomaly_score"]),
        candidate_source="rescue" if row.get("candidate_source") == "rescue" else "metric",
        rescue_score=float(row["rescue_score"]) if row.get("rescue_score") is not None else None,
        rescue_components=None,
        retrieval_strategy=strategy,
        retrieval_latency_ms=float(row.get("retrieval_latency_ms") or 0.0),
        context_event_count=int(row.get("context_event_count") or 0),
        context_tokens=int(row.get("context_tokens") or 0),
        retrieval_truncated=bool(row.get("retrieval_truncated")),
        verdict=verdict,
        confidence=float(row.get("confidence") or 0.0),
        judge_backend=str(row.get("judge_backend") or ""),
        llm_latency_ms=float(row.get("llm_latency_ms") or 0.0),
        cache_hit=bool(row.get("cache_hit")),
        downgraded_by_evidence_rule=bool(row.get("downgraded")),
        raw_verdict=raw_verdict,
        routing_tier=int(row.get("routing_tier") or 1),
        evidence_origin=_normalize_origin(str(row.get("evidence_origin") or "none")),
        threshold_applied=(
            float(row["threshold_applied"]) if row.get("threshold_applied") is not None else None
        ),
        downgraded_by_gating=bool(row.get("downgraded_gating")),
        downgraded_by_anchoring=bool(row.get("downgraded_anchoring")),
        label=WindowLabelResponse(
            is_fault=is_fault,
            fault_type=fault_type,
            root_cause_service=root_cause,
        ),
    )


def _build_per_window_series(
    per_window_rows: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str], dict[str, list[tuple[datetime, float]]]]:
    win_to_pod: dict[str, str] = {}
    by_pod: dict[str, list[tuple[datetime, float]]] = {}
    for row in per_window_rows:
        wid = row["window_id"]
        pod = row.get("pod") or row["service"]
        ts = _parse_ts(row["window_ts"])
        score = float(row["anomaly_score"]) if row.get("anomaly_score") else 0.0
        win_to_pod[wid] = pod
        by_pod.setdefault(pod, []).append((ts, score))
    for points in by_pod.values():
        points.sort(key=lambda pair: pair[0])
    return win_to_pod, by_pod


def _load_judged_reasoning(
    run_cfg: Mapping[str, Any],
    results_dir: Path,
) -> dict[str, tuple[str, list[str]]]:
    """Load (reasoning, evidence_event_ids) for every candidate window of a run."""
    inp = run_cfg.get("input") or {}
    alerts_run = inp.get("alerts_run")
    if not alerts_run and inp.get("ctav_config"):
        ctav_cfg = yaml.safe_load((REPO / str(inp["ctav_config"])).read_text(encoding="utf-8")) or {}
        alerts_run = ctav_cfg.get("run_id")

    index: dict[str, tuple[str, list[str]]] = {}
    if alerts_run:
        jpath = results_dir / str(alerts_run) / "judged.jsonl"
        if jpath.exists():
            with jpath.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    index[str(row["window_id"])] = (
                        str(row.get("reasoning") or ""),
                        [str(x) for x in (row.get("evidence_event_ids") or [])],
                    )
    return index


def _select_detail_windows(
    alerts: Sequence[AlertResponse],
    demo_window_ids: set[str],
    extra_limit: int,
) -> set[str]:
    """Select candidate windows to receive full pre-exported AlertDetail JSON."""
    selected: set[str] = set()
    for a in alerts:
        if a.verdict == "TRUE_ALERT" or a.window_id in demo_window_ids:
            selected.add(a.window_id)

    if extra_limit <= 0:
        return selected

    c3_downgraded = [
        a.window_id
        for a in alerts
        if a.window_id not in selected and a.downgraded_by_anchoring and a.context_event_count > 0
    ]
    with_context = [
        a.window_id
        for a in alerts
        if a.window_id not in selected
        and not a.downgraded_by_anchoring
        and a.context_event_count > 0
    ]

    # Take evenly spaced samples across the timeline so browsing anywhere has rich examples.
    def _sample_even(items: list[str], quota: int) -> list[str]:
        if len(items) <= quota:
            return items
        step = len(items) / quota
        return [items[int(i * step)] for i in range(quota)]

    c3_quota = min(len(c3_downgraded), max(extra_limit // 2, extra_limit - len(with_context)))
    rem_quota = max(0, extra_limit - c3_quota)
    selected.update(_sample_even(c3_downgraded, c3_quota))
    selected.update(_sample_even(with_context, rem_quota))
    return selected


def _build_alert_detail(
    alert: AlertResponse,
    trace_rows: Sequence[Mapping[str, Any]],
    reasoning: str,
    evidence_ids: list[str],
    win_to_pod: Mapping[str, str],
    by_pod: Mapping[str, list[tuple[datetime, float]]],
    graph: ServiceGraph,
) -> AlertDetailResponse:
    events: list[ContextEventResponse] = []
    for tr in sorted(trace_rows, key=lambda r: int(r.get("rank") or 0)):
        raw_debug = json.loads(tr["debug_json"]) if tr.get("debug_json") else {}
        content = str(raw_debug.get("content") or "")
        debug = _sanitize_debug(raw_debug)
        debug.setdefault("rank", int(tr.get("rank") or 0))
        debug["origin"] = str(tr.get("origin") or "local")
        if tr.get("graph_distance") is not None:
            debug["graph_distance"] = int(tr["graph_distance"])
        mod_raw = str(tr.get("modality") or "trace")
        mod: Literal["log", "trace", "metric"] = (
            cast(Literal["log", "trace", "metric"], mod_raw)
            if mod_raw in ("log", "trace", "metric")
            else "trace"
        )
        ev_ts = tr["event_ts"]
        ts = _utc(ev_ts) if isinstance(ev_ts, datetime) else _parse_ts(str(ev_ts))
        events.append(
            ContextEventResponse(
                event_id=str(tr["event_id"]),
                modality=mod,
                ts=ts,
                service=str(tr["service"]),
                content=content,
                score=float(tr["score"]),
                debug=debug,
            )
        )

    pod = win_to_pod.get(alert.window_id)
    series: list[MetricPointResponse] = []
    if pod is not None:
        lo = alert.ts - timedelta(minutes=16)
        hi = alert.ts + timedelta(minutes=7)
        series = [
            MetricPointResponse(ts=ts, value=score)
            for ts, score in by_pod.get(pod, ())
            if lo <= ts <= hi
        ]
    if not series:
        series = [MetricPointResponse(ts=alert.ts, value=alert.anomaly_score)]

    built_by_c1 = any("graph_sim" in e.debug for e in events)
    search_scope: list[SearchScopeEntryResponse] = []
    if built_by_c1:
        hops = graph.distances(alert.service, C1_FUSION_WEIGHTS.graph_max_distance)
        search_scope = [
            SearchScopeEntryResponse(service=svc, distance=int(d))
            for svc, d in sorted(hops.items(), key=lambda kv: (kv[1], kv[0]))
        ]
        if not search_scope:
            search_scope = [SearchScopeEntryResponse(service=alert.service, distance=0)]

    return AlertDetailResponse(
        **alert.model_dump(),
        reasoning=reasoning,
        evidence_event_ids=evidence_ids,
        context_events=events,
        metric_series=series,
        metric_name="anomaly_score (Isolation Forest)",
        detector_threshold=DEFAULT_DETECTOR_THRESHOLD,
        search_scope=search_scope,
        fusion_weights=C1_FUSION_WEIGHTS if built_by_c1 else None,
    )


def _build_incidents(
    run_id: str,
    run_dir: Path,
    alerts_by_window: Mapping[str, AlertResponse],
    graph: ServiceGraph,
) -> tuple[list[IncidentResponse], dict[str, IncidentDetailResponse]]:
    inc_path = run_dir / "incidents.jsonl"
    rep_path = run_dir / "reports.jsonl"
    rej_path = run_dir / "rejected.jsonl"

    reports_by_inc: dict[str, DiagnosticReport] = {}
    if rep_path.exists():
        for line in rep_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            rep_obj = rec.get("report") if isinstance(rec.get("report"), Mapping) else rec
            report = DiagnosticReport.model_validate(rep_obj)
            reports_by_inc[report.incident_id] = report

    rejected_by_inc: dict[str, str] = {}
    if rej_path.exists():
        for line in rej_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("incident_id"):
                rejected_by_inc[str(rec["incident_id"])] = str(
                    rec.get("reject_reason") or rec.get("reason") or "rejected"
                )

    raw_incidents: list[dict[str, Any]] = []
    if inc_path.exists():
        for line in inc_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                raw_incidents.append(json.loads(line))
    raw_incidents.sort(key=lambda r: (_parse_ts(str(r["start_ts"])), str(r["incident_id"])))

    summaries: list[IncidentResponse] = []
    details: dict[str, IncidentDetailResponse] = {}
    directed = graph.directed

    for r in raw_incidents:
        iid = str(r["incident_id"])
        alert_ids = [str(x) for x in (r.get("alert_ids") or [])]
        services = [str(x) for x in (r.get("services") or [])]
        gr = r.get("grouping_reason") or {}
        report = reports_by_inc.get(iid)
        root_cause_service = report.root_cause_service if report is not None else None
        gt_service = str(r["root_cause"]) if r.get("root_cause") else None
        fault_type = str(r["fault_type"]) if r.get("fault_type") else None

        member_alerts = sorted(
            (
                alerts_by_window[_extract_window_id(aid)]
                for aid in alert_ids
                if _extract_window_id(aid) in alerts_by_window
            ),
            key=lambda a: (a.ts, a.window_id),
        )

        alert_count_by_svc: dict[str, int] = {}
        max_score_by_svc: dict[str, float] = {}
        for a in member_alerts:
            alert_count_by_svc[a.service] = alert_count_by_svc.get(a.service, 0) + 1
            max_score_by_svc[a.service] = max(max_score_by_svc.get(a.service, 0.0), a.anomaly_score)

        involved: set[str] = set(services)
        if root_cause_service:
            involved.add(root_cause_service)
        if gt_service:
            involved.add(gt_service)
        if report:
            involved.update(report.propagation_path)

        present: set[str] = set(involved)
        for svc in list(involved):
            if svc in directed:
                present.update(directed.predecessors(svc))
                present.update(directed.successors(svc))

        nodes: list[GraphNodeResponse] = []
        for svc in sorted(present):
            role: GraphRole
            if svc == root_cause_service:
                role = "root_cause"
            elif svc == gt_service:
                role = "ground_truth"
            elif svc in involved:
                role = "affected"
            else:
                role = "healthy"
            nodes.append(
                GraphNodeResponse(
                    service=svc,
                    role=role,
                    alert_count=alert_count_by_svc.get(svc, 0),
                    max_anomaly_score=max_score_by_svc.get(svc, 0.0),
                )
            )

        path_seq = report.propagation_path if report else services
        path_pairs = {f"{path_seq[i]}->{path_seq[i + 1]}" for i in range(len(path_seq) - 1)}
        edges: list[GraphEdgeResponse] = []
        for u, v, data in sorted(directed.edges(data=True)):
            if u in present and v in present:
                edges.append(
                    GraphEdgeResponse(
                        source=str(u),
                        target=str(v),
                        call_count=int(data.get("weight", 1)),
                        error_rate=0.0,
                        on_path=f"{v}->{u}" in path_pairs,
                    )
                )

        summary = IncidentResponse(
            incident_id=iid,
            run_id=run_id,
            alert_ids=alert_ids,
            services=services,
            start_ts=_parse_ts(str(r["start_ts"])),
            end_ts=_parse_ts(str(r["end_ts"])),
            grouping_reason=GroupingReasonResponse(
                temporal_window_sec=float(gr.get("temporal_window_sec") or 180.0),
                graph_edges_used=_edges_used_count(gr),
            ),
            root_cause_service=root_cause_service,
            ground_truth_service=gt_service,
            fault_type=fault_type,
        )
        summaries.append(summary)
        details[iid] = IncidentDetailResponse(
            **summary.model_dump(),
            nodes=nodes,
            edges=edges,
            report=report,
            rejected_reason=rejected_by_inc.get(iid),
            alerts=member_alerts,
        )

    return summaries, details


ALERT_TABLE_COLUMNS = (
    "alert_id",
    "candidate_id",
    "window_id",
    "run_id",
    "service",
    "ts",
    "anomaly_score",
    "candidate_source",
    "rescue_score",
    "retrieval_strategy",
    "retrieval_latency_ms",
    "context_event_count",
    "context_tokens",
    "retrieval_truncated",
    "verdict",
    "confidence",
    "judge_backend",
    "llm_latency_ms",
    "cache_hit",
    "downgraded_by_evidence_rule",
    "raw_verdict",
    "routing_tier",
    "evidence_origin",
    "threshold_applied",
    "downgraded_by_gating",
    "downgraded_by_anchoring",
    "label_is_fault",
    "label_fault_type",
    "label_root_cause_service",
)


def _pack_alerts_table(alerts: Sequence[AlertResponse]) -> dict[str, Any]:
    """Pack alerts into a lossless {columns, rows} table to cut static JSON size by ~65%."""
    rows: list[list[Any]] = []
    for a in alerts:
        d = a.model_dump(mode="json")
        lbl = d["label"]
        rows.append([
            d["alert_id"],
            d["candidate_id"],
            d["window_id"],
            d["run_id"],
            d["service"],
            d["ts"],
            round(float(d["anomaly_score"]), 6),
            d["candidate_source"],
            d["rescue_score"],
            d["retrieval_strategy"],
            round(float(d["retrieval_latency_ms"]), 3),
            d["context_event_count"],
            d["context_tokens"],
            d["retrieval_truncated"],
            d["verdict"],
            d["confidence"],
            d["judge_backend"],
            round(float(d["llm_latency_ms"]), 3),
            d["cache_hit"],
            d["downgraded_by_evidence_rule"],
            d["raw_verdict"],
            d["routing_tier"],
            d["evidence_origin"],
            d["threshold_applied"],
            d["downgraded_by_gating"],
            d["downgraded_by_anchoring"],
            lbl["is_fault"],
            lbl["fault_type"],
            lbl["root_cause_service"],
        ])
    return {"columns": list(ALERT_TABLE_COLUMNS), "rows": rows}


def export_static_api(
    out_dir: Path,
    run_ids: Sequence[str] = DEFAULT_RUN_IDS,
    extra_details_per_run: int = 150,
    results_dir: Path = RESULTS_DIR,
) -> dict[str, Any]:
    """Export all requested pipeline runs to `out_dir` and return a verification summary."""
    graph = load_graph()
    demo_cases: dict[str, Any] = (
        json.loads(DEMO_CASES_PATH.read_text(encoding="utf-8"))
        if DEMO_CASES_PATH.exists()
        else {}
    )
    demo_window_ids = _collect_demo_window_ids(demo_cases)

    runs_out: list[RunResponse] = []
    incident_index: dict[str, str] = {}
    summary: dict[str, Any] = {"runs": {}, "total_bytes": 0}

    for run_id in run_ids:
        run_dir = results_dir / run_id
        cfg_text = (run_dir / "config.snapshot.yaml").read_text(encoding="utf-8")
        run_cfg = yaml.safe_load(cfg_text) or {}
        runtime = json.loads((run_dir / "runtime.json").read_text(encoding="utf-8"))
        git_commit = (
            (run_dir / "git_commit.txt").read_text(encoding="utf-8").splitlines()[0].strip()
            if (run_dir / "git_commit.txt").exists()
            else ""
        )

        inp = run_cfg.get("input") or {}
        evidence_run = str(inp["evidence_run"])
        if inp.get("alerts_run"):
            loaded: LoadedAlerts = load_alerts(
                alerts_run=str(inp["alerts_run"]),
                evidence_run=evidence_run,
                run_id=run_id,
                results_root=results_dir,
            )
        else:
            loaded, _, _ = load_alerts_from_ctav_variant(
                source_cfg=inp,
                expected_split=str(run_cfg["split"]),
                evidence_run=evidence_run,
                run_id=run_id,
                results_root=results_dir,
            )

        alerts = sorted(
            (_eval_row_to_alert(row) for row in loaded.eval_rows),
            key=lambda a: (a.ts, a.window_id),
        )
        alerts_by_window = {a.window_id: a for a in alerts}
        confirmed_count = sum(1 for a in alerts if a.verdict == "TRUE_ALERT")

        expected_counts = runtime.get("counts") or {}
        if len(alerts) != int(expected_counts.get("candidates_loaded", len(alerts))):
            raise RuntimeError(
                f"{run_id}: alert count {len(alerts)} != runtime {expected_counts.get('candidates_loaded')}"
            )
        if confirmed_count != int(expected_counts.get("confirmed_alerts", confirmed_count)):
            raise RuntimeError(
                f"{run_id}: TRUE_ALERT count {confirmed_count} != runtime {expected_counts.get('confirmed_alerts')}"
            )

        # Group retrieval trace rows by window_id.
        traces_by_window: dict[str, list[dict[str, Any]]] = {}
        for tr in loaded.trace_rows:
            traces_by_window.setdefault(str(tr["window_id"]), []).append(tr)

        reasoning_index = _load_judged_reasoning(run_cfg, results_dir)
        win_to_pod, by_pod = _build_per_window_series(loaded.inputs.rows)

        detail_windows = _select_detail_windows(alerts, demo_window_ids, extra_details_per_run)
        alert_details_map: dict[str, Any] = {}
        for wid in sorted(detail_windows):
            alert = alerts_by_window[wid]
            reasoning, ev_ids = reasoning_index.get(wid, ("", []))
            detail = _build_alert_detail(
                alert=alert,
                trace_rows=traces_by_window.get(wid, ()),
                reasoning=reasoning,
                evidence_ids=ev_ids,
                win_to_pod=win_to_pod,
                by_pod=by_pod,
                graph=graph,
            )
            alert_details_map[alert.alert_id] = detail.model_dump(mode="json")

        inc_summaries, inc_details = _build_incidents(run_id, run_dir, alerts_by_window, graph)
        if len(inc_summaries) != int(expected_counts.get("incidents", len(inc_summaries))):
            raise RuntimeError(
                f"{run_id}: incident count {len(inc_summaries)} != runtime {expected_counts.get('incidents')}"
            )
        for inc in inc_summaries:
            incident_index[inc.incident_id] = run_id

        finished_at = _parse_ts(str(runtime["finished_at"]))
        wall_ms = float((runtime.get("stages_ms") or {}).get("e2e_wall_ms") or 0.0)
        started_at = finished_at - timedelta(milliseconds=wall_ms)
        notes = (
            "Sensitivity line (c3_rolling_baseline) — outside pre-registered H5"
            if "sens" in run_id
            else f"Verified M10 pipeline run ({runtime.get('reference_run_id', '')})"
        )
        runs_out.append(
            RunResponse(
                run_id=run_id,
                retrieval_strategy=_infer_strategy(cfg_text),
                split=str(runtime.get("split") or run_cfg.get("split") or "test"),
                seed=int(run_cfg.get("seed") or 42),
                git_commit=git_commit,
                started_at=started_at,
                finished_at=finished_at,
                status="done",
                notes=notes,
                alert_count=len(alerts),
            )
        )

        metrics = get_run_metrics(run_id)
        if metrics is None:
            raise RuntimeError(f"{run_id}: failed to compute RunMetricsResponse")

        b_metrics = _write_json(out_dir / "metrics" / f"{run_id}.json", metrics.model_dump(mode="json"))
        b_alerts = _write_json(
            out_dir / "alerts" / f"{run_id}.json",
            _pack_alerts_table(alerts),
        )
        b_adetails = _write_json(out_dir / "alert_details" / f"{run_id}.json", alert_details_map)
        b_incs = _write_json(
            out_dir / "incidents" / f"{run_id}.json",
            [i.model_dump(mode="json") for i in inc_summaries],
        )
        b_idetails = _write_json(
            out_dir / "incident_details" / f"{run_id}.json",
            {iid: det.model_dump(mode="json") for iid, det in inc_details.items()},
        )
        run_bytes = b_metrics + b_alerts + b_adetails + b_incs + b_idetails
        summary["total_bytes"] += run_bytes
        summary["runs"][run_id] = {
            "alerts": len(alerts),
            "true_alerts": confirmed_count,
            "alert_details": len(alert_details_map),
            "incidents": len(inc_summaries),
            "bytes": run_bytes,
        }

    b_runs = _write_json(out_dir / "runs.json", [r.model_dump(mode="json") for r in runs_out])
    b_idx = _write_json(out_dir / "incident_index.json", incident_index)
    b_demo = _write_json(out_dir / "demo_cases.json", demo_cases) if demo_cases else 0
    summary["total_bytes"] += b_runs + b_idx + b_demo
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO / "services" / "web" / "public" / "static-api",
        help="Destination directory for static API JSON files.",
    )
    parser.add_argument(
        "--runs",
        nargs="+",
        default=list(DEFAULT_RUN_IDS),
        help="Pipeline run IDs to export (first entry becomes default in UI).",
    )
    parser.add_argument(
        "--extra-details-per-run",
        type=int,
        default=150,
        help="Extra non-TRUE_ALERT candidate details to pre-export per run.",
    )
    args = parser.parse_args(argv)
    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    summary = export_static_api(
        out_dir=out_dir,
        run_ids=args.runs,
        extra_details_per_run=args.extra_details_per_run,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
