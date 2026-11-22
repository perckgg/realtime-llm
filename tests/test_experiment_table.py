"""Regression tests for M10-C / M10-C.1 static experiment table generation."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.m10_experiment_table import OUT_EVAL, OUT_WEB, build_experiment_table


def test_experiment_table_matches_committed_json() -> None:
    """Generated web/eval JSON must match live builder output (excluding timestamp)."""
    built = build_experiment_table()
    assert OUT_EVAL.parent.name == "m10_experiment_table_v2"
    web_data = json.loads(Path(OUT_WEB).read_text(encoding="utf-8"))
    eval_data = json.loads(Path(OUT_EVAL).read_text(encoding="utf-8"))

    assert web_data == eval_data
    for section in ("verdicts", "methods", "ablation", "budget_curve", "rca", "sources"):
        assert web_data[section] == built[section]


def test_experiment_table_real_metrics_and_h5_honesty() -> None:
    """Check key H0-H5 and RCA numbers come verbatim from eval/results/."""
    data = json.loads(Path(OUT_WEB).read_text(encoding="utf-8"))

    verdicts = {h["id"]: h for h in data["verdicts"]}
    assert set(verdicts) == {"H0", "H1", "H2", "H3", "H4", "H5"}
    assert verdicts["H0"]["status"] == "accepted"
    assert verdicts["H1"]["status"] == "partial"
    assert "Giữ một phần" in verdicts["H1"]["status_label"]
    assert verdicts["H2"]["status"] == "rejected"
    assert verdicts["H5"]["status"] == "rejected"
    assert verdicts["H5"]["status_label"] == "Không được chấp nhận (0 / 4 vế)"
    assert "đạt nhánh B" not in verdicts["H5"]["status_label"]
    assert "JSON hợp lệ 38 / 38" in verdicts["H5"]["note"]
    assert len(verdicts["H5"]["clauses"]) == 4
    assert [c["clause"] for c in verdicts["H5"]["clauses"]] == [
        "Hit@1 ≥ 0,60",
        "Hit@3 ≥ 0,80",
        "Cận dưới CI95 của ΔHit@1 (RCA − baseline) > 0",
        "Alert Reduction ≥ 30% trên sự cố cascade",
    ]
    assert all(c["met"] is False for c in verdicts["H5"]["clauses"])

    dot_decimal = re.compile(r"\d\.\d")
    for h in data["verdicts"]:
        assert not dot_decimal.search(h["summary"]), f"Decimal dot in {h['id']} summary: {h['summary']}"
        assert not dot_decimal.search(h.get("note") or ""), f"Decimal dot in {h['id']} note"
        for c in h["clauses"]:
            assert not dot_decimal.search(c["detail"]), (
                f"Decimal dot in {h['id']} clause detail: {c['detail']}"
            )

    test_methods = {m["key"]: m for m in data["methods"]["test"]["methods"]}
    assert test_methods["ctav"]["tp"] == 14
    assert test_methods["ctav"]["fp"] == 64
    assert abs(test_methods["ctav"]["f1"] - 14 * 2 / (2 * 14 + 64 + 332)) < 1e-9

    rca_by_id = {r["run_id"]: r for r in data["rca"]}
    assert rca_by_id["rca_final_test_v1"]["hit1_count"] == 8
    assert rca_by_id["rca_final_test_v1"]["labelled"] == 17
    assert rca_by_id["rca_final_test_v1"]["multi_service"] == 0
    assert rca_by_id["rca_final_test_v1"]["summary_valid"] == 38
    assert rca_by_id["rca_sens_test_c3rolling_v1"]["multi_service"] == 39
    assert rca_by_id["rca_final_val_v1"]["cascade_injections"] == 1
