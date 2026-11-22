"""Tests for M10-D deterministic demo cases, offline replay isolation, and V48 (b')+(a')."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from eval.harness import rca
from scripts.m10_pick_demo_cases import DEFAULT_OUTPUT, pick_demo_cases
from services.rca_agent.pipeline import run_pipeline


def test_pick_demo_cases_deterministic_and_invariants() -> None:
    first = pick_demo_cases(seed=42)
    second = pick_demo_cases(seed=42)
    assert first["steps"] == second["steps"]

    saved = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert saved["steps"] == first["steps"]

    step2 = saved["steps"]["step2_c3_downgrade"]
    assert step2["pool_size"] == 1171
    p2 = step2["primary"]
    assert p2["run_id"] == "pipeline_test_v2"
    assert p2["raw_verdict"] == "TRUE_ALERT"
    assert p2["verdict"] == "UNCERTAIN"
    assert p2["downgraded_by_anchoring"] is True
    assert p2["evidence_event_count"] > 0

    step3 = saved["steps"]["step3_topo_rescue_network_delay"]
    assert step3["pool_size"] == 2
    p3 = step3["primary"]
    assert p3["run_id"] == "pipeline_test_v2"
    assert p3["label_fault_type"] == "network_delay"
    assert p3["bm25_verdict"] != "TRUE_ALERT"
    assert p3["ctav_verdict"] == "TRUE_ALERT"

    step4 = saved["steps"]["step4_incident_cascade"]
    assert step4["out_of_registration_sensitivity"] is True
    assert step4["pool_size"] == 3
    p4 = step4["primary"]
    assert p4["run_id"] == "pipeline_sens_test_v1"
    assert len(p4["services"]) >= 2
    assert p4["level1_hit1"] is True

    lim = step4["registered_val_limitation"]
    assert lim is not None
    assert lim["run_id"] == "pipeline_val_v2"
    assert lim["injection_id"] == "2023-01-30#009"
    assert len(lim["split_incidents"]) == 2


def test_pipeline_offline_mode_strips_api_keys_and_uses_cache_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_OFFLINE", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-must-be-cleared")
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key-must-be-cleared")

    out_dir = run_pipeline(
        Path("eval/configs/rca_final.yaml"),
        run_id="pytest_offline_val",
        write_db=False,
        results_root=Path("eval/results"),
        output_root=tmp_path,
        cache_path=rca.LLM_CACHE,
    )
    assert "GEMINI_API_KEY" not in os.environ
    assert "GOOGLE_API_KEY" not in os.environ

    runtime = json.loads((out_dir / "runtime.json").read_text(encoding="utf-8"))
    assert runtime["offline_mode"] is True
    assert runtime["llm_operations"]["api_calls"] == 0
    assert runtime["llm_operations"]["new_api_calls"] == 0
    assert runtime["llm_operations"]["cache_hit_rate"] == 1.0
    assert runtime["parity"]["all_matched"] is True


def test_frontend_bundle_has_no_external_cdn_links() -> None:
    html = Path("services/web/index.html").read_text(encoding="utf-8")
    css = Path("services/web/src/index.css").read_text(encoding="utf-8")
    assert not re.search(r"https?://", html), "index.html must not depend on external URLs"
    assert not re.search(r"https?://", css), "index.css must not import external fonts or styles"


def test_sens_pipeline_db_and_demo_case_records_when_docker_running() -> None:
    psycopg = pytest.importorskip("psycopg")
    from packages.storage import clickhouse
    from services.rca_agent import store

    try:
        ch = clickhouse.get_client()
    except Exception:
        pytest.skip("ClickHouse is not reachable")
    try:
        conn = store.connect(timeout_seconds=2)
    except psycopg.OperationalError:
        ch.close()
        pytest.skip("PostgreSQL is not reachable")

    saved = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    p2 = saved["steps"]["step2_c3_downgrade"]["primary"]
    p3 = saved["steps"]["step3_topo_rescue_network_delay"]["primary"]
    p4 = saved["steps"]["step4_incident_cascade"]["primary"]

    try:
        ev_rows = ch.query(
            "SELECT count(), countIf(verdict = 'TRUE_ALERT') "
            "FROM fact_alert_evaluation WHERE run_id = {r:String}",
            parameters={"r": "pipeline_sens_test_v1"},
        ).result_rows[0]
        assert (int(ev_rows[0]), int(ev_rows[1])) == (13699, 438)

        tr_count = int(
            ch.query(
                "SELECT count() FROM fact_retrieval_trace WHERE run_id = {r:String}",
                parameters={"r": "pipeline_sens_test_v1"},
            ).result_rows[0][0]
        )
        assert tr_count == 19794

        assert store.counts(conn, "pipeline_sens_test_v1") == {
            "incidents": 114,
            "diagnostic_reports": 114,
            "diagnostic_rejected": 0,
        }

        for wid in (p2["window_id"], p3["window_id"]):
            hit = int(
                ch.query(
                    "SELECT count() FROM fact_alert_evaluation "
                    "WHERE run_id = {r:String} AND window_id = {w:String}",
                    parameters={"r": "pipeline_test_v2", "w": wid},
                ).result_rows[0][0]
            )
            assert hit == 1

        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM incidents WHERE run_id = %s AND incident_id = %s",
                ("pipeline_sens_test_v1", p4["incident_id"]),
            )
            row = cur.fetchone()
            assert row is not None and int(row[0]) == 1
    finally:
        ch.close()
        conn.close()
