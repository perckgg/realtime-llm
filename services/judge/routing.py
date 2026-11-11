"""C4 adaptive two-tier routing (08 SS4, 01 SS6.4).

Tier 1 = local evidence (BM25) -> judge -> policy. The decision stands when it is
sure and anchored; otherwise the candidate is escalated to tier 2 (topology
retrieval C1) -> judge -> policy. "Not sure" (08 SS4: "TRUE/FP du chac + bang
chung neo") means:

- `no_context`: tier 1 retrieved nothing;
- `uncertain`: the tier-1 verdict after policy is UNCERTAIN -- judge error, the
  LLM's own "uncertain", or a TRUE_ALERT downgraded by evidence / threshold /
  gating / anchoring (C3 "thieu bang chung");
- `weak_fp`: FALSE_POSITIVE with confidence below `fp_confidence`. QD-031: on
  `val` the topology tier's extra recall comes entirely from tier-1
  FALSE_POSITIVE answers, never from UNCERTAIN ones.

Tier 2 is not judged when its retrieval is empty: the judge would see the tier-1
prompt again. The tier-1 decision then stands. Budget: one call per judged tier;
with no call left, the tier-1 decision stands.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from packages.schemas.models import JudgedAlert

ESCALATION_REASONS = ("no_context", "uncertain", "weak_fp")


@dataclass(frozen=True)
class RoutingConfig:
    enabled: bool = True
    escalate_on: frozenset[str] = frozenset(ESCALATION_REASONS)
    fp_confidence: float = 0.80  # FALSE_POSITIVE below this is "not sure"

    def __post_init__(self) -> None:
        unknown = set(self.escalate_on) - set(ESCALATION_REASONS)
        if unknown:
            raise ValueError(f"unknown escalation reasons {sorted(unknown)}; known: {ESCALATION_REASONS}")


def escalation_reason(tier1: JudgedAlert, tier1_context_events: int, config: RoutingConfig) -> str | None:
    """Why tier 1 is not enough (first matching reason), or None if its decision stands."""
    if not config.enabled:
        return None
    if tier1_context_events == 0 and "no_context" in config.escalate_on:
        return "no_context"
    if tier1.verdict == "UNCERTAIN" and "uncertain" in config.escalate_on:
        return "uncertain"
    if (
        tier1.verdict == "FALSE_POSITIVE"
        and tier1.confidence < config.fp_confidence
        and "weak_fp" in config.escalate_on
    ):
        return "weak_fp"
    return None


@dataclass(frozen=True)
class Routed:
    alert: JudgedAlert  # final decision, `routing_tier` = tier that produced it
    llm_calls: int
    escalation: str | None  # reason, None if tier 1 was enough
    tier2_skipped: str | None = None  # "empty_context" | "budget"


def route(
    tier1: Callable[[], tuple[JudgedAlert, int]],
    tier2: Callable[[], JudgedAlert | None],
    config: RoutingConfig,
    calls_left: int | None = None,
) -> Routed:
    """Run tier 1, then tier 2 if needed.

    `tier1()` -> (alert after policy, number of tier-1 context events); it costs one call.
    `tier2()` -> alert after policy, or None when its
    retrieval is empty (no call is made then). `calls_left` counts the calls still
    allowed, including tier 1's; None = no budget.
    """
    first, events = tier1()
    reason = escalation_reason(first, events, config)
    if reason is None:
        return Routed(first, 1, None)
    if calls_left is not None and calls_left < 2:
        return Routed(first, 1, reason, "budget")
    second = tier2()
    if second is None:
        return Routed(first, 1, reason, "empty_context")
    return Routed(second.model_copy(update={"routing_tier": 2}), 2, reason)
