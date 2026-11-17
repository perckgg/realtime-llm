"""Tests for services/rca_agent/pipeline.py (M10-A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.harness import rca
from packages.graph.service_graph import load_graph
from services.judge.cache import ResponseCache
from services.rca_agent.pipeline import (
    EXPECTED_METHOD_FINGERPRINT,
    CacheOnlyGeminiSummaryBackend,
    _evaluate_stages,
    _summarize_from_cache,
    check_parity,
    load_alerts,
    run_pipeline,
)


def test_cache_only_backend_raises_on_miss_and_never_calls_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = ResponseCache(tmp_path / "cache.jsonl")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-must-never-be-used")
    backend = CacheOnlyGeminiSummaryBackend(cache, "gemini-2.5-flash", 1024)

    cached_prompt = '{"hello": "cached"}'
    cache.put(
        backend.cache_key(cached_prompt),
        {"raw": '{"ok": true}', "usage": {"promptTokenCount": 5}, "model_version": "gemini-2.5-flash"},
    )
    hit = backend.complete(cached_prompt)
    assert hit.cache_hit is True
    assert hit.actual_api_call is False
    assert hit.raw == '{"ok": true}'

    with pytest.raises(RuntimeError, match="Cache miss"):
        backend.complete('{"hello": "missing"}')


def test_parity_check_detects_mismatch(tmp_path: Path) -> None:
    results_root = Path("eval/results")
    config = rca.load_rca_config(Path("eval/configs/rca_final.yaml"))
    loaded = load_alerts(
        str(config["input"]["alerts_run"]),
        str(config["input"]["evidence_run"]),
        "parity_test_run",
        results_root=results_root,
    )
    graph = load_graph()
    _, located, _, _ = _evaluate_stages(config, loaded.inputs, graph, "parity_test_run")
    _, summaries = _summarize_from_cache(
        config=config,
        located=located,
        inputs=loaded.inputs,
        evidence_by_window=loaded.evidence_by_window,
        graph=graph,
        run_id="parity_test_run",
        reference_run_id="rca_final_val_v1",
        cache_path=rca.LLM_CACHE,
    )

    ref_dir = results_root / "rca_final_val_v1"
    parity = check_parity(located, summaries, ref_dir)
    assert parity["all_matched"] is True
    assert parity["incidents_matched"] == 26

    # Copy reference files into tmp_path and mutate each parity axis one at a time.
    inc_lines = [
        json.loads(line)
        for line in (ref_dir / "incidents.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    rep_lines = [
        json.loads(line)
        for line in (ref_dir / "reports.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]

    def write_ref(incidents_data: list[dict], reports_data: list[dict]) -> Path:
        d = tmp_path / "ref"
        d.mkdir(exist_ok=True)
        (d / "incidents.jsonl").write_text(
            "\n".join(json.dumps(x) for x in incidents_data) + "\n", encoding="utf-8"
        )
        (d / "reports.jsonl").write_text(
            "\n".join(json.dumps(x) for x in reports_data) + "\n", encoding="utf-8"
        )
        return d

    bad_alerts = [dict(x) for x in inc_lines]
    bad_alerts[0] = {**bad_alerts[0], "alert_ids": [*bad_alerts[0]["alert_ids"], "extra-alert"]}
    with pytest.raises(ValueError, match="alert_ids"):
        check_parity(located, summaries, write_ref(bad_alerts, rep_lines))

    bad_rank = [dict(x) for x in inc_lines]
    bad_rank[0] = {**bad_rank[0], "level1": [{**bad_rank[0]["level1"][0], "service": "wrong-svc"}]}
    with pytest.raises(ValueError, match="level1 ranking"):
        check_parity(located, summaries, write_ref(bad_rank, rep_lines))

    bad_report = [dict(x) for x in rep_lines]
    bad_report[0] = {
        **bad_report[0],
        "report": {**bad_report[0]["report"], "fault_type": "different_fault"},
    }
    with pytest.raises(ValueError, match="JSON hash"):
        check_parity(located, summaries, write_ref(inc_lines, bad_report))


def test_pipeline_val_parity_and_runtime_no_db(tmp_path: Path) -> None:
    out_dir = run_pipeline(
        Path("eval/configs/rca_final.yaml"),
        run_id="pytest_pipeline_val",
        write_db=False,
        results_root=Path("eval/results"),
        output_root=tmp_path,
        cache_path=rca.LLM_CACHE,
    )
    runtime = json.loads((out_dir / "runtime.json").read_text(encoding="utf-8"))
    assert runtime["method_fingerprint"] == EXPECTED_METHOD_FINGERPRINT
    assert runtime["llm_operations"]["api_calls"] == 0
    assert runtime["llm_operations"]["cache_hit_rate"] == 1.0
    assert runtime["counts"]["candidates_loaded"] == 5677
    assert runtime["counts"]["confirmed_alerts"] == 80
    assert runtime["counts"]["retrieval_trace_rows"] == 7716
    assert runtime["counts"]["incidents"] == 26
    assert runtime["parity"]["all_matched"] is True
    assert runtime["parity"]["incidents_matched"] == 26
    for key in (
        "load_alerts_ms",
        "grouping_ms",
        "propagation_ms",
        "summarizer_ms",
        "e2e_wall_ms",
    ):
        assert runtime["stages_ms"][key] >= 0.0


def test_pipeline_db_records_when_docker_running() -> None:
    """Verify real DB rows for pipeline_val_v1 and pipeline_test_v1 when ClickHouse & Postgres are reachable."""
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

    try:
        for run_id, expected_eval, expected_trace, expected_inc in [
            ("pipeline_val_v1", 5677, 7716, 26),
            ("pipeline_test_v1", 13699, 19794, 38),
        ]:
            ev_count = int(
                ch.query(
                    "SELECT count() FROM fact_alert_evaluation WHERE run_id = {r:String}",
                    parameters={"r": run_id},
                ).result_rows[0][0]
            )
            tr_count = int(
                ch.query(
                    "SELECT count() FROM fact_retrieval_trace WHERE run_id = {r:String}",
                    parameters={"r": run_id},
                ).result_rows[0][0]
            )
            assert ev_count == expected_eval
            assert tr_count == expected_trace
            assert store.counts(conn, run_id) == {
                "incidents": expected_inc,
                "diagnostic_reports": expected_inc,
                "diagnostic_rejected": 0,
            }
    finally:
        ch.close()
        conn.close()
