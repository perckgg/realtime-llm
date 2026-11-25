"""Tests for M11 scripts: blind sampling, descriptive test error analysis, and scoring."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.m11_error_analysis import RESULTS, analyze_test_errors
from scripts.m11_sample_incidents import (
    BLIND_FIELDS,
    KEY_FIELDS,
    classify_graph_relation,
    draw_incidents,
    load_jsonl,
)
from scripts.m11_score_diagnostic_quality import (
    cohens_kappa,
    load_graded_rows,
    score_diagnostic_quality,
)

REPO = Path(__file__).resolve().parents[1]


def test_sample_incidents_deterministic_prefix_and_blinding() -> None:
    incidents = load_jsonl(RESULTS / "rca_final_test_v1" / "incidents.jsonl")
    assert len(incidents) == 38

    s30_a = draw_incidents(incidents, n=30, seed=42)
    s30_b = draw_incidents(incidents, n=30, seed=42)
    s15 = draw_incidents(incidents, n=15, seed=42)
    ids30 = [str(r["incident_id"]) for r in s30_a]
    assert ids30 == [str(r["incident_id"]) for r in s30_b]
    assert len(set(ids30)) == 30
    # First 15 rows of the seeded uniform permutation match an independent SRS of size 15
    assert ids30[:15] == [str(r["incident_id"]) for r in s15]

    blind_path = REPO / "eval" / "manual" / "diagnostic_quality.csv"
    key_path = REPO / "eval" / "manual" / "diagnostic_quality.key.csv"
    with blind_path.open(encoding="utf-8-sig", newline="") as handle:
        blind_rows = list(csv.DictReader(handle))
    with key_path.open(encoding="utf-8-sig", newline="") as handle:
        key_rows = list(csv.DictReader(handle))

    assert len(blind_rows) == 30
    assert len(key_rows) == 30
    assert list(blind_rows[0]) == BLIND_FIELDS
    assert list(key_rows[0]) == KEY_FIELDS

    # Strict blinding: no ground-truth or invalid-evidence fields leaked into blind sheet
    forbidden_cols = {
        "status",
        "true_root_cause",
        "true_fault_type",
        "injection_ids",
        "level1_hit1",
        "level1_hit3",
        "graph_relation",
        "objective_rc_score",
        "invalid_evidence_ids",
        "invalid_evidence_ids_count",
    }
    assert not (set(BLIND_FIELDS) & forbidden_cols)

    for idx, (brow, krow) in enumerate(zip(blind_rows, key_rows, strict=True), start=1):
        assert int(brow["sample_no"]) == idx
        assert int(krow["sample_no"]) == idx
        assert brow["incident_id"] == krow["incident_id"]
        assert brow["incident_id"] == ids30[idx - 1]


def test_sample_incidents_refuses_overwrite(tmp_path: Path) -> None:
    prefix = tmp_path / "dq"
    prefix.with_name("dq.csv").write_text("existing\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "m11_sample_incidents.py"),
            "--out",
            str(prefix),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "already exists" in proc.stderr


def test_classify_graph_relation() -> None:
    adj = {"frontend": {"checkoutservice"}, "checkoutservice": {"paymentservice"}}
    assert classify_graph_relation("frontend", None, adj) == ("NO_GROUND_TRUTH", "")
    assert classify_graph_relation("frontend", "frontend", adj) == ("EXACT", "2")
    assert classify_graph_relation("frontend", "checkoutservice", adj) == ("1hop_callee", "1")
    assert classify_graph_relation("checkoutservice", "frontend", adj) == ("1hop_caller", "1")
    assert classify_graph_relation("frontend", "paymentservice", adj) == ("FAR_OR_DISCONNECTED", "0")


def test_error_analysis_matches_saved_and_m8_m9_invariants() -> None:
    saved_path = RESULTS / "m11_error_analysis_test_v1" / "error_analysis.json"
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    fresh = analyze_test_errors()

    for section in ("counts", "ctav_fp", "ctav_fn", "rca_registered", "rca_sensitivity_out_of_registration"):
        assert saved[section] == fresh[section]

    counts = fresh["counts"]
    assert counts["telemetry_windows"] == 11985
    assert counts["ctav_tp"] == 14
    assert counts["ctav_fp"] == 64
    assert counts["ctav_fn"] == 332
    assert counts["ctav_tp"] + counts["ctav_fn"] == counts["fault_windows"] == 346

    fp = fresh["ctav_fp"]
    assert fp["by_service"] == {"frontend": 39, "ts-travel-service": 25}
    overlap = fp["by_fault_overlap"]
    assert overlap["collateral_during_active_fault"]["count"] == 31
    assert overlap["pure_normal_traffic"]["count"] == 33
    assert 31 + 33 == 64

    fn = fresh["ctav_fn"]
    assert fn["detector_missed_detail"]["total"] == 122
    assert fn["judge_false_positive_detail"]["total"] == 128
    assert fn["c3_anchoring_detail"]["total"] == 82
    assert 122 + 128 + 82 == 332
    c3_subs = fn["c3_anchoring_detail"]["by_subreason"]
    assert c3_subs["c3_service_missing_dev_baseline"] == 67
    assert c3_subs["c3_op_missing_dev_baseline"] == 3
    assert c3_subs["c3_span_below_dev_p90"] == 12
    assert 67 + 3 + 12 == 82

    reg = fresh["rca_registered"]
    assert reg["by_status"] == {"ambiguous": 3, "labelled": 17, "no_fault": 18}
    assert reg["labelled_hit1"] == 8 and reg["labelled_miss1"] == 9
    assert reg["miss_categories"] == {"unalerted_1hop_callee": 7, "unalerted_multihop_or_disconnected": 2}
    assert reg["injections_coverage"]["without_alert"] == 29

    sens = fresh["rca_sensitivity_out_of_registration"]
    assert sens["by_status"] == {"ambiguous": 14, "labelled": 48, "no_fault": 52}
    assert sens["labelled_hit1"] == 10 and sens["labelled_miss1"] == 38
    assert (
        sum(v for k, v in sens["miss_categories"].items() if k.startswith("unalerted_")) == 33
    )
    assert (
        sum(v for k, v in sens["miss_categories"].items() if k.startswith("rc_alerted_")) == 5
    )


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_score_diagnostic_quality_and_kappa(tmp_path: Path) -> None:
    key_path = REPO / "eval" / "manual" / "diagnostic_quality.key.csv"
    blind_path = REPO / "eval" / "manual" / "diagnostic_quality.csv"
    with blind_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    # Reset any already-graded rows in the working copy, then grade first 15 rows synthetically
    for r in rows:
        r["root_cause_score"] = ""
        r["evidence_score"] = ""
        r["action_score"] = ""
    for idx in range(15):
        rows[idx]["root_cause_score"] = "2" if idx % 3 == 0 else "1"
        rows[idx]["evidence_score"] = "2" if idx % 2 == 0 else "1"
        rows[idx]["action_score"] = "1"
    graded_path = tmp_path / "graded_15.csv"
    _write_csv(graded_path, BLIND_FIELDS, rows)  # type: ignore[arg-type]

    # Second rater on first 6 rows (20% of 30)
    sec_rows = [dict(r) for r in rows]
    for r in sec_rows:
        r["root_cause_score"] = ""
        r["evidence_score"] = ""
        r["action_score"] = ""
    for idx in range(6):
        sec_rows[idx]["root_cause_score"] = rows[idx]["root_cause_score"]
        sec_rows[idx]["evidence_score"] = rows[idx]["evidence_score"]
        sec_rows[idx]["action_score"] = "2" if idx == 0 else "1"
    sec_path = tmp_path / "second_6.csv"
    _write_csv(sec_path, BLIND_FIELDS, sec_rows)  # type: ignore[arg-type]

    summary = score_diagnostic_quality(graded_path, key_path, second_rater_path=sec_path, n_boot=200, seed=42)
    assert summary["n_graded"] == 15
    assert summary["is_valid_prefix"] is True
    rc = summary["overall"]["root_cause_score"]
    assert rc["n"] == 15
    # 5 scores of 2 (idx 0,3,6,9,12), 10 scores of 1 -> mean 20/15 = 4/3
    assert rc["mean"] == pytest.approx(4 / 3)
    assert rc["ci95"][0] <= rc["mean"] <= rc["ci95"][1]
    assert summary["inter_rater_agreement"]["overlap_incidents"] == 6
    assert summary["inter_rater_agreement"]["by_criterion"]["root_cause_score"]["exact_agreement"] == 1.0

    # Non-prefix grading detection
    gap_rows = [dict(r) for r in rows]
    gap_rows[0]["root_cause_score"] = ""
    gap_rows[0]["evidence_score"] = ""
    gap_rows[0]["action_score"] = ""
    gap_path = tmp_path / "gap.csv"
    _write_csv(gap_path, BLIND_FIELDS, gap_rows)  # type: ignore[arg-type]
    _, _, is_prefix = load_graded_rows(gap_path, key_path)
    assert is_prefix is False

    # Reject invalid score or partial row
    bad_score = [dict(r) for r in rows]
    bad_score[0]["root_cause_score"] = "3"
    bad_path = tmp_path / "bad_score.csv"
    _write_csv(bad_path, BLIND_FIELDS, bad_score)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="invalid score"):
        load_graded_rows(bad_path, key_path)

    partial = [dict(r) for r in rows]
    partial[20]["root_cause_score"] = "1"
    partial_path = tmp_path / "partial.csv"
    _write_csv(partial_path, BLIND_FIELDS, partial)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Partially graded"):
        load_graded_rows(partial_path, key_path)

    # Kappa edge cases
    assert cohens_kappa([0, 1, 2, 0, 1, 2], [0, 1, 2, 0, 1, 2]) == pytest.approx(1.0)
    assert cohens_kappa([0, 1, 2], [0, 1, 2], weighted=True) == pytest.approx(1.0)
    assert cohens_kappa([2, 2, 2], [2, 2, 2]) is None
    w_near = cohens_kappa([0, 1, 2, 1], [0, 2, 2, 1], weighted=True)
    w_far = cohens_kappa([0, 1, 2, 1], [2, 1, 2, 1], weighted=True)
    assert w_near is not None and w_far is not None and w_near > w_far
