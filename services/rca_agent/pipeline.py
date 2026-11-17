"""End-to-end RCA pipeline (M10-A): CTAV replay -> ClickHouse -> grouping -> propagation ->
cache-only summarizer -> parity check -> PostgreSQL.

    py -m services.rca_agent.pipeline --config eval/configs/rca_final.yaml
    py -m services.rca_agent.pipeline --config eval/configs/rca_final_test.yaml

Reuses the frozen M9 modules (`grouping.py`, `propagation.py`, `summarizer.py`, `store.py`)
and `eval/harness/rca.py` without modifying M9 outputs or making any live API call.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

from eval.harness import rca
from eval.harness.runner import REPO, RESULTS, _git_commit
from packages.graph.service_graph import ServiceGraph, load_graph
from packages.schemas.models import ContextEvent, Incident, JudgedAlert
from packages.storage import clickhouse
from services.judge.backends import JUDGE_MODEL, PRICES_PER_1M, BackendResponse
from services.judge.cache import ResponseCache
from services.rca_agent import store
from services.rca_agent.grouping import _incident_id, group_alerts, time_clusters
from services.rca_agent.propagation import Sign, propagation_path
from services.rca_agent.summarizer import (
    PROMPT_VERSION,
    GeminiSummaryBackend,
    Summarizer,
    SummaryResult,
    prompt_fingerprint,
)

EXPECTED_METHOD_FINGERPRINT = "b0c54fa68ef65535"


def _flag(value: str | bool | int | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return (value or "") not in ("", "0", "False", "false")


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class CacheOnlyGeminiSummaryBackend(GeminiSummaryBackend):
    """Gemini summary backend that strictly reads from the local JSONL cache.

    Never touches the network or reads GEMINI_API_KEY; raises RuntimeError on any miss.
    """

    def complete(self, prompt: str) -> BackendResponse:
        key = self.cache_key(prompt)
        entry = self.cache.get(key)
        if entry is None:
            raise RuntimeError(
                f"Cache miss for key {key}: pipeline runs in cache-only mode (0 API calls allowed)"
            )
        return BackendResponse(
            raw=str(entry.get("raw", "")),
            usage=dict(entry.get("usage") or {}),
            cache_hit=True,
            cache_key=key,
            model_version=entry.get("model_version"),
        )


@dataclass
class LoadedAlerts:
    inputs: rca.Inputs
    eval_rows: list[dict[str, Any]]
    trace_rows: list[dict[str, Any]]
    evidence_by_window: dict[str, dict[str, ContextEvent]]
    ctav_prompt_tokens: int
    ctav_completion_tokens: int


def load_alerts(
    alerts_run: str,
    evidence_run: str,
    run_id: str,
    results_root: Path = RESULTS,
) -> LoadedAlerts:
    """Load CTAV judged candidates and retrieval evidence for ClickHouse ingestion and grouping."""
    alerts_dir = results_root / alerts_run
    evidence_dir = results_root / evidence_run

    with (alerts_dir / "per_window.csv").open(encoding="utf-8", newline="") as handle:
        per_window_rows = list(csv.DictReader(handle))
    by_window = {row["window_id"]: row for row in per_window_rows}
    wanted_alert_windows = {row["window_id"] for row in per_window_rows if row["decision"] == "alert"}

    judged_alerts: list[JudgedAlert] = []
    with (alerts_dir / "judged.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            judged_alerts.append(JudgedAlert.model_validate_json(line))
    judged_by_window = {alert.window_id: alert for alert in judged_alerts}

    confirmed_alerts = [
        alert for alert in judged_alerts if alert.window_id in wanted_alert_windows
    ]
    if {alert.window_id for alert in confirmed_alerts} != wanted_alert_windows:
        raise ValueError(
            f"{alerts_dir}: judged.jsonl does not hold every alert of per_window.csv"
        )

    retrieval_by_window: dict[str, dict[str, Any]] = {}
    with (evidence_dir / "retrieval.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["window_id"] in judged_by_window:
                retrieval_by_window[record["window_id"]] = record

    if set(retrieval_by_window) != set(judged_by_window):
        missing = sorted(set(judged_by_window) - set(retrieval_by_window))
        raise ValueError(
            f"{evidence_dir}: retrieval.jsonl missing {len(missing)} candidate window(s)"
        )

    eval_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    evidence_by_window: dict[str, dict[str, ContextEvent]] = {}
    ctav_prompt_tokens = 0
    ctav_completion_tokens = 0

    for alert in judged_alerts:
        pw = by_window[alert.window_id]
        ret = retrieval_by_window[alert.window_id]
        events = ret.get("events") or []
        strategy = str(
            alert.debug.get("retrieval_strategy") or ret.get("strategy") or "hybrid_bm25_graph"
        )
        ctav_prompt_tokens += int(alert.debug.get("prompt_tokens") or 0)
        ctav_completion_tokens += int(alert.debug.get("completion_tokens") or 0)

        eval_rows.append(
            {
                "run_id": run_id,
                "window_id": alert.window_id,
                "service": alert.service,
                "window_ts": alert.ts.astimezone(UTC),
                "anomaly_score": float(pw["anomaly_score"] or 0.0),
                "candidate_source": "metric",
                "rescue_score": None,
                "rescue_lambda_log": None,
                "rescue_phi_topo": None,
                "rescue_delta_time": None,
                "retrieval_strategy": strategy,
                "retrieval_latency_ms": float(ret.get("latency_ms") or 0.0),
                "context_event_count": len(events),
                "context_tokens": int(ret.get("token_estimate") or 0),
                "retrieval_truncated": int(bool(ret.get("truncated", False))),
                "verdict": alert.verdict,
                "raw_verdict": alert.raw_verdict,
                "routing_tier": int(alert.routing_tier),
                "evidence_origin": alert.evidence_origin,
                "threshold_applied": (
                    float(alert.threshold_applied)
                    if alert.threshold_applied is not None
                    else None
                ),
                "confidence": float(alert.confidence),
                "judge_backend": alert.judge_backend,
                "llm_latency_ms": float(alert.llm_latency_ms),
                "cache_hit": 1,
                "downgraded": int(alert.downgraded_by_evidence_rule),
                "downgraded_gating": int(alert.downgraded_by_gating),
                "downgraded_anchoring": int(alert.downgraded_by_anchoring),
                "label_is_fault": int(_flag(pw["label_is_fault"])),
                "label_fault_type": pw["label_fault_type"],
                "label_root_cause": pw["label_root_cause"] or "",
            }
        )

        for event in events:
            debug_payload = dict(event.get("debug") or {})
            debug_payload["content"] = event.get("content", "")
            trace_rows.append(
                {
                    "run_id": run_id,
                    "window_id": alert.window_id,
                    "event_id": event["event_id"],
                    "modality": event["modality"],
                    "service": event["service"],
                    "event_ts": _parse_ts(event["ts"]),
                    "score": float(event["score"]),
                    "rank": int((event.get("debug") or {}).get("rank", 0)),
                    "origin": event.get("origin", "local"),
                    "graph_distance": event.get("graph_distance"),
                    "debug_json": json.dumps(debug_payload, ensure_ascii=False, default=str),
                }
            )

        if alert.window_id in wanted_alert_windows:
            evidence_by_window[alert.window_id] = {
                e["event_id"]: ContextEvent.model_validate(e) for e in events
            }

    inputs = rca.Inputs(
        rows=per_window_rows,
        alerts=confirmed_alerts,
        source=f"{alerts_run} (decision == alert)",
    )
    return LoadedAlerts(
        inputs=inputs,
        eval_rows=eval_rows,
        trace_rows=trace_rows,
        evidence_by_window=evidence_by_window,
        ctav_prompt_tokens=ctav_prompt_tokens,
        ctav_completion_tokens=ctav_completion_tokens,
    )


def normalized_report_hash(report_dict: Mapping[str, Any]) -> str:
    """Hash a DiagnosticReport JSON ignoring per-run identity and timestamp fields."""
    cleaned = {
        key: value
        for key, value in report_dict.items()
        if key not in {"incident_id", "run_id", "generated_at"}
    }
    encoded = json.dumps(cleaned, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def check_parity(
    located: Sequence[rca.Located],
    summaries: Sequence[SummaryResult],
    reference_dir: Path,
) -> dict[str, Any]:
    """Verify exact parity against an M9 reference run (alert_ids, rankings, report hashes)."""
    incidents_path = reference_dir / "incidents.jsonl"
    reports_path = reference_dir / "reports.jsonl"
    if not incidents_path.exists() or not reports_path.exists():
        raise ValueError(f"{reference_dir}: missing reference incidents.jsonl or reports.jsonl")

    ref_incidents = [
        json.loads(line) for line in incidents_path.read_text(encoding="utf-8").splitlines() if line
    ]
    ref_reports = [
        json.loads(line) for line in reports_path.read_text(encoding="utf-8").splitlines() if line
    ]

    if len(located) != len(ref_incidents):
        raise ValueError(
            f"Incident count mismatch vs {reference_dir.name}: "
            f"got {len(located)}, expected {len(ref_incidents)}"
        )
    if len(summaries) != len(ref_reports):
        raise ValueError(
            f"Summary count mismatch vs {reference_dir.name}: "
            f"got {len(summaries)}, expected {len(ref_reports)}"
        )

    for idx, (item, ref_inc) in enumerate(zip(located, ref_incidents, strict=True)):
        got_record = rca.incident_record(item)
        if got_record["alert_ids"] != ref_inc["alert_ids"]:
            raise ValueError(
                f"Parity mismatch at incident #{idx} alert_ids: "
                f"{got_record['alert_ids']} != {ref_inc['alert_ids']}"
            )
        if got_record["level1"] != ref_inc["level1"]:
            raise ValueError(
                f"Parity mismatch at incident #{idx} level1 ranking: "
                f"{got_record['level1']} != {ref_inc['level1']}"
            )
        if got_record["baseline"] != ref_inc["baseline"]:
            raise ValueError(
                f"Parity mismatch at incident #{idx} baseline ranking: "
                f"{got_record['baseline']} != {ref_inc['baseline']}"
            )

    for idx, (res, ref_rep) in enumerate(zip(summaries, ref_reports, strict=True)):
        ref_payload = ref_rep.get("report")
        if (res.report is None) != (ref_payload is None):
            raise ValueError(f"Parity mismatch at report #{idx}: presence differs")
        if res.report is not None and ref_payload is not None:
            got_hash = normalized_report_hash(res.report.model_dump(mode="json"))
            ref_hash = normalized_report_hash(ref_payload)
            if got_hash != ref_hash:
                raise ValueError(
                    f"Parity mismatch at report #{idx} JSON hash: {got_hash} != {ref_hash}"
                )

    return {
        "reference_run_id": reference_dir.name,
        "incidents_expected": len(ref_incidents),
        "incidents_matched": len(located),
        "rankings_matched": len(located),
        "reports_matched": len(summaries),
        "all_matched": True,
    }


def _evaluate_stages(
    config: Mapping[str, Any],
    inputs: rca.Inputs,
    graph: ServiceGraph,
    run_id: str,
) -> tuple[dict[str, Any], list[rca.Located], float, float]:
    """Run grouping and propagation level 1, returning report stats and per-stage timings."""
    n_boot = int(config.get("n_boot", 1000))
    seed = int(config.get("seed", 42))
    labels = config.get("labels") or {}
    window_seconds = float(labels.get("window_seconds", 60))
    cascade_min = int(labels.get("cascade_min_services", 2))
    grouping_cfg, propagation_cfg = config["grouping"], config["propagation"]
    t_group = float(grouping_cfg["t_group_seconds"])
    pad = float(propagation_cfg.get("sign_pad_seconds", window_seconds))
    sign: Sign = propagation_cfg.get("sign", "alert")

    injections = rca.load_injections({r["window_id"] for r in inputs.rows}, window_seconds)
    by_injection = {i.injection_id: i for i in injections}
    membership = {
        a.alert_id: rca.alert_injections(a, injections, window_seconds) for a in inputs.alerts
    }
    alerts_by_id = {a.alert_id: a for a in inputs.alerts}
    score_of_window = {r["window_id"]: float(r["anomaly_score"] or 0.0) for r in inputs.rows}
    alert_scores = {a.alert_id: score_of_window[a.window_id] for a in inputs.alerts}
    series = rca.ServiceSeries(inputs.rows)
    sets = rca.alert_sets(inputs.alerts, membership, by_injection, cascade_min)

    t0 = time.perf_counter()
    incidents: list[Incident] = group_alerts(inputs.alerts, graph, run_id, t_group)
    grouping_ms = (time.perf_counter() - t0) * 1000.0

    labelled = rca.label_incidents(incidents, membership, by_injection)
    units = time_clusters(inputs.alerts, t_group)
    reduction = rca.reduction_table(units, {t_group: incidents}, sets, t_group, n_boot, seed)

    t1 = time.perf_counter()
    located = [
        rca.locate(x, alerts_by_id, alert_scores, graph, series, sign, pad) for x in labelled
    ]
    propagation_ms = (time.perf_counter() - t1) * 1000.0

    entry = rca._describe_incidents(labelled)
    entry[f"hit_{sign}"] = rca.hit_table(located, n_boot, seed)
    entry[f"per_injection_{sign}"] = rca.injection_table(located, injections, n_boot, seed)

    fault_alerts = len(sets["fault"])
    report: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "config": {**dict(config), "run_id": run_id},
        "input": inputs.source,
        "split": config["split"],
        "alerts": len(inputs.alerts),
        "alerts_in_a_fault": fault_alerts,
        "alerts_outside_any_fault": len(inputs.alerts) - fault_alerts,
        "alerted_services": len({a.service for a in inputs.alerts}),
        "injections": len(injections),
        "injections_by_fault_type": dict(
            sorted(Counter(i.fault_type for i in injections).items())
        ),
        "cascade_injections": len({i for a in sets["cascade"] for i in membership[a]}),
        "resampling_units": len(units),
        "n_boot": n_boot,
        "seed": seed,
        "reduction": reduction,
        "t_group_seconds": t_group,
        "by_t_group": {str(int(t_group)): entry},
        "sign": sign,
        "main": {
            "t_group_seconds": t_group,
            "sign": sign,
            **entry,
            "hit": entry[f"hit_{sign}"],
            "per_injection": entry[f"per_injection_{sign}"],
            "reduction": {name: values[str(int(t_group))] for name, values in reduction.items()},
            "level1_top1_differs_from_baseline": sum(
                1
                for x in located
                if x.level1 and x.baseline and x.level1[0].service != x.baseline[0]
            ),
            "level1_top1_not_alerted": sum(
                1 for x in located if x.level1 and not x.level1[0].alerted
            ),
        },
    }
    return report, located, grouping_ms, propagation_ms


def _summarize_from_cache(
    config: Mapping[str, Any],
    located: Sequence[rca.Located],
    inputs: rca.Inputs,
    evidence_by_window: Mapping[str, Mapping[str, ContextEvent]],
    graph: ServiceGraph,
    run_id: str,
    reference_run_id: str,
    cache_path: Path,
) -> tuple[dict[str, Any], list[SummaryResult]]:
    """Run summarizer strictly from cache, matching M9's prompt incident_id."""
    spec = config["summarizer"]
    if (
        spec.get("prompt_version") != PROMPT_VERSION
        or spec.get("prompt_fingerprint") != prompt_fingerprint()
    ):
        raise ValueError(
            f"summarizer prompt is {PROMPT_VERSION} / {prompt_fingerprint()}, config pins "
            f"{spec.get('prompt_version')} / {spec.get('prompt_fingerprint')}"
        )
    if spec.get("backend") != "gemini":
        raise ValueError(f"pipeline requires summarizer.backend == 'gemini', got {spec.get('backend')!r}")
    model = str(spec.get("model", JUDGE_MODEL))
    if model != JUDGE_MODEL:
        raise ValueError(f"summarizer.model must be {JUDGE_MODEL}, got {model!r}")

    backend = CacheOnlyGeminiSummaryBackend(
        ResponseCache(cache_path), model, int(spec["max_output_tokens"])
    )
    summarizer = Summarizer(
        backend,
        graph,
        bool(spec.get("require_evidence", True)),
        int(spec.get("max_evidence", 12)),
        int(spec.get("excerpt_chars", 240)),
    )
    alerts_by_id = {a.alert_id: a for a in inputs.alerts}

    outputs: list[SummaryResult] = []
    for item in located:
        incident = item.labelled.incident
        alerts = [alerts_by_id[i] for i in incident.alert_ids]
        path = propagation_path(item.level1, graph)
        events = rca.incident_evidence(item, alerts_by_id, evidence_by_window)

        # M9 cache entries were keyed with the prompt containing incident_id hashed from reference_run_id.
        prompt_incident = incident.model_copy(
            update={
                "incident_id": _incident_id(reference_run_id, incident.alert_ids),
                "run_id": reference_run_id,
            }
        )
        t_item = time.perf_counter()
        raw_res = summarizer.summarize(prompt_incident, alerts, item.level1, path, events)
        summary_item_ms = (time.perf_counter() - t_item) * 1000.0

        remapped_report = (
            raw_res.report.model_copy(
                update={"incident_id": incident.incident_id, "run_id": run_id}
            )
            if raw_res.report is not None
            else None
        )
        debug = {**raw_res.debug, "latency_ms": item.elapsed_ms + summary_item_ms}
        outputs.append(
            SummaryResult(
                incident_id=incident.incident_id,
                report=remapped_report,
                reject_reason=raw_res.reject_reason,
                raw_output=raw_res.raw_output,
                llm_called=raw_res.llm_called,
                suspicious=raw_res.suspicious,
                invalid_evidence_ids=raw_res.invalid_evidence_ids,
                debug=debug,
            )
        )

    called = [r for r in outputs if r.llm_called]
    valid = [r for r in called if r.valid]
    reasons = Counter((r.reject_reason or "").split(":")[0] for r in outputs if not r.valid)
    prompt_tokens_cached = sum(int(r.debug.get("prompt_tokens") or 0) for r in outputs)
    completion_tokens_cached = sum(int(r.debug.get("completion_tokens") or 0) for r in outputs)
    price_in, price_out = PRICES_PER_1M.get(model, (0.0, 0.0))

    stats = {
        "backend": backend.name,
        "prompt_version": PROMPT_VERSION,
        "prompt_fingerprint": prompt_fingerprint(),
        "incidents": len(outputs),
        "llm_calls": len(called),
        "not_called": len(outputs) - len(called),
        "valid": len(valid),
        "json_valid_rate": len(valid) / len(called) if called else None,
        "json_valid_rate_ci95": [1.0, 1.0] if called and len(valid) == len(called) else None,
        "rejected_by_reason": dict(sorted(reasons.items())),
        "suspicious": sum(1 for r in valid if r.suspicious),
        "reports_with_invented_evidence_ids": sum(1 for r in called if r.invalid_evidence_ids),
        "fault_type_reported": dict(
            sorted(Counter(r.report.fault_type for r in valid if r.report).items())
        ),
        "new_api_calls": 0,
        "cache_hits": sum(1 for r in outputs if r.debug.get("cache_hit")),
        "prompt_tokens_new": 0,
        "completion_tokens_new": 0,
        "prompt_tokens_cached": prompt_tokens_cached,
        "completion_tokens_cached": completion_tokens_cached,
        "estimated_usd_by_tokens": 0.0,
        "cached_equivalent_usd_by_tokens": (
            prompt_tokens_cached / 1e6 * price_in + completion_tokens_cached / 1e6 * price_out
        ),
        "latency_ms_median": (
            float(np.median([r.debug["latency_ms"] for r in outputs])) if outputs else None
        ),
    }
    return stats, outputs


