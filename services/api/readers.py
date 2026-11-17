"""Read-only database and result-artifact readers for `services/api` (M10-B).

PostgreSQL reading lives here rather than in `services/rca_agent/store.py` (V47 (a), QD-045).
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

import psycopg
import yaml
from psycopg.rows import dict_row

from packages.graph.service_graph import ServiceGraph, load_graph
from packages.schemas.models import DiagnosticReport
from packages.storage import clickhouse
from services.api.schemas import (
    AlertDetailResponse,
    AlertResponse,
    ContextEventResponse,
    EvidenceOrigin,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphRole,
    GroupingReasonResponse,
    IncidentDetailResponse,
    IncidentResponse,
    MetricPointResponse,
    MetricWithCIResponse,
    RescueComponentsResponse,
    RunMetricsResponse,
    RunResponse,
    Verdict,
    WindowLabelResponse,
)

REPO = Path(__file__).resolve().parents[2]
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", str(REPO / "eval" / "results")))
DEFAULT_DETECTOR_THRESHOLD = 0.85

_ALERT_ID_RE = re.compile(r"^cand-([^:]+):([^:]+):r\d+$")
_ALERT_SELECT_COLS = (
    "run_id, window_id, service, window_ts, anomaly_score, candidate_source, "
    "rescue_score, rescue_lambda_log, rescue_phi_topo, rescue_delta_time, "
    "retrieval_strategy, retrieval_latency_ms, context_event_count, context_tokens, "
    "retrieval_truncated, verdict, raw_verdict, routing_tier, evidence_origin, "
    "threshold_applied, confidence, judge_backend, llm_latency_ms, cache_hit, "
    "downgraded, downgraded_gating, downgraded_anchoring, "
    "label_is_fault, label_fault_type, label_root_cause"
)


def pg_connect(timeout_seconds: int = 5) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "aiops"),
        password=os.environ.get("POSTGRES_PASSWORD", "aiops"),
        dbname=os.environ.get("POSTGRES_DB", "aiops"),
        connect_timeout=timeout_seconds,
        row_factory=dict_row,
    )


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _infer_strategy(config_yaml: str) -> str:
    try:
        cfg = yaml.safe_load(config_yaml) or {}
    except yaml.YAMLError:
        return "hybrid_bm25_graph"
    if not isinstance(cfg, Mapping):
        return "hybrid_bm25_graph"
    ret = cfg.get("retrieval")
    if isinstance(ret, Mapping) and ret.get("type"):
        return str(ret["type"])
    return "hybrid_bm25_graph"


def _ci(value: float | None, bounds: Sequence[float] | None) -> MetricWithCIResponse:
    v = float(value) if value is not None else 0.0
    if bounds and len(bounds) == 2:
        return MetricWithCIResponse(value=v, ci_low=float(bounds[0]), ci_high=float(bounds[1]))
    return MetricWithCIResponse(value=v, ci_low=v, ci_high=v)


def _extract_window_id(alert_id: str) -> str:
    m = _ALERT_ID_RE.match(alert_id)
    return m.group(1) if m else alert_id


def _normalize_verdict(raw: str, fallback: Verdict = "UNCERTAIN") -> Verdict:
    if raw in ("TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"):
        return cast(Verdict, raw)
    return fallback


def _normalize_origin(raw: str) -> EvidenceOrigin:
    if raw in ("local", "graph", "mixed", "none"):
        return cast(EvidenceOrigin, raw)
    return "none"


def _row_to_alert(row: Sequence[Any]) -> AlertResponse:
    (
        run_id,
        window_id,
        service,
        window_ts,
        anomaly_score,
        candidate_source,
        rescue_score,
        rescue_lambda_log,
        rescue_phi_topo,
        rescue_delta_time,
        retrieval_strategy,
        retrieval_latency_ms,
        context_event_count,
        context_tokens,
        retrieval_truncated,
        verdict_raw,
        raw_verdict_raw,
        routing_tier,
        evidence_origin_raw,
        threshold_applied,
        confidence,
        judge_backend,
        llm_latency_ms,
        cache_hit,
        downgraded,
        downgraded_gating,
        downgraded_anchoring,
        label_is_fault,
        label_fault_type,
        label_root_cause,
    ) = row

    strategy = str(retrieval_strategy or "hybrid_bm25_graph")
    verdict = _normalize_verdict(str(verdict_raw))
    raw_verdict = _normalize_verdict(str(raw_verdict_raw), fallback=verdict)
    is_fault = bool(label_is_fault)
    fault_type = str(label_fault_type) if is_fault and label_fault_type not in ("", "none", "normal") else None
    root_cause = str(label_root_cause) if is_fault and label_root_cause else None

    rescue_components: RescueComponentsResponse | None = None
    if (
        rescue_lambda_log is not None
        and rescue_phi_topo is not None
        and rescue_delta_time is not None
    ):
        rescue_components = RescueComponentsResponse(
            lambda_log=float(rescue_lambda_log),
            phi_topo=float(rescue_phi_topo),
            delta_time=float(rescue_delta_time),
        )

    return AlertResponse(
        alert_id=f"cand-{window_id}:{strategy}:r0",
        candidate_id=f"cand-{window_id}",
        window_id=str(window_id),
        run_id=str(run_id),
        service=str(service),
        ts=_utc(window_ts),
        anomaly_score=float(anomaly_score),
        candidate_source="rescue" if candidate_source == "rescue" else "metric",
        rescue_score=float(rescue_score) if rescue_score is not None else None,
        rescue_components=rescue_components,
        retrieval_strategy=strategy,
        retrieval_latency_ms=float(retrieval_latency_ms),
        context_event_count=int(context_event_count),
        context_tokens=int(context_tokens),
        retrieval_truncated=bool(retrieval_truncated),
        verdict=verdict,
        confidence=float(confidence) if confidence is not None else 0.0,
        judge_backend=str(judge_backend),
        llm_latency_ms=float(llm_latency_ms) if llm_latency_ms is not None else 0.0,
        cache_hit=bool(cache_hit),
        downgraded_by_evidence_rule=bool(downgraded),
        raw_verdict=raw_verdict,
        routing_tier=int(routing_tier) if routing_tier else 1,
        evidence_origin=_normalize_origin(str(evidence_origin_raw)),
        threshold_applied=float(threshold_applied) if threshold_applied is not None else None,
        downgraded_by_gating=bool(downgraded_gating),
        downgraded_by_anchoring=bool(downgraded_anchoring),
        label=WindowLabelResponse(
            is_fault=is_fault,
            fault_type=fault_type,
            root_cause_service=root_cause,
        ),
    )


@lru_cache(maxsize=1)
def _cached_graph() -> ServiceGraph:
    return load_graph()


@lru_cache(maxsize=1)
def _discover_ctav_runs() -> tuple[str, ...]:
    """Discover CTAV source run IDs from eval/results artifacts without hardcoding."""
    discovered: list[str] = []
    if RESULTS_DIR.is_dir():
        for entry in sorted(RESULTS_DIR.iterdir()):
            if not entry.is_dir():
                continue
            rt = entry / "runtime.json"
            if rt.is_file():
                try:
                    data = json.loads(rt.read_text(encoding="utf-8"))
                    ar = data.get("alerts_run")
                    if ar and ar not in discovered:
                        discovered.append(str(ar))
                except json.JSONDecodeError:
                    pass
            rca_p = entry / "rca.json"
            if rca_p.is_file():
                try:
                    data = json.loads(rca_p.read_text(encoding="utf-8"))
                    ar = ((data.get("config") or {}).get("input") or {}).get("alerts_run")
                    if ar and ar not in discovered:
                        discovered.append(str(ar))
                except json.JSONDecodeError:
                    pass
    for fallback in ("ctav_final_val_v1", "ctav_final_test_v1"):
        if fallback not in discovered and (RESULTS_DIR / fallback).is_dir():
            discovered.append(fallback)
    return tuple(discovered)


@lru_cache(maxsize=1)
def _judged_details_index() -> dict[str, tuple[str, list[str]]]:
    """window_id -> (reasoning, evidence_event_ids) from CTAV judged.jsonl files."""
    index: dict[str, tuple[str, list[str]]] = {}
    for run_name in _discover_ctav_runs():
        path = RESULTS_DIR / run_name / "judged.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                index[str(row["window_id"])] = (
                    str(row.get("reasoning") or ""),
                    [str(x) for x in (row.get("evidence_event_ids") or [])],
                )
    return index


@lru_cache(maxsize=1)
def _per_window_series_index() -> tuple[dict[str, tuple[str, str]], dict[str, list[tuple[datetime, float]]]]:
    """(window_id -> (service, pod), pod -> sorted [(ts, anomaly_score)]) from per_window.csv."""
    win_meta: dict[str, tuple[str, str]] = {}
    by_pod: dict[str, list[tuple[datetime, float]]] = {}
    for run_name in _discover_ctav_runs():
        path = RESULTS_DIR / run_name / "per_window.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                wid = row["window_id"]
                svc = row["service"]
                pod = row.get("pod") or svc
                ts = datetime.fromisoformat(row["window_ts"].replace("Z", "+00:00")).astimezone(UTC)
                score = float(row["anomaly_score"]) if row.get("anomaly_score") else 0.0
                win_meta[wid] = (svc, pod)
                by_pod.setdefault(pod, []).append((ts, score))
    for pod in by_pod:
        by_pod[pod].sort(key=lambda pair: pair[0])
    return win_meta, by_pod


@lru_cache(maxsize=8)
def _incident_labels_for_run(run_id: str) -> dict[str, tuple[str | None, str | None]]:
    """incident_id -> (ground_truth_service, fault_type) from eval/results/<run_id>/incidents.jsonl."""
    path = RESULTS_DIR / run_id / "incidents.jsonl"
    if not path.exists():
        return {}
    out: dict[str, tuple[str | None, str | None]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            out[str(row["incident_id"])] = (
                row.get("root_cause"),
                row.get("fault_type"),
            )
    return out


def _alert_counts_by_run() -> dict[str, int]:
    ch = clickhouse.get_client()
    try:
        res = ch.query(
            "SELECT run_id, count() FROM fact_alert_evaluation GROUP BY run_id"
        )
    finally:
        ch.close()
    return {str(run_id): int(cnt) for run_id, cnt in res.result_rows}


def _run_start_times() -> dict[str, datetime]:
    with pg_connect() as conn:
        rows = conn.execute("SELECT run_id, started_at FROM run_registry").fetchall()
    return {str(r["run_id"]): _utc(r["started_at"]) for r in rows}


def list_runs() -> list[RunResponse]:
    with pg_connect() as conn:
        rows = conn.execute(
            "SELECT run_id, config_yaml, git_commit, split, seed, started_at, finished_at, status, notes "
            "FROM run_registry "
            "ORDER BY (run_id LIKE 'pipeline_%%') DESC, started_at DESC, (split = 'test') DESC"
        ).fetchall()
    counts = _alert_counts_by_run()
    runs = [
        RunResponse(
            run_id=str(r["run_id"]),
            retrieval_strategy=_infer_strategy(str(r["config_yaml"])),
            split=str(r["split"]),
            seed=int(r["seed"]),
            git_commit=str(r["git_commit"]).splitlines()[0] if r["git_commit"] else "",
            started_at=_utc(r["started_at"]),
            finished_at=_utc(r["finished_at"]) if r["finished_at"] is not None else None,
            status=str(r["status"]),
            notes=str(r["notes"] or ""),
            alert_count=counts.get(str(r["run_id"]), 0),
        )
        for r in rows
    ]
    runs.sort(
        key=lambda item: (item.alert_count > 0, item.started_at, item.split == "test"),
        reverse=True,
    )
    return runs


def get_run_metrics(run_id: str) -> RunMetricsResponse | None:
    run_dir = RESULTS_DIR / run_id
    rca_path = run_dir / "rca.json"
    ctav_path = run_dir / "ctav.json"
    metrics_path = run_dir / "metrics.json"

    if rca_path.exists():
        return _metrics_from_rca(run_id, run_dir, json.loads(rca_path.read_text(encoding="utf-8")))
    if ctav_path.exists():
        return _metrics_from_ctav(run_id, json.loads(ctav_path.read_text(encoding="utf-8")))
    if metrics_path.exists():
        return _metrics_from_plain(run_id, run_dir, json.loads(metrics_path.read_text(encoding="utf-8")))
    return None


def _read_ops_latencies(evidence_run: str | None) -> tuple[float, float]:
    if not evidence_run:
        return 0.0, 0.0
    mpath = RESULTS_DIR / evidence_run / "metrics.json"
    if not mpath.exists():
        return 0.0, 0.0
    ops = json.loads(mpath.read_text(encoding="utf-8")).get("telemetry", {}).get("operations", {})
    return float(ops.get("retrieval_latency_ms_p95") or 0.0), float(ops.get("llm_latency_ms_p95") or 0.0)


def _metrics_from_rca(run_id: str, run_dir: Path, rca_data: Mapping[str, Any]) -> RunMetricsResponse:
    cfg = rca_data.get("config") or {}
    inp = cfg.get("input") or {}
    evidence_run = inp.get("evidence_run")
    rlat, llat = _read_ops_latencies(str(evidence_run) if evidence_run else None)

    ctav_run_id = inp.get("alerts_run")
    variant_name = "ctav"
    if not ctav_run_id and inp.get("ctav_config"):
        ctav_cfg_path = REPO / str(inp["ctav_config"])
        if ctav_cfg_path.exists():
            ctav_cfg = yaml.safe_load(ctav_cfg_path.read_text(encoding="utf-8")) or {}
            ctav_run_id = ctav_cfg.get("run_id")
            variant_name = str(inp.get("variant") or "ctav")

    n_windows = 0
    cm: Mapping[str, Any] = {}
    if ctav_run_id and (RESULTS_DIR / str(ctav_run_id) / "ctav.json").exists():
        ctav_data = json.loads((RESULTS_DIR / str(ctav_run_id) / "ctav.json").read_text(encoding="utf-8"))
        n_windows = int(ctav_data.get("windows") or 0)
        cm = (ctav_data.get("ablation") or {}).get("methods", {}).get(variant_name, {})

    hit = (rca_data.get("main") or {}).get("hit") or {}
    summarizer = rca_data.get("summarizer") or {}
    runtime_path = run_dir / "runtime.json"
    if runtime_path.exists():
        runtime_data = json.loads(runtime_path.read_text(encoding="utf-8"))
        cache_rate = float((runtime_data.get("llm_operations") or {}).get("cache_hit_rate") or 0.0)
    else:
        llm_calls = int(summarizer.get("llm_calls") or 0)
        cache_hits = int(summarizer.get("cache_hits") or 0)
        cache_rate = float(cache_hits / llm_calls) if llm_calls else 0.0

    return RunMetricsResponse(
        run_id=run_id,
        retrieval_strategy="hybrid_bm25_graph",
        n_windows=n_windows,
        tp=int(cm.get("tp") or 0),
        fp=int(cm.get("fp") or 0),
        fn=int(cm.get("fn") or 0),
        tn=int(cm.get("tn") or 0),
        precision=_ci(cm.get("precision"), cm.get("precision_ci95")),
        recall=_ci(cm.get("recall"), cm.get("recall_ci95")),
        f1=_ci(cm.get("f1"), cm.get("f1_ci95")),
        fpr=_ci(cm.get("fpr"), cm.get("fpr_ci95")),
        hit_at_1=_ci(hit.get("level1_hit1"), hit.get("level1_hit1_ci95")),
        hit_at_3=_ci(hit.get("level1_hit3"), hit.get("level1_hit3_ci95")),
        context_precision=MetricWithCIResponse(value=0.0, ci_low=0.0, ci_high=0.0),
        retrieval_latency_p95_ms=rlat,
        llm_latency_p95_ms=llat,
        cache_hit_rate=cache_rate,
        json_valid_rate=float(summarizer.get("json_valid_rate") or 0.0),
    )


def _metrics_from_ctav(run_id: str, ctav_data: Mapping[str, Any]) -> RunMetricsResponse:
    cfg = ctav_data.get("config") or {}
    topo_run = (cfg.get("tiers") or {}).get("topology")
    rlat, llat = _read_ops_latencies(str(topo_run) if topo_run else None)
    cm = (ctav_data.get("ablation") or {}).get("methods", {}).get("ctav", {})
    zero = MetricWithCIResponse(value=0.0, ci_low=0.0, ci_high=0.0)
    return RunMetricsResponse(
        run_id=run_id,
        retrieval_strategy="hybrid_bm25_graph",
        n_windows=int(ctav_data.get("windows") or 0),
        tp=int(cm.get("tp") or 0),
        fp=int(cm.get("fp") or 0),
        fn=int(cm.get("fn") or 0),
        tn=int(cm.get("tn") or 0),
        precision=_ci(cm.get("precision"), cm.get("precision_ci95")),
        recall=_ci(cm.get("recall"), cm.get("recall_ci95")),
        f1=_ci(cm.get("f1"), cm.get("f1_ci95")),
        fpr=_ci(cm.get("fpr"), cm.get("fpr_ci95")),
        hit_at_1=zero,
        hit_at_3=zero,
        context_precision=zero,
        retrieval_latency_p95_ms=rlat,
        llm_latency_p95_ms=llat,
        cache_hit_rate=1.0,
        json_valid_rate=0.0,
    )


def _metrics_from_plain(run_id: str, run_dir: Path, metrics_data: Mapping[str, Any]) -> RunMetricsResponse:
    tel = metrics_data.get("telemetry") or metrics_data.get("all") or {}
    pipe = tel.get("pipeline") or {}
    ops = tel.get("operations") or {}
    snap_path = run_dir / "config.snapshot.yaml"
    strategy = _infer_strategy(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else "hybrid_bm25_graph"
    zero = MetricWithCIResponse(value=0.0, ci_low=0.0, ci_high=0.0)
    return RunMetricsResponse(
        run_id=run_id,
        retrieval_strategy=strategy,
        n_windows=int(ops.get("windows") or 0),
        tp=int(pipe.get("tp") or 0),
        fp=int(pipe.get("fp") or 0),
        fn=int(pipe.get("fn") or 0),
        tn=int(pipe.get("tn") or 0),
        precision=_ci(pipe.get("precision"), pipe.get("precision_ci95")),
        recall=_ci(pipe.get("recall"), pipe.get("recall_ci95")),
        f1=_ci(pipe.get("f1"), pipe.get("f1_ci95")),
        fpr=_ci(pipe.get("fpr"), pipe.get("fpr_ci95")),
        hit_at_1=zero,
        hit_at_3=zero,
        context_precision=zero,
        retrieval_latency_p95_ms=float(ops.get("retrieval_latency_ms_p95") or 0.0),
        llm_latency_p95_ms=float(ops.get("llm_latency_ms_p95") or 0.0),
        cache_hit_rate=float(ops.get("cache_hit_rate") or 0.0),
        json_valid_rate=0.0,
    )


def _run_known(run_id: str) -> bool:
    with pg_connect() as conn:
        row = conn.execute("SELECT 1 FROM run_registry WHERE run_id = %s", (run_id,)).fetchone()
        if row is not None:
            return True
    ch = clickhouse.get_client()
    try:
        res = ch.query(
            "SELECT count() FROM fact_alert_evaluation WHERE run_id = {run_id:String}",
            parameters={"run_id": run_id},
        )
        return int(res.result_rows[0][0]) > 0
    finally:
        ch.close()


def list_alerts(
    run_id: str,
    verdict: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[AlertResponse] | None:
    if not _run_known(run_id):
        return None
    clauses = [
        "run_id = {run_id:String}",
        "verdict IN ('TRUE_ALERT', 'FALSE_POSITIVE', 'UNCERTAIN')",
    ]
    params: dict[str, Any] = {"run_id": run_id}
    if verdict and verdict != "ALL":
        clauses.append("verdict = {verdict:String}")
        params["verdict"] = verdict
    sql = (
        f"SELECT {_ALERT_SELECT_COLS} FROM fact_alert_evaluation "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY window_ts ASC, window_id ASC"
    )
    if limit is not None:
        sql += " LIMIT {limit:UInt64} OFFSET {offset:UInt64}"
        params["limit"] = int(limit)
        params["offset"] = int(offset)
    elif offset > 0:
        sql += " OFFSET {offset:UInt64}"
        params["offset"] = int(offset)

    ch = clickhouse.get_client()
    try:
        res = ch.query(sql, parameters=params)
        return [_row_to_alert(row) for row in res.result_rows]
    finally:
        ch.close()


def _sanitize_debug(raw: Mapping[str, Any]) -> dict[str, str | int | float | bool]:
    out: dict[str, str | int | float | bool] = {}
    for k, v in raw.items():
        if k == "content" or v is None:
            continue
        if isinstance(v, (bool, int, float, str)):
            out[str(k)] = v
        elif isinstance(v, (list, tuple)):
            out[str(k)] = ", ".join(str(x) for x in v)
        else:
            out[str(k)] = json.dumps(v, ensure_ascii=False, default=str)
    return out


def _build_metric_series(
    window_id: str,
    alert_ts: datetime,
    anomaly_score: float,
) -> list[MetricPointResponse]:
    win_meta, by_pod = _per_window_series_index()
    meta = win_meta.get(window_id)
    if meta is not None:
        _, pod = meta
        lo = alert_ts - timedelta(minutes=16)
        hi = alert_ts + timedelta(minutes=7)
        pts = [
            MetricPointResponse(ts=ts, value=score)
            for ts, score in by_pod.get(pod, ())
            if lo <= ts <= hi
        ]
        if pts:
            return pts

    # Fallback: read the single window via NezhaReplaySource (01 / M10-B spec).
    from services.replayer.nezha_source import NezhaReplaySource

    try:
        windows = list(NezhaReplaySource(window_ids={window_id}, limit=1).stream())
    except OSError:
        windows = []
    if windows:
        return [MetricPointResponse(ts=_utc(windows[0].start_ts), value=anomaly_score)]
    return [MetricPointResponse(ts=alert_ts, value=anomaly_score)]


def get_alert_detail(alert_id: str, run_id: str | None = None) -> AlertDetailResponse | None:
    window_id = _extract_window_id(alert_id)
    ch = clickhouse.get_client()
    try:
        if run_id is not None:
            sql = (
                f"SELECT {_ALERT_SELECT_COLS} FROM fact_alert_evaluation "
                "WHERE run_id = {run_id:String} AND window_id = {window_id:String} LIMIT 1"
            )
            params: dict[str, Any] = {"run_id": run_id, "window_id": window_id}
            res = ch.query(sql, parameters=params)
            if not res.result_rows:
                return None
            chosen_row = res.result_rows[0]
        else:
            sql = (
                f"SELECT {_ALERT_SELECT_COLS} FROM fact_alert_evaluation "
                "WHERE window_id = {window_id:String}"
            )
            res = ch.query(sql, parameters={"window_id": window_id})
            if not res.result_rows:
                return None
            starts = _run_start_times() if len(res.result_rows) > 1 else {}
            chosen_row = max(
                res.result_rows,
                key=lambda row: (
                    str(row[0]).startswith("pipeline_"),
                    starts.get(str(row[0]), _utc(datetime.min.replace(tzinfo=UTC))),
                    str(row[0]),
                ),
            )
        alert = _row_to_alert(chosen_row)

        trace_res = ch.query(
            "SELECT event_id, modality, service, event_ts, score, rank, origin, graph_distance, debug_json "
            "FROM fact_retrieval_trace "
            "WHERE run_id = {run_id:String} AND window_id = {window_id:String} "
            "ORDER BY rank ASC",
            parameters={"run_id": alert.run_id, "window_id": alert.window_id},
        )
    finally:
        ch.close()

    events: list[ContextEventResponse] = []
    for event_id, modality, svc, event_ts, score, rank, origin, graph_distance, debug_json in trace_res.result_rows:
        try:
            raw_debug = json.loads(debug_json) if debug_json else {}
        except json.JSONDecodeError:
            raw_debug = {}
        content = str(raw_debug.get("content") or "")
        debug = _sanitize_debug(raw_debug)
        debug.setdefault("rank", int(rank))
        debug["origin"] = str(origin or "local")
        if graph_distance is not None:
            debug["graph_distance"] = int(graph_distance)
        mod: Literal["log", "trace", "metric"] = (
            cast(Literal["log", "trace", "metric"], modality)
            if modality in ("log", "trace", "metric")
            else "trace"
        )
        events.append(
            ContextEventResponse(
                event_id=str(event_id),
                modality=mod,
                ts=_utc(event_ts),
                service=str(svc),
                content=content,
                score=float(score),
                debug=debug,
            )
        )

    reasoning, evidence_ids = _judged_details_index().get(alert.window_id, ("", []))
    series = _build_metric_series(alert.window_id, alert.ts, alert.anomaly_score)

    return AlertDetailResponse(
        **alert.model_dump(),
        reasoning=reasoning,
        evidence_event_ids=evidence_ids,
        context_events=events,
        metric_series=series,
        metric_name="anomaly_score (Isolation Forest)",
        detector_threshold=DEFAULT_DETECTOR_THRESHOLD,
    )


def _edges_used_count(grouping_reason: Mapping[str, Any]) -> int:
    raw = grouping_reason.get("graph_edges_used")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return len(raw)
    return 0


def list_incidents(run_id: str) -> list[IncidentResponse] | None:
    if not _run_known(run_id):
        return None
    with pg_connect() as conn:
        rows = conn.execute(
            "SELECT i.incident_id, i.run_id, i.alert_ids, i.services, i.start_ts, i.end_ts, "
            "i.grouping_reason, dr.report->>'root_cause_service' AS root_cause_service "
            "FROM incidents i "
            "LEFT JOIN diagnostic_reports dr ON dr.incident_id = i.incident_id "
            "WHERE i.run_id = %s "
            "ORDER BY i.start_ts ASC, i.incident_id ASC",
            (run_id,),
        ).fetchall()

    labels = _incident_labels_for_run(run_id)
    out: list[IncidentResponse] = []
    for r in rows:
        iid = str(r["incident_id"])
        gt_service, fault_type = labels.get(iid, (None, None))
        gr = r["grouping_reason"] or {}
        out.append(
            IncidentResponse(
                incident_id=iid,
                run_id=str(r["run_id"]),
                alert_ids=[str(x) for x in (r["alert_ids"] or [])],
                services=[str(x) for x in (r["services"] or [])],
                start_ts=_utc(r["start_ts"]),
                end_ts=_utc(r["end_ts"]),
                grouping_reason=GroupingReasonResponse(
                    temporal_window_sec=float(gr.get("temporal_window_sec") or 180.0),
                    graph_edges_used=_edges_used_count(gr),
                ),
                root_cause_service=str(r["root_cause_service"]) if r["root_cause_service"] else None,
                ground_truth_service=gt_service,
                fault_type=fault_type,
            )
        )
    return out


def get_incident_detail(incident_id: str) -> IncidentDetailResponse | None:
    with pg_connect() as conn:
        row = conn.execute(
            "SELECT i.incident_id, i.run_id, i.alert_ids, i.services, i.start_ts, i.end_ts, "
            "i.grouping_reason, dr.report AS report_json, rej.reject_reason "
            "FROM incidents i "
            "LEFT JOIN diagnostic_reports dr ON dr.incident_id = i.incident_id "
            "LEFT JOIN diagnostic_rejected rej ON rej.incident_id = i.incident_id "
            "WHERE i.incident_id = %s LIMIT 1",
            (incident_id,),
        ).fetchone()
    if row is None:
        return None

    run_id = str(row["run_id"])
    alert_ids = [str(x) for x in (row["alert_ids"] or [])]
    services = [str(x) for x in (row["services"] or [])]
    gr = row["grouping_reason"] or {}

    report: DiagnosticReport | None = (
        DiagnosticReport.model_validate(row["report_json"]) if row["report_json"] else None
    )
    root_cause_service = report.root_cause_service if report is not None else None
    gt_service, fault_type = _incident_labels_for_run(run_id).get(incident_id, (None, None))

    window_ids = [_extract_window_id(aid) for aid in alert_ids]
    alerts: list[AlertResponse] = []
    if window_ids:
        ch = clickhouse.get_client()
        try:
            res = ch.query(
                f"SELECT {_ALERT_SELECT_COLS} FROM fact_alert_evaluation "
                "WHERE run_id = {run_id:String} AND window_id IN {window_ids:Array(String)} "
                "ORDER BY window_ts ASC, window_id ASC",
                parameters={"run_id": run_id, "window_ids": window_ids},
            )
            alerts = [_row_to_alert(r) for r in res.result_rows]
        finally:
            ch.close()

    alert_count_by_svc: dict[str, int] = {}
    max_score_by_svc: dict[str, float] = {}
    for a in alerts:
        alert_count_by_svc[a.service] = alert_count_by_svc.get(a.service, 0) + 1
        max_score_by_svc[a.service] = max(max_score_by_svc.get(a.service, 0.0), a.anomaly_score)

    graph = _cached_graph()
    directed = graph.directed
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

    return IncidentDetailResponse(
        incident_id=incident_id,
        run_id=run_id,
        alert_ids=alert_ids,
        services=services,
        start_ts=_utc(row["start_ts"]),
        end_ts=_utc(row["end_ts"]),
        grouping_reason=GroupingReasonResponse(
            temporal_window_sec=float(gr.get("temporal_window_sec") or 180.0),
            graph_edges_used=_edges_used_count(gr),
        ),
        root_cause_service=root_cause_service,
        ground_truth_service=gt_service,
        fault_type=fault_type,
        nodes=nodes,
        edges=edges,
        report=report,
        rejected_reason=str(row["reject_reason"]) if row["reject_reason"] else None,
        alerts=alerts,
    )
