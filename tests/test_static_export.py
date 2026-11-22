"""Verification tests for the GitHub Pages static API exporter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_static_pages_api import DEFAULT_RUN_IDS, DEMO_CASES_PATH, export_static_api
from services.api.schemas import (
    AlertDetailResponse,
    AlertResponse,
    IncidentDetailResponse,
    IncidentResponse,
    RunMetricsResponse,
    RunResponse,
)

REPO = Path(__file__).resolve().parents[1]
STATIC_API_DIR = REPO / "services" / "web" / "public" / "static-api"


@pytest.fixture(scope="module")
def exported_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if (STATIC_API_DIR / "runs.json").exists():
        return STATIC_API_DIR
    out = tmp_path_factory.mktemp("static_api")
    export_static_api(out_dir=out, run_ids=DEFAULT_RUN_IDS, extra_details_per_run=50)
    return out


def _unpack_alerts(raw: dict[str, object]) -> list[AlertResponse]:
    cols = raw["columns"]
    rows = raw["rows"]
    assert isinstance(cols, list) and isinstance(rows, list)
    out: list[AlertResponse] = []
    for row in rows:
        item = dict(zip(cols, row, strict=True))
        item["rescue_components"] = None
        item["label"] = {
            "is_fault": item.pop("label_is_fault"),
            "fault_type": item.pop("label_fault_type"),
            "root_cause_service": item.pop("label_root_cause_service"),
        }
        out.append(AlertResponse.model_validate(item))
    return out


def test_runs_and_metrics_match_chapter6_counts(exported_dir: Path) -> None:
    runs = [
        RunResponse.model_validate(item)
        for item in json.loads((exported_dir / "runs.json").read_text(encoding="utf-8"))
    ]
    assert [r.run_id for r in runs] == list(DEFAULT_RUN_IDS)

    expected = {
        "pipeline_test_v2": (13699, 78, 38),
        "pipeline_val_v2": (5677, 80, 26),
        "pipeline_sens_test_v1": (13699, 438, 114),
    }
    for run_id, (n_alerts, n_true, n_inc) in expected.items():
        metrics = RunMetricsResponse.model_validate(
            json.loads((exported_dir / "metrics" / f"{run_id}.json").read_text(encoding="utf-8"))
        )
        assert metrics.run_id == run_id
        assert metrics.json_valid_rate == pytest.approx(1.0)

        alerts = _unpack_alerts(
            json.loads((exported_dir / "alerts" / f"{run_id}.json").read_text(encoding="utf-8"))
        )
        assert len(alerts) == n_alerts
        assert sum(1 for a in alerts if a.verdict == "TRUE_ALERT") == n_true

        incidents = [
            IncidentResponse.model_validate(item)
            for item in json.loads((exported_dir / "incidents" / f"{run_id}.json").read_text(encoding="utf-8"))
        ]
        assert len(incidents) == n_inc
        assert all(inc.grouping_reason.temporal_window_sec == 180.0 for inc in incidents)

        inc_details_raw = json.loads(
            (exported_dir / "incident_details" / f"{run_id}.json").read_text(encoding="utf-8")
        )
        assert len(inc_details_raw) == n_inc
        sample_inc = IncidentDetailResponse.model_validate(next(iter(inc_details_raw.values())))
        assert sample_inc.report is not None
        assert sample_inc.report.llm_backend == "gemini-2.5-flash"


def test_chapter6_demo_cases_have_full_details(exported_dir: Path) -> None:
    demo = json.loads(DEMO_CASES_PATH.read_text(encoding="utf-8"))

    test_details = json.loads(
        (exported_dir / "alert_details" / "pipeline_test_v2.json").read_text(encoding="utf-8")
    )
    step2_id = demo["steps"]["step2_c3_downgrade"]["primary"]["alert_id"]
    step3_id = demo["steps"]["step3_topo_rescue_network_delay"]["primary"]["alert_id"]

    d2 = AlertDetailResponse.model_validate(test_details[step2_id])
    assert d2.raw_verdict == "TRUE_ALERT"
    assert d2.verdict == "UNCERTAIN"
    assert d2.downgraded_by_anchoring is True
    assert d2.fusion_weights is not None
    assert len(d2.search_scope) >= 1

    d3 = AlertDetailResponse.model_validate(test_details[step3_id])
    assert d3.verdict == "TRUE_ALERT"
    assert d3.service == "cartservice"
    assert d3.fusion_weights is not None

    sens_inc_details = json.loads(
        (exported_dir / "incident_details" / "pipeline_sens_test_v1.json").read_text(encoding="utf-8")
    )
    step4_inc_id = demo["steps"]["step4_incident_cascade"]["primary"]["incident_id"]
    d4 = IncidentDetailResponse.model_validate(sens_inc_details[step4_inc_id])
    assert len(d4.services) >= 2
    assert d4.root_cause_service == "ts-basic-service"
    assert d4.report is not None and d4.report.llm_backend == "gemini-2.5-flash"
