from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from eval.harness.compare import Method, compare, paired_delta_ci, parse_methods

FIELDS = ["window_id", "label_is_fault", "has_telemetry", "is_candidate", "decision"]


def _run(root: Path, run_id: str, rows: list[tuple[str, int, int, int, str]]) -> None:
    (root / run_id).mkdir(parents=True)
    with (root / run_id / "per_window.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)


def test_paired_delta_ci_is_zero_for_identical_and_signed_for_dominating() -> None:
    label = np.array([True] * 20 + [False] * 80)
    a = np.array([True] * 5 + [False] * 15 + [False] * 80)
    zero = paired_delta_ci(label, a, a.copy(), n_boot=200, seed=1)
    assert all(lo == hi == 0.0 for lo, hi in zero.values())

    b = np.array([True] * 15 + [False] * 5 + [True] * 30 + [False] * 50)  # more TP and more FP than a
    ci = paired_delta_ci(label, a, b, n_boot=500, seed=1)
    assert ci["recall"][0] > 0 and ci["fpr"][0] > 0


def test_compare_pairs_methods_per_subset(tmp_path: Path) -> None:
    #           id   fault tel cand  decision
    base = [("w1", 1, 1, 1, "alert"), ("w2", 1, 1, 1, "suppress"), ("w3", 0, 1, 1, "suppress"),
            ("w4", 0, 1, 1, "suppress"), ("w5", 0, 0, 1, "suppress"), ("w6", 1, 0, 0, "none")]
    topo = [("w1", 1, 1, 1, "alert"), ("w2", 1, 1, 1, "alert"), ("w3", 0, 1, 1, "alert"),
            ("w4", 0, 1, 1, "alert"), ("w5", 0, 0, 1, "alert"), ("w6", 1, 0, 0, "none")]
    _run(tmp_path, "bm25_v1", base)
    _run(tmp_path, "c1_v1", topo)
    report = compare(parse_methods("bm25=bm25_v1,c1=c1_v1", detector_only="bm25_v1"), tmp_path, n_boot=100)

    tel = report["telemetry"]
    assert tel["windows"] == 4 and tel["reference"] == "bm25"
    assert {k: tel["methods"]["bm25"][k] for k in ("tp", "fp", "fn", "tn")} == {"tp": 1, "fp": 0, "fn": 1, "tn": 2}
    assert tel["methods"]["detector_only"]["fp"] == 2  # every candidate is an alert
    pair = tel["pairs"]["c1 - bm25"]
    assert pair["d_recall"] == pytest.approx(0.5) and pair["d_fpr"] == pytest.approx(1.0)
    assert pair["mcnemar_fault"]["a_wrong_b_right"] == 1 and pair["mcnemar_normal"]["a_right_b_wrong"] == 2
    assert pair["mcnemar_all"]["n"] == 4

    alls = report["all"]["methods"]["c1"]
    assert (alls["tp"], alls["fp"], alls["fn"]) == (2, 3, 1)


def test_compare_rejects_runs_over_different_windows(tmp_path: Path) -> None:
    _run(tmp_path, "a", [("w1", 1, 1, 1, "alert")])
    _run(tmp_path, "b", [("w2", 1, 1, 1, "alert")])
    with pytest.raises(ValueError, match="same windows"):
        compare([Method("a", "a"), Method("b", "b")], tmp_path, n_boot=10)