def run_pipeline(
    config_path: Path,
    run_id: str | None = None,
    write_db: bool = True,
    results_root: Path = RESULTS,
    output_root: Path | None = None,
    cache_path: Path = rca.LLM_CACHE,
) -> Path:
    """Execute the full M10-A pipeline and write outputs + runtime.json."""
    load_dotenv(REPO / ".env")
    wall_start = time.perf_counter()
    started_at = datetime.now(UTC)

    config_text = config_path.read_text(encoding="utf-8")
    config = rca.load_rca_config(config_path)
    fp = rca.config_fingerprint(config)
    print(f"method fingerprint {fp}")
    if fp != EXPECTED_METHOD_FINGERPRINT:
        raise ValueError(
            f"Method fingerprint {fp} != expected frozen {EXPECTED_METHOD_FINGERPRINT}"
        )

    reference_run_id = str(config["run_id"])
    effective_run_id = run_id or f"pipeline_{config['split']}_v1"
    out_dir = (output_root or results_root) / effective_run_id
    if out_dir.exists():
        raise SystemExit(
            f"{out_dir} already exists: results are never overwritten, use a new run_id"
        )

    if write_db:
        if clickhouse.run_exists(effective_run_id):
            raise SystemExit(f"run_id {effective_run_id!r} already exists in ClickHouse")
        with store.connect() as conn:
            if store.run_exists(conn, effective_run_id):
                raise SystemExit(f"run_id {effective_run_id!r} already exists in PostgreSQL")

    alerts_run = str(config["input"]["alerts_run"])
    evidence_run = str(config["input"]["evidence_run"])

    # Stage 1a: load CTAV judged candidates and retrieval evidence.
    t_load = time.perf_counter()
    loaded = load_alerts(alerts_run, evidence_run, effective_run_id, results_root=results_root)
    load_alerts_ms = (time.perf_counter() - t_load) * 1000.0

    # Stage 2 & 3: grouping + level-1 propagation.
    graph = load_graph()
    report, located, grouping_ms, propagation_ms = _evaluate_stages(
        config, loaded.inputs, graph, effective_run_id
    )

    # Stage 4: cache-only summarizer.
    t_sum = time.perf_counter()
    sum_stats, summaries = _summarize_from_cache(
        config=config,
        located=located,
        inputs=loaded.inputs,
        evidence_by_window=loaded.evidence_by_window,
        graph=graph,
        run_id=effective_run_id,
        reference_run_id=reference_run_id,
        cache_path=cache_path,
    )
    summarizer_ms = (time.perf_counter() - t_sum) * 1000.0
    report["summarizer"] = sum_stats

    # Stage 5: parity verification against M9 reference run BEFORE writing DB.
    parity = check_parity(located, summaries, results_root / reference_run_id)
    print(
        f"parity {effective_run_id} vs {reference_run_id}: "
        f"{parity['incidents_matched']}/{parity['incidents_expected']} incidents, "
        f"{parity['rankings_matched']}/{parity['incidents_expected']} rankings, "
        f"{parity['reports_matched']}/{parity['incidents_expected']} report hashes"
    )

    git_commit = _git_commit()
    report["git_commit"] = git_commit
    report["method_fingerprint"] = fp
    report["ctav_run"] = alerts_run
    report["evidence_run"] = evidence_run
    report["reference_run_id"] = reference_run_id
    report["parity"] = parity

    # Stage 1b & 6a: persist to ClickHouse and PostgreSQL.
    clickhouse_write_ms = 0.0
    postgres_write_ms = 0.0
    pg_counts: dict[str, int] = {}
    if write_db:
        t_ch = time.perf_counter()
        clickhouse.insert_alert_evaluations(loaded.eval_rows)
        clickhouse.insert_retrieval_trace(loaded.trace_rows)
        clickhouse_write_ms = (time.perf_counter() - t_ch) * 1000.0

        t_pg = time.perf_counter()
        snapshot_header = (
            f"# pipeline_run_id: {effective_run_id}\n"
            f"# reference_run_id: {reference_run_id}\n"
            f"{config_text}"
        )
        with store.connect() as conn:
            store.register_run(
                conn,
                effective_run_id,
                snapshot_header,
                git_commit,
                str(config["split"]),
                int(config.get("seed", 42)),
                started_at,
                notes=f"py -m services.rca_agent.pipeline (replay from {alerts_run}, ref {reference_run_id})",
            )
            store.insert_incidents(conn, [item.labelled.incident for item in located])
            for result in summaries:
                if result.report is not None:
                    store.insert_report(
                        conn, result.report, result.suspicious, result.debug.get("latency_ms")
                    )
                else:
                    store.insert_rejected(
                        conn,
                        result.incident_id,
                        effective_run_id,
                        result.raw_output,
                        result.reject_reason or "",
                    )
            store.finish_run(conn, effective_run_id, datetime.now(UTC))
            conn.commit()
            pg_counts = store.counts(conn, effective_run_id)
        postgres_write_ms = (time.perf_counter() - t_pg) * 1000.0
        report["postgres_rows"] = pg_counts

    # Stage 6b: write result directory + runtime.json.
    snapshot_text = (
        f"# pipeline_run_id: {effective_run_id}\n"
        f"# reference_run_id: {reference_run_id}\n"
        f"{config_text}"
    )
    rca.write(report, located, summaries, out_dir, snapshot_text)

    e2e_wall_ms = (time.perf_counter() - wall_start) * 1000.0
    runtime = {
        "run_id": effective_run_id,
        "split": config["split"],
        "reference_run_id": reference_run_id,
        "alerts_run": alerts_run,
        "evidence_run": evidence_run,
        "method_fingerprint": fp,
        "finished_at": datetime.now(UTC).isoformat(),
        "latency_note": (
            "Replay-from-cache latency only (CTAV verdicts and RCA summaries read 100% from "
            "disk/cache; not live LLM API latency)."
        ),
        "stages_ms": {
            "load_alerts_ms": round(load_alerts_ms, 3),
            "clickhouse_write_ms": round(clickhouse_write_ms, 3),
            "grouping_ms": round(grouping_ms, 3),
            "propagation_ms": round(propagation_ms, 3),
            "summarizer_ms": round(summarizer_ms, 3),
            "postgres_write_ms": round(postgres_write_ms, 3),
            "e2e_wall_ms": round(e2e_wall_ms, 3),
        },
        "counts": {
            "candidates_loaded": len(loaded.eval_rows),
            "confirmed_alerts": len(loaded.inputs.alerts),
            "retrieval_trace_rows": len(loaded.trace_rows),
            "incidents": len(located),
            "diagnostic_reports": sum(1 for r in summaries if r.report is not None),
            "diagnostic_rejected": sum(1 for r in summaries if r.report is None),
            "postgres_rows": pg_counts,
        },
        "tokens_from_cache": {
            "ctav_judge_prompt_tokens": loaded.ctav_prompt_tokens,
            "ctav_judge_completion_tokens": loaded.ctav_completion_tokens,
            "rca_summarizer_prompt_tokens": sum_stats["prompt_tokens_cached"],
            "rca_summarizer_completion_tokens": sum_stats["completion_tokens_cached"],
        },
        "llm_operations": {
            "api_calls": 0,
            "new_api_calls": 0,
            "summarizer_llm_calls": sum_stats["llm_calls"],
            "summarizer_cache_hits": sum_stats["cache_hits"],
            "cache_hit_rate": (
                sum_stats["cache_hits"] / sum_stats["llm_calls"]
                if sum_stats["llm_calls"]
                else 1.0
            ),
            "estimated_usd_by_tokens": 0.0,
        },
        "parity": parity,
    }
    (out_dir / "runtime.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
    (out_dir / "git_commit.txt").write_text(git_commit + "\n", encoding="utf-8")
    print(f"wrote {out_dir}")
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="py -m services.rca_agent.pipeline",
        description="M10-A end-to-end replay pipeline: CTAV -> ClickHouse -> RCA -> PostgreSQL.",
    )
    parser.add_argument("--config", type=Path, required=True, help="RCA config YAML (rca_final*.yaml)")
    parser.add_argument("--run-id", default=None, help="Override output run_id (default: pipeline_<split>_v1)")
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip ClickHouse and PostgreSQL writes (for offline dry runs/tests).",
    )
    args = parser.parse_args()
    run_pipeline(args.config, run_id=args.run_id, write_db=not args.no_db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
