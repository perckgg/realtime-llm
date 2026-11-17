"""Read-only FastAPI backend for the AIOps RCA Platform dashboard (01 SS6.6, M10-B)."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Query

from services.api import readers
from services.api.schemas import (
    AlertDetailResponse,
    AlertResponse,
    HealthResponse,
    IncidentDetailResponse,
    IncidentResponse,
    RunMetricsResponse,
    RunResponse,
)

app = FastAPI(
    title="AIOps RCA Platform API",
    description="Read-only API serving ClickHouse, PostgreSQL, and eval/results artifacts.",
    version="0.1.0",
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/runs", response_model=list[RunResponse])
def get_runs() -> list[RunResponse]:
    return readers.list_runs()


@router.get("/runs/{run_id}/metrics", response_model=RunMetricsResponse)
def get_run_metrics(run_id: str) -> RunMetricsResponse:
    metrics = readers.get_run_metrics(run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Metrics not found for run {run_id!r}")
    return metrics


@router.get("/alerts", response_model=list[AlertResponse])
def get_alerts(
    run_id: str = Query(..., description="Experiment or pipeline run_id"),
    verdict: str | None = Query(default=None, description="Optional verdict filter"),
    limit: int | None = Query(default=None, ge=1, le=50000),
    offset: int = Query(default=0, ge=0),
) -> list[AlertResponse]:
    alerts = readers.list_alerts(run_id=run_id, verdict=verdict, limit=limit, offset=offset)
    if alerts is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return alerts


@router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
def get_alert_detail(
    alert_id: str,
    run_id: str | None = Query(default=None),
) -> AlertDetailResponse:
    detail = readers.get_alert_detail(alert_id=alert_id, run_id=run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id!r} not found")
    return detail


@router.get("/incidents", response_model=list[IncidentResponse])
def get_incidents(
    run_id: str = Query(..., description="Experiment or pipeline run_id"),
) -> list[IncidentResponse]:
    incidents = readers.list_incidents(run_id=run_id)
    if incidents is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return incidents


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(incident_id: str) -> IncidentDetailResponse:
    detail = readers.get_incident_detail(incident_id=incident_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id!r} not found")
    return detail


# Serve at both root (for Vite proxy rewrite & TestClient) and /api (for direct browser/nginx).
app.include_router(router)
app.include_router(router, prefix="/api")
