"""Tests for the V35 context-precision grading rule and aggregation (M8 task 9, QD-051)."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from scripts.m8_context_precision_rule_label import (
    Rule,
    binary_label,
    build_rows,
    label_event,
    parse_duration,
)
from scripts.m8_context_precision_score import Event, counts, load_events, macro, micro, summarise


def _row(window_no: int, event_no: int, label: str, ranks: dict[str, int | None]) -> Event:
    return Event(window_no, event_no, {"relevance": label}, ranks)


# --- labeling rule -------------------------------------------------------------------------


def test_parse_duration_reads_ms_and_ignores_logs() -> None:
    assert parse_duration("Trace span GetCart on pod duration_ms=12.5") == 12.5
    assert parse_duration('{"log":"INFO something"}') is None


@pytest.mark.parametrize(
    ("seconds", "severity", "duration", "expected", "branch"),
    [
        (10.0, "INFO", 250.0, "1", "slow_in_window"),
        (-175.0, "INFO", 900.0, "1", "slow_in_window"),
        (400.0, "INFO", 900.0, "0", "slow_out_of_window"),
        (5.0, "WARN", 2.0, "1", "warn_in_window"),
        (300.0, "WARN", 2.0, "0", "warn_out_of_window"),
        (5.0, "INFO", 150.0, "?", "mid_band_in_window"),
        (150.0, "INFO", 150.0, "0", "mid_band_out_of_window"),
        (5.0, "INFO", 7.0, "0", "fast_span"),
        (5.0, "INFO", None, "0", "no_duration"),
    ],
)
def test_label_event(
    seconds: float, severity: str, duration: float | None, expected: str, branch: str
) -> None:
    label, got_branch = label_event(seconds, severity, duration, Rule())
    assert (label, got_branch) == (expected, branch)


ERROR_LOG = (
    '{"log":"20:46:10.826 ERROR f.s.FoodServiceImpl#302 TraceID: 29fc [getAllFood]'
    '[Get the Get Food Request Failed!]\\n","stream":"stdout"}'
)
INFO_LOG = '{"log":"20:46:10.826 INFO f.s.FoodServiceImpl#120 [getAllFood][Success]\\n"}'
ERROR_SPAN = "Trace span BasicErrorController.error on ts-preserve-service-b5ccf8557-l5l4p duration_ms=0.650"


@pytest.mark.parametrize(
    ("seconds", "content", "expected", "branch"),
    [
        (-102.2, ERROR_LOG, "1", "error_log_in_window"),  # W49.E5: severity column says INFO
        (400.0, ERROR_LOG, "0", "error_log_out_of_window"),
        (-0.3, ERROR_SPAN, "1", "error_span_in_window"),  # W29.E2: ~1 ms, duration rule never fires
        (16.4, ERROR_SPAN, "1", "error_span_in_window"),  # W47.E3
        (300.0, ERROR_SPAN, "0", "error_span_out_of_window"),
        (5.0, INFO_LOG, "0", "no_duration"),
    ],
)
def test_label_event_reads_error_signals_from_content(
    seconds: float, content: str, expected: str, branch: str
) -> None:
    duration = parse_duration(content)
    label, got_branch = label_event(seconds, "INFO", duration, Rule(), content)
    assert (label, got_branch) == (expected, branch)


def test_error_controller_name_inside_a_slow_span_of_another_op_is_not_an_error_span() -> None:
    content = "Trace span HTTP GET /error-page on pod duration_ms=3.0"
    assert label_event(5.0, "INFO", 3.0, Rule(), content) == ("0", "fast_span")


def test_sensitivity_columns_also_see_content_errors() -> None:
    graded = [
        {"window_no": "49", "event_no": "5", "seconds_from_window_start": "-102.2",
         "severity": "INFO", "content": ERROR_LOG},
        {"window_no": "29", "event_no": "2", "seconds_from_window_start": "-0.3",
         "severity": "INFO", "content": ERROR_SPAN},
    ]  # fmt: skip
    for row in build_rows(graded, Rule()):
        assert (row["relevance"], row["relevance_loose"], row["relevance_strict"]) == ("1", "1", "1")


def test_binary_label_sensitivity_thresholds() -> None:
    assert binary_label(5.0, "INFO", 120.0, 100.0, 180.0) == "1"
    assert binary_label(5.0, "INFO", 120.0, 200.0, 180.0) == "0"
    assert binary_label(5.0, "INFO", 600.0, 500.0, 180.0) == "1"
    assert binary_label(500.0, "INFO", 600.0, 500.0, 180.0) == "0"


def test_build_rows_emits_three_label_columns() -> None:
    graded = [
        {
            "window_no": "1",
            "event_no": "2",
            "seconds_from_window_start": "-10.0",
            "severity": "INFO",
            "content": "Trace span GetCart on pod duration_ms=250.0",
        }
    ]
    rows = build_rows(graded, Rule())
    assert rows[0]["relevance"] == "1"
    assert rows[0]["relevance_loose"] == "1"
    assert rows[0]["relevance_strict"] == "0"
    assert rows[0]["note"].startswith("dur=250.0ms")


# --- aggregation ---------------------------------------------------------------------------


def test_counts_and_precision_policies() -> None:
    events = [
        Event(1, 1, {"relevance": "1"}, {"bm25": 1, "c1": None}),
        Event(1, 2, {"relevance": "0"}, {"bm25": 2, "c1": 1}),
        Event(1, 3, {"relevance": "?"}, {"bm25": None, "c1": 2}),
        Event(2, 1, {"relevance": "1"}, {"bm25": 1, "c1": 1}),
        Event(2, 2, {"relevance": "0"}, {"bm25": None, "c1": 2}),
    ]
    assert counts(events, "bm25", "relevance", "irrelevant") == (2, 3, 0, 3)
    assert counts(events, "c1", "relevance", "irrelevant") == (1, 4, 1, 4)
    assert counts(events, "c1", "relevance", "exclude") == (1, 3, 1, 4)
    assert counts(events, "c1", "relevance", "relevant") == (2, 4, 1, 4)


def test_micro_and_macro() -> None:
    assert micro([(1, 2), (1, 1)]) == pytest.approx(2 / 3)
    assert macro([(1, 2), (1, 1)]) == pytest.approx(0.75)
    assert math.isnan(micro([(0, 0)]))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    pairs = [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2)]
    graded = [{"window_no": str(w), "event_no": str(e)} for w, e in pairs]
    labels = [
        {"window_no": "1", "event_no": "1", "relevance": "1", "relevance_loose": "1", "relevance_strict": "0"},
        {"window_no": "1", "event_no": "2", "relevance": "0", "relevance_loose": "0", "relevance_strict": "0"},
        {"window_no": "1", "event_no": "3", "relevance": "?", "relevance_loose": "1", "relevance_strict": "0"},
        {"window_no": "2", "event_no": "1", "relevance": "1", "relevance_loose": "1", "relevance_strict": "1"},
        {"window_no": "2", "event_no": "2", "relevance": "0", "relevance_loose": "0", "relevance_strict": "0"},
    ]
    key = [
        {"window_no": "1", "event_no": "1", "rank_bm25": "1", "rank_c1": ""},
        {"window_no": "1", "event_no": "2", "rank_bm25": "2", "rank_c1": "1"},
        {"window_no": "1", "event_no": "3", "rank_bm25": "", "rank_c1": "2"},
        {"window_no": "2", "event_no": "1", "rank_bm25": "1", "rank_c1": "1"},
        {"window_no": "2", "event_no": "2", "rank_bm25": "", "rank_c1": "2"},
    ]
    graded_path, labels_path, key_path = tmp_path / "g.csv", tmp_path / "l.csv", tmp_path / "k.csv"
    _write_csv(graded_path, graded)
    _write_csv(labels_path, labels)
    _write_csv(key_path, key)
    return graded_path, labels_path, key_path


def test_load_events_and_summarise(tmp_path: Path) -> None:
    graded, labels, key = _fixture_files(tmp_path)
    events = load_events(graded, labels, key, top_k=6)
    assert len(events) == 5
    block = summarise(events, "relevance", "irrelevant", n_boot=50, seed=7)
    methods = block["methods"]
    assert methods["bm25"]["retrieved"] == 3
    assert methods["bm25"]["relevant"] == 2
    assert methods["bm25"]["micro"] == pytest.approx(2 / 3)
    assert methods["bm25"]["macro"] == pytest.approx(0.75)
    assert methods["c1"]["retrieved"] == 4
    assert methods["c1"]["relevant"] == 1
    assert methods["c1"]["micro"] == pytest.approx(0.25)
    assert methods["c1"]["unsure_rate"] == pytest.approx(0.25)
    assert block["delta"]["micro"] == pytest.approx(0.25 - 2 / 3)
    assert block["per_window"]["1"]["c1"] == (0, 2)


def test_unsure_policies_change_denominator(tmp_path: Path) -> None:
    graded, labels, key = _fixture_files(tmp_path)
    events = load_events(graded, labels, key, top_k=6)
    excluded = summarise(events, "relevance", "exclude", n_boot=20, seed=7)
    as_relevant = summarise(events, "relevance", "relevant", n_boot=20, seed=7)
    assert excluded["methods"]["c1"]["retrieved"] == 3
    assert excluded["methods"]["c1"]["micro"] == pytest.approx(1 / 3)
    assert as_relevant["methods"]["c1"]["relevant"] == 2
    assert as_relevant["methods"]["c1"]["micro"] == pytest.approx(0.5)


def test_bootstrap_is_deterministic(tmp_path: Path) -> None:
    graded, labels, key = _fixture_files(tmp_path)
    events = load_events(graded, labels, key, top_k=6)
    first = summarise(events, "relevance", "irrelevant", n_boot=100, seed=42)["methods"]["c1"]["micro_ci95"]
    second = summarise(events, "relevance", "irrelevant", n_boot=100, seed=42)["methods"]["c1"]["micro_ci95"]
    assert first == second


def test_validation_rejects_empty_label_or_bad_rank(tmp_path: Path) -> None:
    graded, labels, key = _fixture_files(tmp_path)
    rows = list(csv.DictReader(labels.open(encoding="utf-8")))
    rows[0]["relevance"] = ""
    _write_csv(labels, rows)
    with pytest.raises(ValueError, match="relevance is empty"):
        load_events(graded, labels, key, top_k=6)

    (tmp_path / "b").mkdir()
    graded, labels, key = _fixture_files(tmp_path / "b")
    key_rows = list(csv.DictReader(key.open(encoding="utf-8")))
    key_rows[0]["rank_bm25"] = "9"
    _write_csv(key, key_rows)
    with pytest.raises(ValueError, match="outside 1..6"):
        load_events(graded, labels, key, top_k=6)


def test_main_writes_json_and_tables_and_refuses_overwrite(tmp_path: Path) -> None:
    from scripts.m8_context_precision_score import main

    graded, labels, key = _fixture_files(tmp_path)
    out = tmp_path / "results" / "run_v1"
    code = main([
        "--graded", str(graded), "--labels", str(labels), "--key", str(key),
        "--out", str(out), "--n-boot", "20",
    ])  # fmt: skip
    assert code == 0
    report = json.loads((out / "context_precision.json").read_text(encoding="utf-8"))
    assert report["n_events"] == 5
    assert "Context precision" in (out / "tables.md").read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="already exists"):
        main([
            "--graded", str(graded), "--labels", str(labels), "--key", str(key),
            "--out", str(out), "--n-boot", "20",
        ])  # fmt: skip
