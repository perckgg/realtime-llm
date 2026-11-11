"""C2/C3 policy and C4 routing (M6, QD-031): pure functions on cached judge answers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from packages.schemas.models import JudgedAlert
from services.judge.policy import EvidenceFact, PolicyConfig, apply_policy, decide, is_abnormal
from services.judge.routing import RoutingConfig, escalation_reason, route


def _alert(verdict: str = "TRUE_ALERT", confidence: float = 0.9, **debug: Any) -> JudgedAlert:
    return JudgedAlert(
        alert_id="a",
        candidate_id="c",
        window_id="w",
        service="cart",
        ts=datetime(2022, 8, 22, tzinfo=UTC),
        verdict=verdict,  # type: ignore[arg-type]
        raw_verdict=verdict,  # type: ignore[arg-type]
        confidence=confidence,
        reasoning="",
        evidence_event_ids=["e1"],
        judge_backend="mock",
        llm_latency_ms=0.0,
        cache_hit=True,
        debug={"status": "llm_valid", **debug},
    )


SLOW = EvidenceFact("slow", "cart", "trace", duration_ms=500.0, baseline_ms=100.0)
FAST = EvidenceFact("fast", "cart", "trace", duration_ms=50.0, baseline_ms=100.0)
NO_BASELINE = EvidenceFact("nb", "cart", "trace", duration_ms=500.0)
ERROR_LOG = EvidenceFact("err", "cart", "log", severity="error")
INFO_LOG = EvidenceFact("info", "cart", "log", severity="INFO")
OTHER = EvidenceFact("other", "redis", "trace", duration_ms=500.0, baseline_ms=100.0)
LEVELS = frozenset({"ERROR", "WARN"})


def test_abnormal_evidence_must_be_of_s0() -> None:
    assert is_abnormal(SLOW, "cart", LEVELS)
    assert is_abnormal(ERROR_LOG, "cart", LEVELS)
    assert not is_abnormal(FAST, "cart", LEVELS)
    assert not is_abnormal(NO_BASELINE, "cart", LEVELS)
    assert not is_abnormal(INFO_LOG, "cart", LEVELS)
    assert not is_abnormal(OTHER, "cart", LEVELS)


def test_rule_order_evidence_threshold_gating_anchoring() -> None:
    config = PolicyConfig(theta_local=0.8, theta_topo=0.9)
    assert decide("TRUE_ALERT", 0.95, [], "cart", 2, config).downgraded_by_evidence_rule
    assert decide("TRUE_ALERT", 0.7, [SLOW], "cart", 2, config).downgraded_by_threshold
    gated = decide("TRUE_ALERT", 0.85, [SLOW], "cart", 2, config)
    assert gated.verdict == "UNCERTAIN" and gated.downgraded_by_gating and gated.threshold_applied == 0.9
    assert decide("TRUE_ALERT", 0.85, [SLOW], "cart", 1, config).verdict == "TRUE_ALERT"
    assert decide("TRUE_ALERT", 0.95, [FAST, OTHER], "cart", 2, config).downgraded_by_anchoring
    kept = decide("TRUE_ALERT", 0.95, [FAST, SLOW], "cart", 2, config)
    assert kept.verdict == "TRUE_ALERT" and kept.anchor_ids == ("slow",)


def test_switches_and_non_true_verdicts() -> None:
    off = PolicyConfig(theta_local=0.8, theta_topo=0.9, gating=False, anchoring=False)
    assert decide("TRUE_ALERT", 0.85, [FAST], "cart", 2, off).verdict == "TRUE_ALERT"
    assert off.threshold(2) == 0.8
    assert decide("FALSE_POSITIVE", 0.1, [], "cart", 2, PolicyConfig()).verdict == "FALSE_POSITIVE"


def test_apply_policy_keeps_raw_and_judge_errors_stay_uncertain() -> None:
    config = PolicyConfig(theta_local=0.8, theta_topo=0.9)
    out = apply_policy(_alert(confidence=0.85), [SLOW], 2, config)
    assert (out.raw_verdict, out.verdict, out.routing_tier) == ("TRUE_ALERT", "UNCERTAIN", 2)
    assert out.downgraded_by_gating and out.debug["status"] == "llm_valid"
    error = apply_policy(_alert(status="manual_review"), [SLOW], 1, config)
    assert error.verdict == "UNCERTAIN"


def test_escalation_reasons() -> None:
    config = RoutingConfig(fp_confidence=0.85)
    assert escalation_reason(_alert(), 0, config) == "no_context"
    assert escalation_reason(_alert("UNCERTAIN"), 3, config) == "uncertain"
    assert escalation_reason(_alert("FALSE_POSITIVE", 0.8), 3, config) == "weak_fp"
    assert escalation_reason(_alert("FALSE_POSITIVE", 0.9), 3, config) is None
    assert escalation_reason(_alert(), 3, config) is None
    assert escalation_reason(_alert("UNCERTAIN"), 0, RoutingConfig(enabled=False)) is None
    assert escalation_reason(_alert("UNCERTAIN"), 3, RoutingConfig(escalate_on=frozenset({"weak_fp"}))) is None
    with pytest.raises(ValueError):
        RoutingConfig(escalate_on=frozenset({"rrf"}))


def test_route_budget_and_empty_tier2() -> None:
    first, second = _alert("UNCERTAIN"), _alert("TRUE_ALERT")
    routed = route(lambda: (first, 3), lambda: second, RoutingConfig())
    assert (routed.llm_calls, routed.escalation, routed.alert.routing_tier) == (2, "uncertain", 2)
    assert route(lambda: (first, 3), lambda: second, RoutingConfig(), calls_left=1).tier2_skipped == "budget"
    empty = route(lambda: (first, 3), lambda: None, RoutingConfig())
    assert (empty.llm_calls, empty.tier2_skipped, empty.alert.verdict) == (1, "empty_context", "UNCERTAIN")
    sure = route(lambda: (second, 3), lambda: pytest.fail("tier 2 must not run"), RoutingConfig())
    assert sure.llm_calls == 1 and sure.escalation is None
