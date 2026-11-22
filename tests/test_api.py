"""Contract and integration tests for services/api (M10-B, QD-046)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from packages.storage import clickhouse
from services.api import readers
from services.api.main import app

TYPES_TS = Path(__file__).resolve().parents[1] / "services" / "web" / "src" / "api" / "types.ts"


def _parse_ts_interfaces(path: Path) -> dict[str, set[str]]:
    """Extract interface fields (resolving `extends`) directly from services/web/src/api/types.ts."""
    text = path.read_text(encoding="utf-8")
    raw: dict[str, set[str]] = {}
    parents: dict[str, str | None] = {}

    header_re = re.compile(
        r"export\s+interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{",
        re.MULTILINE,
    )
    for match in header_re.finditer(text):
        name = match.group(1)
        parent = match.group(2)
        parents[name] = parent
        pos = match.end()
        depth = 1
        while pos < len(text) and depth > 0:
            ch = text[pos]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            pos += 1
        body = text[match.end() : pos - 1]
        # Top-level fields (indent 2 spaces, excluding nested `{ ... }` blocks and comments).
        fields: set[str] = set()
        inner_depth = 0
        for line in body.splitlines():
            stripped = line.strip()
            if inner_depth == 0:
                m_field = re.match(r"^([a-zA-Z_]\w*)\??\s*:", stripped)
                if m_field:
                    fields.add(m_field.group(1))
            inner_depth += line.count("{") - line.count("}")
        raw[name] = fields

    resolved: dict[str, set[str]] = {}
    for name in raw:
        keys = set(raw[name])
        cur = parents.get(name)
        while cur:
            keys |= raw.get(cur, set())
            cur = parents.get(cur)
        resolved[name] = keys
    return resolved


def _require_dbs() -> None:
    try:
        ch = clickhouse.get_client()
        ch.query("SELECT 1")
        ch.close()
    except Exception:
        pytest.skip("ClickHouse is not reachable")
    try:
        conn = readers.pg_connect(timeout_seconds=2)
        conn.close()
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not reachable")


def test_ts_interface_parser_has_policy_fields() -> None:
    ifaces = _parse_ts_interfaces(TYPES_TS)
    assert {
        "raw_verdict",
        "routing_tier",
        "evidence_origin",
        "threshold_applied",
        "downgraded_by_gating",
        "downgraded_by_anchoring",
    } <= ifaces["Alert"]
    assert ifaces["Alert"] <= ifaces["AlertDetail"]
    assert ifaces["Incident"] <= ifaces["IncidentDetail"]


def test_api_endpoints_real_data_and_contract() -> None:
    _require_dbs()
    ifaces = _parse_ts_interfaces(TYPES_TS)
    client = TestClient(app)

    # 1. /health (and /api/health alias)
    for path in ("/health", "/api/health"):
        res = client.get(path)
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    # 2. /runs (F6: includes alert_count distinguishing pipeline_* from rca_*)
    runs_res = client.get("/runs")
    assert runs_res.status_code == 200
    runs = runs_res.json()
    by_run_id = {r["run_id"]: r for r in runs}
    assert {
        "pipeline_val_v1",
        "pipeline_test_v1",
        "pipeline_val_v2",
        "pipeline_test_v2",
        "rca_final_test_v1",
    } <= set(by_run_id)
    assert set(runs[0].keys()) >= ifaces["Run"]
    assert by_run_id["pipeline_test_v1"]["alert_count"] == 13699
    assert by_run_id["pipeline_test_v2"]["alert_count"] == 13699
    assert by_run_id["rca_final_test_v1"]["alert_count"] == 0

    # F5 + F4: requesting same alert_id across _v1 vs _v2 returns exact run_id & authentic cache_hit.
    import json as _json

    judged_path = (
        Path(__file__).resolve().parents[1]
        / "eval"
        / "results"
        / "ctav_final_test_v1"
        / "judged.jsonl"
    )
    false_wid: str | None = None
    true_wid: str | None = None
    with judged_path.open(encoding="utf-8") as handle:
        for line in handle:
            rec = _json.loads(line)
            if false_wid is None and rec.get("cache_hit") is False:
                false_wid = str(rec["window_id"])
            elif true_wid is None and rec.get("cache_hit") is True:
                true_wid = str(rec["window_id"])
            if false_wid and true_wid:
                break
    assert false_wid is not None and true_wid is not None
    false_id = f"cand-{false_wid}:hybrid_bm25_graph:r0"
    true_id = f"cand-{true_wid}:hybrid_bm25_graph:r0"

    res_v1 = client.get(f"/alerts/{false_id}?run_id=pipeline_test_v1")
    res_v2 = client.get(f"/alerts/{false_id}?run_id=pipeline_test_v2")
    assert res_v1.status_code == 200 and res_v2.status_code == 200
    assert res_v1.json()["run_id"] == "pipeline_test_v1"
    assert res_v1.json()["cache_hit"] is True
    assert res_v2.json()["run_id"] == "pipeline_test_v2"
    assert res_v2.json()["cache_hit"] is False

    res_v2_true = client.get(f"/alerts/{true_id}?run_id=pipeline_test_v2")
    assert res_v2_true.status_code == 200
    assert res_v2_true.json()["run_id"] == "pipeline_test_v2"
    assert res_v2_true.json()["cache_hit"] is True

    # 3. /runs/{run_id}/metrics & 4. /alerts & 5. /alerts/{alert_id} & 6-7. /incidents
    for run_id, n_windows, tp, fp, n_alerts, n_true, n_inc in [
        ("pipeline_val_v2", 7636, 29, 51, 5677, 80, 26),
        ("pipeline_test_v2", 11985, 14, 64, 13699, 78, 38),
    ]:
        m_res = client.get(f"/runs/{run_id}/metrics")
        assert m_res.status_code == 200
        m = m_res.json()
        assert set(m.keys()) >= ifaces["RunMetrics"]
        assert set(m["precision"].keys()) >= ifaces["MetricWithCI"]
        assert (m["n_windows"], m["tp"], m["fp"]) == (n_windows, tp, fp)
        assert m["json_valid_rate"] == pytest.approx(1.0)
        assert m["cache_hit_rate"] == pytest.approx(1.0)

        a_res = client.get(f"/alerts?run_id={run_id}")
        assert a_res.status_code == 200
        alerts = a_res.json()
        assert len(alerts) == n_alerts
        assert set(alerts[0].keys()) >= ifaces["Alert"]
        assert set(alerts[0]["label"].keys()) >= ifaces["WindowLabel"]

        true_res = client.get(f"/alerts?run_id={run_id}&verdict=TRUE_ALERT")
        assert true_res.status_code == 200
        true_alerts = true_res.json()
        assert len(true_alerts) == n_true

        paged_res = client.get(f"/alerts?run_id={run_id}&limit=5&offset=2")
        assert paged_res.status_code == 200
        assert paged_res.json() == alerts[2:7]

        # Inspect one TRUE_ALERT detail and one C3-downgraded UNCERTAIN detail.
        sample_true = true_alerts[0]
        d_res = client.get(f"/alerts/{sample_true['alert_id']}?run_id={run_id}")
        assert d_res.status_code == 200
        detail = d_res.json()
        assert set(detail.keys()) >= ifaces["AlertDetail"]
        assert detail["detector_threshold"] == pytest.approx(0.85)
        assert len(detail["metric_series"]) >= 1
        assert len(detail["context_events"]) >= 1
        assert set(detail["context_events"][0].keys()) >= ifaces["ContextEvent"]
        assert detail["context_events"][0]["content"] != ""
        assert "origin" in detail["context_events"][0]["debug"]

        # C1 search scope + Fusion Score breakdown used by the "How C1 built this context" card.
        scope = detail["search_scope"]
        assert scope[0] == {"service": detail["service"], "distance": 0}
        assert all(0 <= s["distance"] <= 2 for s in scope)
        weights = detail["fusion_weights"]
        assert weights is not None
        for ev in detail["context_events"]:
            dbg = ev["debug"]
            recomposed = (
                weights["alpha"] * dbg["bm25_norm"]
                + weights["beta"] * dbg["time_sim"]
                + weights["gamma"] * dbg["graph_sim"]
            )
            assert recomposed == pytest.approx(dbg["score_final"], abs=1e-6)
            assert dbg["graph_sim"] == pytest.approx(1 / (1 + dbg["graph_distance"]))

        anchored = next((a for a in alerts if a["downgraded_by_anchoring"]), None)
        assert anchored is not None
        anc_res = client.get(f"/alerts/{anchored['alert_id']}?run_id={run_id}")
        assert anc_res.status_code == 200
        assert anc_res.json()["raw_verdict"] == "TRUE_ALERT"
        assert anc_res.json()["verdict"] == "UNCERTAIN"
        assert anc_res.json()["downgraded_by_anchoring"] is True

        inc_res = client.get(f"/incidents?run_id={run_id}")
        assert inc_res.status_code == 200
        incidents = inc_res.json()
        assert len(incidents) == n_inc
        assert set(incidents[0].keys()) >= ifaces["Incident"]
        assert isinstance(incidents[0]["grouping_reason"]["graph_edges_used"], int)

        id_res = client.get(f"/incidents/{incidents[0]['incident_id']}")
        assert id_res.status_code == 200
        inc_detail = id_res.json()
        assert set(inc_detail.keys()) >= ifaces["IncidentDetail"]
        assert len(inc_detail["nodes"]) >= 1
        assert set(inc_detail["nodes"][0].keys()) >= ifaces["GraphNode"]
        if inc_detail["edges"]:
            assert set(inc_detail["edges"][0].keys()) >= ifaces["GraphEdge"]
        assert inc_detail["report"] is not None
        assert set(inc_detail["report"].keys()) >= ifaces["DiagnosticReport"]
        assert set(inc_detail["report"]["evidence"][0].keys()) >= ifaces["EvidenceItem"]
        assert set(inc_detail["report"]["suggested_actions"][0].keys()) >= ifaces["SuggestedAction"]
        assert len(inc_detail["alerts"]) == len(incidents[0]["alert_ids"])


def test_api_404_and_empty_run() -> None:
    _require_dbs()
    client = TestClient(app)

    # 404 cases for every parameterized endpoint
    assert client.get("/runs/missing_run_404/metrics").status_code == 404
    assert client.get("/alerts?run_id=missing_run_404").status_code == 404
    assert client.get("/alerts/cand-missing_window_404:hybrid_bm25_graph:r0").status_code == 404
    assert client.get("/incidents?run_id=missing_run_404").status_code == 404
    assert client.get("/incidents/inc-missing_404").status_code == 404

    # Empty run present in run_registry with 0 alerts and 0 incidents -> 200 []
    empty_run_id = f"pytest-empty-{uuid.uuid4().hex[:12]}"
    with readers.pg_connect() as conn:
        conn.execute(
            "INSERT INTO run_registry (run_id, config_yaml, git_commit, split, seed, started_at, status, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'done', %s)",
            (empty_run_id, "kind: rca\n", "test", "val", 42, datetime.now(UTC), "pytest empty run"),
        )
        conn.commit()
    try:
        alerts_res = client.get(f"/alerts?run_id={empty_run_id}")
        assert alerts_res.status_code == 200
        assert alerts_res.json() == []

        inc_res = client.get(f"/incidents?run_id={empty_run_id}")
        assert inc_res.status_code == 200
        assert inc_res.json() == []
    finally:
        with readers.pg_connect() as conn:
            conn.execute("DELETE FROM run_registry WHERE run_id = %s", (empty_run_id,))
            conn.commit()


def test_c1_fusion_weights_match_frozen_configs() -> None:
    """The alert-detail breakdown must use the weights the registered C1 runs actually used."""
    import yaml

    from services.api.readers import C1_FUSION_WEIGHTS

    for name in ("h0_val_c1_k0.yaml", "h0_test_c1_k0.yaml"):
        params = yaml.safe_load((Path(__file__).resolve().parents[1] / "eval" / "configs" / name).read_text(encoding="utf-8"))["retrieval"]["params"]
        assert params["alpha"] == C1_FUSION_WEIGHTS.alpha
        assert params["beta"] == C1_FUSION_WEIGHTS.beta
        assert params["gamma"] == C1_FUSION_WEIGHTS.gamma
        assert params["tau_seconds"] == C1_FUSION_WEIGHTS.tau_seconds
        assert params["graph_max_distance"] == C1_FUSION_WEIGHTS.graph_max_distance
