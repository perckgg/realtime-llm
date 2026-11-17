"""Pydantic v2 response schemas mirroring `services/web/src/api/types.ts`."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from packages.schemas.models import DiagnosticReport

Verdict = Literal["TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"]
EvidenceOrigin = Literal["local", "graph", "mixed", "none"]
GraphRole = Literal["root_cause", "ground_truth", "affected", "healthy"]


class HealthResponse(BaseModel):
    status: str


class RunResponse(BaseModel):
    run_id: str
    retrieval_strategy: str
    split: str
    seed: int
    git_commit: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    notes: str
    alert_count: int = 0


class MetricWithCIResponse(BaseModel):
    value: float
    ci_low: float
    ci_high: float


class RunMetricsResponse(BaseModel):
    run_id: str
    retrieval_strategy: str
    n_windows: int
    tp: int
    fp: int
    fn: int
    tn: int
    precision: MetricWithCIResponse
    recall: MetricWithCIResponse
    f1: MetricWithCIResponse
    fpr: MetricWithCIResponse
    hit_at_1: MetricWithCIResponse
    hit_at_3: MetricWithCIResponse
    context_precision: MetricWithCIResponse
    retrieval_latency_p95_ms: float
    llm_latency_p95_ms: float
    cache_hit_rate: float
    json_valid_rate: float


class RescueComponentsResponse(BaseModel):
    lambda_log: float
    phi_topo: float
    delta_time: float


class WindowLabelResponse(BaseModel):
    is_fault: bool
    fault_type: str | None
    root_cause_service: str | None


class AlertResponse(BaseModel):
    alert_id: str
    candidate_id: str
    window_id: str
    run_id: str
    service: str
    ts: datetime
    anomaly_score: float
    candidate_source: str
    rescue_score: float | None
    rescue_components: RescueComponentsResponse | None

    retrieval_strategy: str
    retrieval_latency_ms: float
    context_event_count: int
    context_tokens: int
    retrieval_truncated: bool

    verdict: Verdict
    confidence: float
    judge_backend: str
    llm_latency_ms: float
    cache_hit: bool
    downgraded_by_evidence_rule: bool

    raw_verdict: Verdict
    routing_tier: int
    evidence_origin: EvidenceOrigin
    threshold_applied: float | None
    downgraded_by_gating: bool
    downgraded_by_anchoring: bool

    label: WindowLabelResponse


class ContextEventResponse(BaseModel):
    event_id: str
    modality: Literal["log", "trace", "metric"]
    ts: datetime
    service: str
    content: str
    score: float
    debug: dict[str, str | int | float | bool]


class MetricPointResponse(BaseModel):
    ts: datetime
    value: float


class AlertDetailResponse(AlertResponse):
    reasoning: str
    evidence_event_ids: list[str]
    context_events: list[ContextEventResponse]
    metric_series: list[MetricPointResponse]
    metric_name: str
    detector_threshold: float


class GroupingReasonResponse(BaseModel):
    temporal_window_sec: float
    graph_edges_used: int


class IncidentResponse(BaseModel):
    incident_id: str
    run_id: str
    alert_ids: list[str]
    services: list[str]
    start_ts: datetime
    end_ts: datetime
    grouping_reason: GroupingReasonResponse
    root_cause_service: str | None
    ground_truth_service: str | None
    fault_type: str | None


class GraphEdgeResponse(BaseModel):
    source: str
    target: str
    call_count: int
    error_rate: float
    on_path: bool


class GraphNodeResponse(BaseModel):
    service: str
    role: GraphRole
    alert_count: int
    max_anomaly_score: float


class IncidentDetailResponse(IncidentResponse):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    report: DiagnosticReport | None
    rejected_reason: str | None
    alerts: list[AlertResponse]
