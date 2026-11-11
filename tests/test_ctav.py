"""eval/harness/ctav.py: CTAV replay on cached tier runs (M6, QD-031)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from eval.harness.ctav import Replay, TierRun, Variant, ablations, component_verdicts, raw_run_predictions
from packages.schemas.models import JudgedAlert
from services.judge.policy import PolicyConfig
from services.judge.routing import RoutingConfig


def _row(window_id: str, fault: bool, candidate: bool = True, decision: str = "suppress") -> dict[str, str]:
    return {
        "window_id": window_id,
        "label_is_fault": str(int(fault)),
        "has_telemetry": "1",
        "is_candidate": str(int(candidate)),
        "decision": decision if candidate else "none",
        "prompt_tokens": "100" if candidate else "",
        "completion_tokens": "10" if candidate else "",
    }


def _judged(window_id: str, verdict: str, confidence: float) -> JudgedAlert:
    return JudgedAlert(
        alert_id=window_id,
        candidate_id=window_id,
        window_id=window_id,
        service="cart",
        ts=datetime(2022, 8, 22, tzinfo=UTC),
        verdict=verdict,  # type: ignore[arg-type]
        raw_verdict=verdict,  # type: ignore[arg-type]
        confidence=confidence,
        reasoning="",
        evidence_event_ids=[f"{window_id}-e"],
        judge_backend="mock",
        llm_latency_ms=0.0,
        cache_hit=True,
        debug={"status": "llm_valid"},
    )


def _replay() -> Replay:
    rows = [_row("w1", True), _row("w2", False, decision="alert"), _row("w3", False, candidate=False)]
    local = TierRun("bm25", rows, {"w1": _judged("w1", "FALSE_POSITIVE", 0.8), "w2": _judged("w2", "TRUE_ALERT", 0.85)},
                    {"w1": ["w1-e"], "w2": ["w2-e"]})
    topo = TierRun("c1", [dict(r) for r in rows],
                   {"w1": _judged("w1", "TRUE_ALERT", 0.9), "w2": _judged("w2", "TRUE_ALERT", 0.85)},
                   {"w1": ["w1-e"], "w2": ["w2-e"]})
    slow = {"service": "cart", "modality": "trace", "severity": "INFO", "duration_ms": 500.0,
            "rolling": {"95": 100.0}, "dev": {}}
    facts = {(run, w, f"{w}-e"): {**slow, "event_id": f"{w}-e"} for run in ("bm25", "c1") for w in ("w1", "w2")}
    return Replay(local, topo, facts)


MAIN = Variant("ctav", "two_tier", PolicyConfig(theta_local=0.8, theta_topo=0.9),
               RoutingConfig(fp_confidence=0.85), baseline="rolling", percentile=95)


def test_two_tier_escalates_weak_fp_and_counts_calls() -> None:
    outcome = _replay().run(MAIN)
    assert outcome.decisions == ["alert", "alert", "none"]
    assert outcome.escalations == {"w1": "weak_fp", "w2": None}
    assert (outcome.llm_calls, outcome.tier2_calls, outcome.prompt_tokens) == (3, 1, 300)
    assert outcome.alerts["w1"].routing_tier == 2


def test_topology_only_gates_and_dev_baseline_cannot_anchor() -> None:
    replay = _replay()
    assert replay.run(replace(MAIN, mode="topology_only")).decisions == ["alert", "manual_review", "none"]
    assert replay.run(replace(MAIN, mode="topology_only", baseline="dev")).decisions[0] == "manual_review"


def test_budget_exhaustion_matches_runner_gate() -> None:
    replay = _replay()
    outcome = replay.run(MAIN, budget=1)
    assert outcome.decisions == ["suppress", "manual_review", "none"]  # no call left for tier 2, then none at all
    assert raw_run_predictions(replay.local, 1).tolist() == [False, False, False]
    assert raw_run_predictions(replay.local).tolist() == [False, True, False]


def test_tier_runs_must_cover_the_same_labelled_windows() -> None:
    replay = _replay()
    other = TierRun("c1", [_row("w1", False), *replay.topology.rows[1:]], replay.topology.judged, {})
    with pytest.raises(ValueError):
        Replay(replay.local, other, replay.facts)


def test_c4_verdict_on_a_topology_only_main() -> None:
    main = replace(MAIN, mode="topology_only", routing=replace(MAIN.routing, enabled=False))
    assert [v.name for v in ablations(main)][3] == "with_c4"
    pairs = {
        "no_c2 - ctav": {"d_fpr_ci95": [0.0, 0.001]},
        "no_c3 - ctav": {"d_precision_ci95": [-0.3, -0.1]},
        "with_c4 - ctav": {"d_f1": -0.05, "d_f1_ci95": [-0.09, -0.01]},
    }
    costs = {"ctav": {"estimated_cost_usd": 3.0}, "with_c4": {"estimated_cost_usd": 5.0}}
    verdicts = component_verdicts(pairs, costs, main)
    assert verdicts["C2"]["contributes"] is False and verdicts["C3"]["contributes"] is True
    assert verdicts["C4"]["d_f1_ci95"] == [0.01, 0.09] and verdicts["C4"]["contributes"] is False
