"""eval.harness: statistics, metrics, GD1 gate/budget/decision rules, config checks."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from eval.harness.metrics import confusion, is_alert, scores, summarize
from eval.harness.runner import Gate, _decision, load_config
from eval.harness.stats import bootstrap_ci, bootstrap_confusion_ci, mcnemar_exact
from packages.schemas.models import JudgedAlert


def _row(fault: bool, decision: str, candidate: bool = True, telemetry: bool = True, **extra) -> dict:
    row = {
        "label_is_fault": int(fault),
        "decision": decision,
        "is_candidate": int(candidate),
        "has_telemetry": int(telemetry),
        "retrieved": 0,
        "judged": 0,
        "context_events": 0,
        "context_tokens": 0,
        "retrieval_latency_ms": "",
        "llm_latency_ms": "",
        "prompt_tokens": "",
        "completion_tokens": "",
        "cache_hit": 0,
        "actual_api_call": 0,
        "downgraded_by_evidence_rule": 0,
        "judge_status": "",
    }
    row.update(extra)
    return row


# --- stats -------------------------------------------------------------------------------


def test_mcnemar_exact_known_values():
    assert mcnemar_exact([True] * 5, [True] * 5) == 1.0  # no discordant pairs
    # b = 10, c = 0 -> 2 * 0.5**10
    assert mcnemar_exact([True] * 10, [False] * 10) == pytest.approx(2 / 1024)
    # b = 3, c = 1 -> 2 * P(X <= 1 | n=4) = 2 * 5/16
    a = [True, True, True, False]
    b = [False, False, False, True]
    assert mcnemar_exact(a, b) == pytest.approx(10 / 16)
    with pytest.raises(ValueError):
        mcnemar_exact([True], [True, False])


def test_bootstrap_ci_contains_point_estimate_and_is_deterministic():
    values = [0.0] * 70 + [1.0] * 30
    lo, hi = bootstrap_ci(values, lambda s: sum(s) / len(s), n_boot=500, seed=1)
    assert lo < 0.3 < hi
    assert (lo, hi) == bootstrap_ci(values, lambda s: sum(s) / len(s), n_boot=500, seed=1)
    assert all(math.isnan(x) for x in bootstrap_ci([], len))


def test_confusion_bootstrap_matches_row_bootstrap():
    cm = {"tp": 30, "fp": 10, "fn": 20, "tn": 140}
    fast = bootstrap_confusion_ci(cm, scores, n_boot=2000, seed=3)
    rows = (
        [("tp")] * 30 + [("fp")] * 10 + [("fn")] * 20 + [("tn")] * 140
    )
    slow = bootstrap_ci(rows, lambda s: scores({c: s.count(c) for c in ("tp", "fp", "fn", "tn")})["f1"], 2000, 3)
    assert fast["f1"][0] == pytest.approx(slow[0], abs=0.03)
    assert fast["f1"][1] == pytest.approx(slow[1], abs=0.03)
    assert fast["precision"][0] < 0.75 < fast["precision"][1]


# --- metrics -----------------------------------------------------------------------------


def test_recall_counts_faults_the_detector_never_promoted():
    rows = [
        _row(True, "alert"),
        _row(True, "none", candidate=False),  # detector miss is still a FN (02 SS4.1)
        _row(False, "alert"),
        _row(False, "manual_review"),  # manual review is not an alert
        _row(False, "none", candidate=False),
    ]
    cm = confusion(rows, is_alert)
    assert cm == {"tp": 1, "fp": 1, "fn": 1, "tn": 2}
    assert scores(cm) == {"precision": 0.5, "recall": 0.5, "f1": 0.5, "fpr": pytest.approx(1 / 3)}


def test_summarize_reports_telemetry_subset_and_all():
    rows = [
        _row(True, "alert", context_events=3, retrieved=1, judged=1, retrieval_latency_ms=5.0, llm_latency_ms=1.0),
        _row(False, "alert", retrieved=1, judged=1, retrieval_latency_ms=7.0, llm_latency_ms=2.0),
        _row(False, "none", candidate=False, telemetry=False),
        _row(False, "none", candidate=False, telemetry=False),
    ]
    summary = summarize(rows, n_boot=50)
    assert summary["telemetry"]["operations"]["windows"] == 2
    assert summary["all"]["operations"]["windows"] == 4
    assert summary["telemetry"]["pipeline"]["fpr"] == 1.0
    assert summary["all"]["pipeline"]["fpr"] == pytest.approx(1 / 3)
    assert summary["all"]["operations"]["context_coverage"] == 1.0
    assert summary["all"]["detector_only"]["fp"] == 1
    assert len(summary["all"]["pipeline"]["f1_ci95"]) == 2


# --- GD1 gate, budget, decisions ---------------------------------------------------------


def test_gate_disabled_sends_everything_to_judge():
    gate = Gate(None)
    assert gate.action(0.01) == "call_llm"


def test_gate_thresholds_and_budget():
    gate = Gate({"enabled": True, "low_threshold": 0.8, "high_threshold": 0.98, "high_score_action": "direct_alert",
                 "max_llm_calls": 1, "budget_exhausted_action": "route_alert"})
    assert gate.action(0.5) == "ignore"
    assert gate.action(0.99) == "direct_alert"
    assert gate.action(0.9) == "call_llm"
    gate.calls = 1
    assert gate.action(0.9) == "llm_budget_exhausted"
    assert _decision("llm_budget_exhausted", gate, None) == "alert"
    assert _decision("ignore", gate, None) == "suppress"
    assert _decision("direct_alert", gate, None) == "alert"
    assert _decision("not_candidate", gate, None) == "none"
    assert _decision("llm_budget_exhausted", Gate({"max_llm_calls": 0}), None) == "manual_review"


@pytest.mark.parametrize(("verdict", "decision"), [("TRUE_ALERT", "alert"), ("FALSE_POSITIVE", "suppress"),
                                                   ("UNCERTAIN", "manual_review")])
def test_decision_follows_verdict(verdict, decision):
    from datetime import UTC, datetime

    judged = JudgedAlert(
        alert_id="a", candidate_id="c", window_id="w", service="s", ts=datetime(2022, 1, 1, tzinfo=UTC),
        verdict=verdict, raw_verdict=verdict, confidence=0.9, reasoning="", evidence_event_ids=[],
        judge_backend="mock", llm_latency_ms=0.0, cache_hit=False,
    )
    assert _decision("call_llm", Gate(None), judged) == decision


# --- config -------------------------------------------------------------------------------


def test_load_config_requires_exactly_one_window_source(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("run_id: x\ndetector: {}\nretrieval: {}\njudge: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)
    path.write_text("run_id: x\nsplit: dev\ndetector: {}\nstages: detector\n", encoding="utf-8")
    assert load_config(path)["split"] == "dev"
    path.write_text("run_id: x\nsplit: dev\ndetector: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):  # full pipeline needs retrieval + judge
        load_config(path)


def test_committed_configs_load():
    for path in (Path(__file__).parents[1] / "eval" / "configs").glob("*.yaml"):
        if path.name == "bm25_baseline.yaml":
            continue  # M0 draft, superseded in M4
        load_config(path)


# --- parallel judging (QD-019) ------------------------------------------------------------


def test_rate_limiter_spaces_calls_across_threads():
    import threading
    import time

    from services.judge.backends import RateLimiter

    limiter = RateLimiter(per_minute=1200)  # one slot every 50 ms
    stamps: list[float] = []
    lock = threading.Lock()

    def take() -> None:
        limiter.acquire()
        with lock:
            stamps.append(time.monotonic())

    threads = [threading.Thread(target=take) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stamps.sort()
    assert stamps[-1] - stamps[0] >= 5 * 0.05 - 0.01
    RateLimiter(0).acquire()  # disabled: returns immediately


def test_judge_all_parallel_equals_sequential_and_keeps_order():
    from datetime import UTC, datetime

    from eval.harness.runner import judge_all
    from packages.schemas.models import AlertCandidate, ContextEvent, RetrievalResult
    from services.judge.backends import MockBackend
    from services.judge.llm_judge import LLMJudge

    ts = datetime(2022, 8, 22, tzinfo=UTC)
    jobs = []
    for i in range(20):
        severity = ["ERROR", "INFO", "WARN"][i % 3]
        event = ContextEvent(
            event_id=f"e{i}", modality="log", ts=ts, service="s", content="m", score=0.5,
            debug={"source": "nezha_log", "severity": severity, "event_type": "application_log"},
        )
        candidate = AlertCandidate(
            candidate_id=f"c{i}", window_id=f"w{i}", service="s", ts=ts, anomaly_score=0.9, source="metric"
        )
        jobs.append((candidate, RetrievalResult(strategy="x", events=[event], latency_ms=0, token_estimate=1)))
    judge = LLMJudge(MockBackend())

    def strip(alerts):
        return [a.model_dump(exclude={"llm_latency_ms"}) for a in alerts]

    sequential = judge_all(judge, jobs, workers=1)
    parallel = judge_all(judge, jobs, workers=8)
    assert strip(parallel) == strip(sequential)
    assert [a.candidate_id for a in parallel] == [f"c{i}" for i in range(20)]


def test_response_cache_is_safe_under_concurrent_writes(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor

    from services.judge.cache import ResponseCache

    path = tmp_path / "c.jsonl"
    cache = ResponseCache(path)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: cache.put(f"k{i}", {"raw": "{}", "n": i}), range(200)))
    reloaded = ResponseCache(path)
    assert len(reloaded) == 200
    assert all(reloaded.get(f"k{i}")["n"] == i for i in range(200))  # type: ignore[index]


PARITY_SWITCHES = [
    {"retrieval": {"type": "bm25_hybrid", "parity_query_terms": True}, "judge": {}},
    {"evidence": {"store": "gd1_corpus", "path": "x"}, "retrieval": {"type": "bm25_hybrid"}, "judge": {}},
    {"retrieval": {"type": "hybrid_bm25_graph", "params": {"bm25_pool": "global"}}, "judge": {}},
]


@pytest.mark.parametrize("extra", PARITY_SWITCHES)
def test_parity_switches_are_forbidden_on_val_and_test(tmp_path: Path, extra: dict):
    import yaml

    path = tmp_path / "c.yaml"
    for split in ("val", "test"):
        path.write_text(yaml.safe_dump({"run_id": "x", "split": split, "detector": {}, **extra}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_config(path)
    path.write_text(yaml.safe_dump({"run_id": "x", "split": "dev", "detector": {}, **extra}), encoding="utf-8")
    load_config(path)  # allowed on dev (parity checks)
