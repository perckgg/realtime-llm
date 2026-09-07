"""Pydantic v2 models shared by every service.

Copied verbatim from docs/Final_Thesis_Phase2/03-schemas-and-contracts.md §1.
No service may redefine these — import from here (rule R-B2 in
docs/Final_Thesis_Phase2/05-agent-coding-rules.md).

Only the models needed through Week 2 (TelemetryWindow, WindowLabel,
AlertCandidate and their pieces) are implemented so far. RetrievalResult,
JudgedAlert, Incident and DiagnosticReport belong to later weeks
(docs/CURRENT-WEEK.md) and are added when those services are ported, to keep
this module in sync with what is actually used.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
