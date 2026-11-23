"""Pydantic v2 models shared by every service.

Copied verbatim from docs/Final_Thesis_Phase2/03-schemas-and-contracts.md §1.
No service may redefine these — import from here (rule R-B2 in
docs/Final_Thesis_Phase2/05-agent-coding-rules.md).

Implemented through milestone M1: TelemetryWindow, WindowLabel, AlertCandidate
and their pieces (M0), ContextEvent, RetrievalBudget, RetrievalResult and
JudgedAlert with the CTAV fields (M1, QD-011/QD-016), Incident (M6, grouping).
DiagnosticReport is added when the RCA summarizer is ported, to keep this
module in sync with what is actually used.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MetricPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: float
    ts: datetime


class LogEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    ts: datetime
    service: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    message: str
    trace_id: str | None = None
    span_id: str | None = None


class TraceSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    trace_id: str
    span_id: str
    parent_span_id: str | None
    service: str
    operation: str
    start_ts: datetime
    duration_ms: float
    status_code: int | None = None
    error: bool = False
    exception_message: str | None = None


class WindowLabel(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_fault: bool
    fault_type: str | None  # network_delay | cpu_contention | ...
    root_cause_service: str | None


class TelemetryWindow(BaseModel):
    """Unit of data entering the pipeline (03-schemas-and-contracts.md §1.1)."""

    model_config = ConfigDict(frozen=True)

    window_id: str  # deterministic: hash(service + start_ts), see make_window_id
    service: str
    pod: str | None = None  # QD-015: ground truth and rolling buffers are per pod (QD-003)
    start_ts: datetime
    end_ts: datetime
    metrics: list[MetricPoint] = []
    logs: list[LogEvent] = []
    spans: list[TraceSpan] = []
    # ground truth, only present when running on a labelled dataset
    label: WindowLabel | None = None


class AlertCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: str
    window_id: str
    service: str
    ts: datetime
    anomaly_score: float
    source: Literal["metric", "rescue"]  # rescue = promoted by the Rescue Score gate
    rescue_score: float | None = None
    rescue_components: dict[str, float] | None = None  # lambda_log, phi_topo, delta_time
    # QD-016: what the BM25 query and the GD1 judge prompt read from the window
    # (GD1's alert_candidate carried node_id, time_window, metric_snapshot,
    # top_features). Never ground truth.
    pod: str | None = None
    end_ts: datetime | None = None
    metric_snapshot: dict[str, float] = {}
    top_features: list[str] = []


Verdict = Literal["TRUE_ALERT", "FALSE_POSITIVE", "UNCERTAIN"]


class ContextEvent(BaseModel):
    """One piece of evidence a RetrievalStrategy hands to the judge (03 SS1.3)."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    modality: Literal["log", "trace", "metric"]
    ts: datetime
    service: str
    content: str  # text put in the prompt
    score: float  # retrieval score
    origin: Literal["local", "graph"] = "local"  # QD-011: graph = reached by topology expansion
    graph_distance: int | None = None  # d_G(service, s0); None if unreachable
    debug: dict[str, Any] = {}  # why it was picked: BM25 rank, graph distance, channel...


class RetrievalBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    top_k: int = 6
    max_tokens: int = 4000
    timeout_ms: int = 500


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    events: list[ContextEvent]
    latency_ms: float
    token_estimate: int
    truncated: bool = False
    debug: dict[str, Any] = {}


class JudgedAlert(BaseModel):
    """Judge output (03 SS1.4). `verdict` is after the decision rules,
    `raw_verdict` is the LLM's own label, so policy ablations (H3) never need
    a new LLM call."""

    model_config = ConfigDict(frozen=True)

    alert_id: str
    candidate_id: str
    window_id: str
    service: str
    ts: datetime
    verdict: Verdict
    confidence: float  # 0.0 - 1.0
    reasoning: str
    evidence_event_ids: list[str]  # references ContextEvent.event_id
    judge_backend: str  # gemini-2.5-flash | mock (G-port only) -- QD-021 (flash-lite only for G-paper cache)
    llm_latency_ms: float
    cache_hit: bool
    downgraded_by_evidence_rule: bool = False
    # CTAV (QD-011, milestone M1)
    raw_verdict: Verdict
    routing_tier: Literal[1, 2] = 1  # C4: 1 = BM25 only, 2 = topology expanded
    evidence_origin: Literal["local", "graph", "mixed", "none"] = "none"
    threshold_applied: float | None = None  # theta_local or theta_topo
    downgraded_by_gating: bool = False  # C2
    downgraded_by_anchoring: bool = False  # C3
    # QD-016: model version returned by the API, cache key, tokens, parse
    # errors, the LLM's raw evidence list -- what a re-run or an audit needs.
    debug: dict[str, Any] = {}


class Incident(BaseModel):
    """Alerts grouped by time and service dependency (03 SS1.5, services/rca_agent/grouping.py)."""

    model_config = ConfigDict(frozen=True)

    incident_id: str
    run_id: str
    alert_ids: list[str]
    services: list[str]
    start_ts: datetime
    end_ts: datetime
    grouping_reason: dict[str, Any]  # temporal_window_sec, graph_edges_used


# --- Diagnostic report of the RCA agent (03 SS2, added at M9 with services/rca_agent/summarizer.py) ---


class SuggestedAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str  # a description, NOT an executable command
    priority: Literal["high", "medium", "low"]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    modality: Literal["log", "trace", "metric"]
    service: str
    ts: datetime
    excerpt: str


class DiagnosticReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    incident_id: str
    run_id: str
    root_cause_service: str
    fault_type: str  # network_delay | cpu_contention | exception | unknown
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(min_length=1)  # at least one, or the report is not published
    propagation_path: list[str]  # services in propagation order
    suggested_actions: list[SuggestedAction]
    generated_at: datetime
    llm_backend: str
    schema_version: str = "1.0"
