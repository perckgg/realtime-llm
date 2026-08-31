from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from src.decision.audit_logger import AuditLogger
from src.decision.policy import build_alert_candidate, decide, decide_llm_budget_exhausted, gate_alert
from src.detectors.factory import build_detector
from src.evaluation.report import write_result
from src.ingestion.log_loader import load_logs
from src.ingestion.metric_loader import load_metrics
from src.llm.local_first_judge import build_judge_client
from src.llm.prompt_composer import compose_prompt, estimate_tokens
from src.llm.scheduler import LLMRequestScheduler, LLMRouteDecision
from src.models import DetectorResult, LogEvent, MetricWindow
from src.phase2.retrieval.pipeline_adapter import PipelineTopologyAwareRetriever
from src.phase2.retrieval.topology_candidate_expander import ServiceTopology
from src.preprocessing.log_preprocessing import preprocess_logs
from src.preprocessing.metric_preprocessing import create_metric_windows
from src.retrieval.context_store import LocalContextStore
from src.retrieval.context_signal import ContextSignal, evaluate_context_signal
from src.retrieval.retriever import HybridRetriever


def run_pipeline(
    config: dict[str, Any],
    mode: str,
    replay_stream: bool = False,
    output_mode: str | None = None,
    window_indices: list[int] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    metrics = load_metrics(config["data"]["metric_path"])
    windows = create_metric_windows(
        metrics,
        int(config["preprocessing"]["window_size"]),
        int(config["preprocessing"]["stride"]),
        str(config["preprocessing"]["normalization"]),
    )
    detector = build_detector(config.get("detector", {}), windows)
    retrieval_config = config.get("retrieval", {})
    retrieval_backend = _configured_retrieval_backend(retrieval_config)
    store_backend = _store_backend_for_retrieval(retrieval_config, retrieval_backend)
    store = LocalContextStore(
        vector_db=store_backend,
        embedding_dimensions=int(retrieval_config.get("embedding_dimensions", 512)),
    )
    log_events: list[LogEvent] = []
    if mode == "hybrid":
        log_events = sorted(preprocess_logs(load_logs(config["data"]["log_path"])), key=lambda event: event.timestamp)
        if not replay_stream:
            store.add_events(log_events)
    retriever = _build_retriever(store, retrieval_config, retrieval_backend)
    llm_provider = str(config["llm"]["provider"])
    judge_client = build_judge_client(config["llm"])
    scheduler = LLMRequestScheduler(config.get("llm_scheduler", {}))
    audit_records: list[dict[str, Any]] = []
    evaluation_config = config.get("evaluation", {})
    gate_config = config.get("llm_gate", {})
    decision_config = config.get("decision", {})
    confidence_threshold = float(decision_config["confidence_threshold"])
    require_evidence_for_true_alert = bool(decision_config.get("require_evidence_for_true_alert", False))
    max_windows = int(evaluation_config.get("max_windows", 0) or 0)
    max_llm_calls = int(evaluation_config.get("max_llm_calls", gate_config.get("max_total_calls", 0)) or 0)
    max_llm_calls_per_minute = int(gate_config.get("max_llm_calls_per_minute", 0) or 0)
    if llm_provider == "mock":
        max_llm_calls_per_minute = 0
    min_llm_interval_seconds = 60.0 / max_llm_calls_per_minute if max_llm_calls_per_minute else 0.0
    llm_calls_made = 0
    actual_api_calls_made = 0
    last_llm_call_at = 0.0
    streaming_config = config.get("streaming", {})
    stream_state = _StreamState(
        enabled=replay_stream,
        speedup=float(streaming_config.get("speedup", 0) or 0),
        max_sleep_seconds=float(streaming_config.get("max_sleep_seconds", 0) or 0),
        ingest_lag=timedelta(seconds=float(streaming_config.get("ingest_lag_seconds", 0) or 0)),
    )
    selected_windows = _select_windows(windows, max_windows, replay_stream, window_indices)

    for sequence, window in enumerate(selected_windows):
        if replay_stream:
            _replay_wait(stream_state, window)
            if mode == "hybrid":
                _ingest_stream_context(store, log_events, stream_state, window)
        e2e_started = time.perf_counter()
        detector_result = detector.score(window)
        alert = build_alert_candidate(window, detector_result)
        pre_retrieved_contexts: list[dict[str, Any]] = []
        pre_retrieval_latency = 0.0
        retrieval_attempted = False
        rescue_signal: ContextSignal | None = None
        rescue_checked = False
        rescue_promoted = False
        if not detector_result.is_candidate:
            (
                detector_result,
                alert,
                pre_retrieved_contexts,
                pre_retrieval_latency,
                rescue_signal,
                rescue_checked,
                rescue_promoted,
            ) = _maybe_promote_with_context_rescue(
                config=config,
                mode=mode,
                retriever=retriever,
                window=window,
                detector_result=detector_result,
                alert=alert,
            )
            retrieval_attempted = rescue_checked
        if not detector_result.is_candidate:
            audit_records.append(
                {
                    "alert_id": alert.alert_id,
                    "window_id": alert.window_id,
                    "ground_truth": alert.ground_truth,
                    "service_id": alert.service_id,
                    "node_id": alert.node_id,
                    "fault_type": alert.fault_type,
                    "is_candidate": False,
                    "anomaly_score": alert.anomaly_score,
                    "retrieved_context_ids": [ctx["doc_id"] for ctx in pre_retrieved_contexts],
                    "retrieved_context_count": len(pre_retrieved_contexts),
                    "context_token_count": _context_token_count(pre_retrieved_contexts),
                    "prompt_token_count": 0,
                    "completion_token_count": 0,
                    "detector_latency_ms": round(detector_result.detector_latency_ms, 4),
                    "retrieval_latency_ms": round(pre_retrieval_latency, 4),
                    "retrieval_attempted": retrieval_attempted,
                    "llm_latency_ms": 0.0,
                    "end_to_end_latency_ms": round((time.perf_counter() - e2e_started) * 1000, 4),
                    "final_decision": "suppress",
                    "fallback_status": "detector_normal",
                    "llm_called": False,
                    "llm_call_avoided": True,
                    "gate_action": "context_rescue_checked" if rescue_checked else "not_candidate",
                    "json_valid": False,
                    "llm_response": None,
                    "llm_error": None,
                    "actual_api_calls": 0,
                    "cache_hits": 0,
                    "retrieval_backend": _retrieval_backend_name(retriever, store),
                    "retrieval_backend_warning": _retrieval_backend_warning(retriever, store),
                    "context_rescue_checked": rescue_checked,
                    "context_rescue_promoted": rescue_promoted,
                    "context_rescue_reason": rescue_signal.reason if rescue_signal else None,
                    "context_signal_score": rescue_signal.score if rescue_signal else 0.0,
                    **_topology_audit_fields(retriever, alert, pre_retrieved_contexts),
                    **_scheduler_record_fields(None),
                    **_stream_record_fields(stream_state, sequence),
                }
            )
            continue
        gate = gate_alert(alert.anomaly_score, config["llm_gate"])
        contexts: list[dict[str, Any]] = pre_retrieved_contexts
        retrieval_latency = pre_retrieval_latency
        judge_result = None
        llm_called = False
        schedule_decision: LLMRouteDecision | None = None

        if mode == "detector_only":
            final_decision, fallback_status = decide(
                alert,
                None,
                confidence_threshold,
                require_evidence_for_true_alert=require_evidence_for_true_alert,
            )
            gate_action = "detector_only"
        else:
            gate_action = gate.action
            if gate.action == "ignore":
                final_decision, fallback_status = "suppress", "gate_ignored"
            elif gate.action == "direct_alert":
                final_decision, fallback_status = "route_alert", "gate_direct"
            else:
                if max_llm_calls and llm_calls_made >= max_llm_calls:
                    final_decision, fallback_status = decide_llm_budget_exhausted(decision_config)
                    gate_action = "llm_budget_exhausted"
                else:
                    if mode == "hybrid" and not contexts:
                        retrieval_attempted = True
                        contexts, retrieval_latency = retriever.retrieve(alert)
                    schedule_decision = scheduler.plan(
                        alert,
                        context_signal_score=rescue_signal.score if rescue_signal else 0.0,
                        provider=llm_provider,
                        api_calls_made=actual_api_calls_made,
                        max_api_calls=int(config.get("llm_scheduler", {}).get("max_api_calls_per_run", 0) or 0),
                    )
                    if schedule_decision.action == "defer":
                        final_decision, fallback_status = "manual_review", "llm_deferred"
                        gate_action = "llm_deferred"
                    else:
                        prompt = compose_prompt(alert, contexts)
                        if min_llm_interval_seconds and last_llm_call_at:
                            elapsed = time.perf_counter() - last_llm_call_at
                            if elapsed < min_llm_interval_seconds:
                                time.sleep(min_llm_interval_seconds - elapsed)
                        judge_result = judge_client.judge(
                            prompt,
                            contexts,
                            alert=alert,
                            allow_api_fallback=schedule_decision.action != "local_only",
                        )
                        last_llm_call_at = time.perf_counter()
                        llm_called = True
                        llm_calls_made += 1
                        if judge_result.actual_api_call:
                            actual_api_calls_made += 1
                        scheduler.record_result(
                            judge_result.error or judge_result.api_fallback_error,
                            judge_result.actual_api_call,
                        )
                        final_decision, fallback_status = decide(
                            alert,
                            judge_result,
                            confidence_threshold,
                            require_evidence_for_true_alert=require_evidence_for_true_alert,
                        )

        record = {
            "alert_id": alert.alert_id,
            "window_id": alert.window_id,
            "ground_truth": alert.ground_truth,
            "service_id": alert.service_id,
            "node_id": alert.node_id,
            "fault_type": alert.fault_type,
            "is_candidate": True,
            "anomaly_score": alert.anomaly_score,
            "retrieved_context_ids": [ctx["doc_id"] for ctx in contexts],
            "retrieved_context_count": len(contexts),
            "context_token_count": _context_token_count(contexts),
            "retrieval_backend": _retrieval_backend_name(retriever, store),
            "retrieval_backend_warning": _retrieval_backend_warning(retriever, store),
            "prompt_token_count": judge_result.prompt_tokens if judge_result else 0,
            "completion_token_count": judge_result.completion_tokens if judge_result else 0,
            "detector_latency_ms": round(detector_result.detector_latency_ms, 4),
            "retrieval_latency_ms": round(retrieval_latency, 4),
            "retrieval_attempted": retrieval_attempted,
            "llm_latency_ms": round(judge_result.latency_ms, 4) if judge_result else 0.0,
            "end_to_end_latency_ms": round((time.perf_counter() - e2e_started) * 1000, 4),
            "final_decision": final_decision,
            "fallback_status": fallback_status,
            "llm_called": llm_called,
            "llm_call_avoided": (
                gate.llm_call_avoided
                or mode == "detector_only"
                or gate_action in {"llm_budget_exhausted", "llm_deferred"}
            ),
            "gate_action": gate_action,
            "json_valid": judge_result.valid_json if judge_result else False,
            "llm_response": judge_result.raw_response if judge_result else None,
            "llm_error": judge_result.error if judge_result else None,
            "token_source": judge_result.token_source if judge_result else None,
            "llm_provider": judge_result.provider if judge_result else None,
            "llm_model": judge_result.model if judge_result else None,
            "api_fallback_used": judge_result.api_fallback_used if judge_result else False,
            "api_fallback_reason": judge_result.api_fallback_reason if judge_result else None,
            "api_fallback_error": judge_result.api_fallback_error if judge_result else None,
            "local_result_valid_json": judge_result.local_result_valid_json if judge_result else None,
            "local_result_label": judge_result.local_result_label if judge_result else None,
            "local_result_confidence": judge_result.local_result_confidence if judge_result else None,
            "model_route": judge_result.model_route if judge_result else None,
            "primary_local_model": judge_result.primary_local_model if judge_result else None,
            "fallback_model": judge_result.fallback_model if judge_result else None,
            "model_fallback_used": judge_result.model_fallback_used if judge_result else False,
            "model_fallback_reason": judge_result.model_fallback_reason if judge_result else None,
            "llm_cache_hit": judge_result.cache_hit if judge_result else False,
            "actual_api_call": judge_result.actual_api_call if judge_result else False,
            "actual_api_calls": 1 if judge_result and judge_result.actual_api_call else 0,
            "cache_hits": 1 if judge_result and judge_result.cache_hit else 0,
            "llm_retry_count": judge_result.retry_count if judge_result else 0,
            "llm_backoff_sleep_ms": round(judge_result.backoff_sleep_ms, 4) if judge_result else 0.0,
            "context_rescue_checked": rescue_checked,
            "context_rescue_promoted": rescue_promoted,
            "context_rescue_reason": rescue_signal.reason if rescue_signal else None,
            "context_signal_score": rescue_signal.score if rescue_signal else 0.0,
            **_topology_audit_fields(retriever, alert, contexts),
            **_scheduler_record_fields(schedule_decision),
            **_stream_record_fields(stream_state, sequence),
        }
        audit_records.append(record)

    report_mode = output_mode or mode
    audit_path = AuditLogger(config["evaluation"]["audit_dir"]).write(report_mode, audit_records)
    result_path = write_result(report_mode, audit_records, config["evaluation"]["output_dir"], config=config)
    return audit_records, f"wrote {audit_path} and {result_path}"


class _StreamState:
    def __init__(self, enabled: bool, speedup: float, max_sleep_seconds: float, ingest_lag: timedelta) -> None:
        self.enabled = enabled
        self.speedup = speedup
        self.max_sleep_seconds = max_sleep_seconds
        self.ingest_lag = ingest_lag
        self.previous_window_start = None
        self.log_cursor = 0
        self.ingested_context_events = 0


def _select_windows(
    windows: list[MetricWindow],
    max_windows: int,
    replay_stream: bool,
    window_indices: list[int] | None = None,
) -> list[MetricWindow]:
    if window_indices is not None:
        selected = [windows[i] for i in window_indices if 0 <= i < len(windows)]
    else:
        selected = windows[:max_windows or None]
    if replay_stream:
        return sorted(selected, key=lambda window: window.start_time)
    return selected


def _replay_wait(state: _StreamState, window: MetricWindow) -> None:
    if not state.enabled:
        return
    if state.speedup <= 0 or state.previous_window_start is None:
        state.previous_window_start = window.start_time
        return
    delta = max(0.0, (window.start_time - state.previous_window_start).total_seconds())
    sleep_seconds = delta / state.speedup
    if state.max_sleep_seconds:
        sleep_seconds = min(sleep_seconds, state.max_sleep_seconds)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    state.previous_window_start = window.start_time


def _ingest_stream_context(
    store: LocalContextStore,
    events: list[LogEvent],
    state: _StreamState,
    window: MetricWindow,
) -> None:
    watermark = window.end_time + state.ingest_lag
    batch: list[LogEvent] = []
    while state.log_cursor < len(events) and events[state.log_cursor].timestamp <= watermark:
        batch.append(events[state.log_cursor])
        state.log_cursor += 1
    if batch:
        store.add_events(batch)
        state.ingested_context_events += len(batch)


def _stream_record_fields(state: _StreamState, sequence: int) -> dict[str, Any]:
    if not state.enabled:
        return {}
    return {
        "stream_sequence": sequence,
        "stream_context_events_ingested": state.ingested_context_events,
    }


def _scheduler_record_fields(decision: LLMRouteDecision | None) -> dict[str, Any]:
    if decision is None:
        return {
            "scheduler_action": None,
            "scheduler_reason": None,
            "priority_score": None,
            "scheduled_delay_seconds": 0.0,
            "api_deferred": False,
        }
    return {
        "scheduler_action": decision.action,
        "scheduler_reason": decision.reason,
        "priority_score": decision.priority_score,
        "scheduled_delay_seconds": decision.delay_seconds,
        "api_deferred": decision.api_deferred,
    }


def _context_token_count(contexts: list[dict[str, Any]]) -> int:
    return sum(estimate_tokens(str(context.get("message", ""))) for context in contexts)


def _configured_retrieval_backend(retrieval_config: dict[str, Any]) -> str:
    return str(
        retrieval_config.get(
            "backend",
            retrieval_config.get("retrieval_backend", retrieval_config.get("vector_db", "local")),
        )
    )


def _store_backend_for_retrieval(retrieval_config: dict[str, Any], retrieval_backend: str) -> str:
    if retrieval_backend == "topology_aware_fusion":
        return str(retrieval_config.get("lexical_backend", "hybrid_bm25"))
    return str(retrieval_config.get("vector_db", "local"))


def _build_retriever(
    store: LocalContextStore,
    retrieval_config: dict[str, Any],
    retrieval_backend: str,
) -> Any:
    if retrieval_backend == "topology_aware_fusion":
        graph_path = Path(str(retrieval_config.get("graph_path", "outputs/phase2/service_graph_undirected.json")))
        warning = None
        if graph_path.exists():
            topology = ServiceTopology.from_undirected_json(graph_path)
        else:
            topology = ServiceTopology({})
            warning = f"topology graph '{graph_path}' missing; using empty graph"
        retriever = PipelineTopologyAwareRetriever(store, topology, retrieval_config)
        if warning:
            retriever.backend_warning = warning
        return retriever
    return HybridRetriever(
        store,
        top_k=int(retrieval_config.get("top_k", 5)),
        time_margin_minutes=int(retrieval_config.get("time_margin_minutes", 5)),
        search_k=int(retrieval_config.get("search_k", 250)),
        semantic_weight=float(retrieval_config.get("semantic_weight", 0.45)),
        time_weight=float(retrieval_config.get("time_weight", 0.25)),
        metadata_weight=float(retrieval_config.get("metadata_weight", 0.2)),
        signal_weight=float(retrieval_config.get("signal_weight", 0.1)),
    )


def _retrieval_backend_name(retriever: Any, store: LocalContextStore) -> str:
    return str(getattr(retriever, "actual_backend", store.actual_backend))


def _retrieval_backend_warning(retriever: Any, store: LocalContextStore) -> str | None:
    return getattr(retriever, "backend_warning", None) or store.backend_warning


def _topology_audit_fields(retriever: Any, alert: Any, contexts: list[dict[str, Any]]) -> dict[str, Any]:
    debug = getattr(retriever, "last_debug", None)
    if not debug or debug.alert_id != alert.alert_id or debug.window_id != alert.window_id:
        debug = None
    score_components = [
        {
            "context_id": context.get("context_id") or context.get("doc_id"),
            "bm25_raw": context.get("bm25_raw"),
            "bm25_norm": context.get("bm25_norm"),
            "time_sim": context.get("time_sim"),
            "graph_distance": context.get("graph_distance"),
            "graph_sim": context.get("graph_sim"),
            "score_final": context.get("score_final"),
            "rank": context.get("rank"),
        }
        for context in contexts
        if "score_final" in context
    ]
    return {
        "candidate_pool_size": debug.candidate_pool_size if debug else 0,
        "bm25_candidate_count": debug.bm25_candidate_count if debug else 0,
        "graph_candidate_count": debug.graph_candidate_count if debug else 0,
        "duplicates_removed": debug.duplicates_removed if debug else 0,
        "context_coverage": bool(contexts),
        "topology_context_ratio": _topology_context_ratio(contexts),
        "avg_graph_distance": _avg_graph_distance(contexts),
        "bm25_norm": [component["bm25_norm"] for component in score_components],
        "time_sim": [component["time_sim"] for component in score_components],
        "graph_distance": [component["graph_distance"] for component in score_components],
        "graph_sim": [component["graph_sim"] for component in score_components],
        "score_final": [component["score_final"] for component in score_components],
        "retrieved_context_score_components": score_components,
    }


def _topology_context_ratio(contexts: list[dict[str, Any]]) -> float:
    if not contexts:
        return 0.0
    graph_contexts = [
        context
        for context in contexts
        if "graph" in set(context.get("source_flags") or [])
    ]
    return round(len(graph_contexts) / len(contexts), 4)


def _avg_graph_distance(contexts: list[dict[str, Any]]) -> float:
    distances = [
        float(context["graph_distance"])
        for context in contexts
        if context.get("graph_distance") is not None
    ]
    return round(sum(distances) / len(distances), 4) if distances else 0.0


def _maybe_promote_with_context_rescue(
    config: dict[str, Any],
    mode: str,
    retriever: Any,
    window: MetricWindow,
    detector_result: DetectorResult,
    alert: Any,
) -> tuple[DetectorResult, Any, list[dict[str, Any]], float, ContextSignal | None, bool, bool]:
    rescue_config = config.get("candidate_rescue", {})
    if mode != "hybrid" or not rescue_config.get("enabled", False):
        return detector_result, alert, [], 0.0, None, False, False
    min_detector_score = float(rescue_config.get("min_detector_score", 0.0))
    if detector_result.anomaly_score < min_detector_score:
        return detector_result, alert, [], 0.0, None, False, False
    contexts, retrieval_latency = retriever.retrieve(alert)
    signal = evaluate_context_signal(
        contexts,
        min_context_score=float(rescue_config.get("min_context_score", 0.7)),
        min_trace_duration_ms=float(rescue_config.get("min_trace_duration_ms", 1.0)),
    )
    if not signal.should_promote:
        return detector_result, alert, contexts, retrieval_latency, signal, True, False
    promoted_score = max(detector_result.anomaly_score, float(rescue_config.get("promoted_score", 0.85)), signal.score)
    promoted_top_features = list(dict.fromkeys([*detector_result.top_features, "context_signal"]))
    promoted_result = DetectorResult(
        window_id=detector_result.window_id,
        is_candidate=True,
        anomaly_score=round(min(promoted_score, 1.0), 4),
        detector_label="context_rescue",
        top_features=promoted_top_features[:4],
        detector_latency_ms=detector_result.detector_latency_ms,
    )
    return promoted_result, build_alert_candidate(window, promoted_result), contexts, retrieval_latency, signal, True, True
