"""CTAV decision policy: C2 asymmetric confidence gating + C3 evidence anchoring
(08 SS4, QD-027, QD-029, QD-031).

A pure function of the judge's raw answer and facts about the evidence it cited,
so it re-runs on cached verdicts without any LLM call (01 SS6.4). Rules, applied
in this order to `raw_verdict` (FALSE_POSITIVE and UNCERTAIN pass unchanged):

1. `require_evidence` (as LLMJudge): TRUE_ALERT citing no evidence of the context
   -> UNCERTAIN, `downgraded_by_evidence_rule`.
2. Threshold. `theta_local` is GD1's symmetric threshold (0.80). With C2 on,
   a verdict whose context came from the topology tier (C1, `tier == 2`) needs
   `theta_topo` instead. QD-029: H1 gave no evidence-profile feature that separates
   normal from fault, so the risky profile is the tier itself. A TRUE_ALERT with
   theta_local <= confidence < theta_topo -> UNCERTAIN, `downgraded_by_gating`;
   below theta_local it is the plain threshold (`downgraded_by_threshold`).
3. C3 anchoring: a TRUE_ALERT must cite at least one *abnormal* event of the
   alerted service s0 -- a log at one of `anchor_log_levels`, or a trace span
   slower than its (service, operation) baseline. Otherwise -> UNCERTAIN,
   `downgraded_by_anchoring`. A span without a baseline (too few spans) cannot be
   shown abnormal, so it does not anchor.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from typing import Literal

from packages.schemas.models import JudgedAlert, Verdict

Tier = Literal[1, 2]


@dataclass(frozen=True)
class EvidenceFact:
    """What C3 needs to know about one cited event."""

    event_id: str
    service: str
    modality: str  # log | trace | metric
    severity: str = "INFO"
    duration_ms: float | None = None
    baseline_ms: float | None = None  # span threshold of the same (service, operation); None = no baseline


@dataclass(frozen=True)
class PolicyConfig:
    theta_local: float = 0.80
    theta_topo: float = 0.80
    gating: bool = True  # C2
    anchoring: bool = True  # C3
    require_evidence: bool = True
    anchor_log_levels: frozenset[str] = field(default_factory=lambda: frozenset({"ERROR", "WARN"}))

    def threshold(self, tier: Tier) -> float:
        return self.theta_topo if self.gating and tier == 2 else self.theta_local


@dataclass(frozen=True)
class PolicyDecision:
    verdict: Verdict
    threshold_applied: float
    downgraded_by_evidence_rule: bool = False
    downgraded_by_threshold: bool = False
    downgraded_by_gating: bool = False
    downgraded_by_anchoring: bool = False
    anchor_ids: tuple[str, ...] = ()


def is_abnormal(fact: EvidenceFact, s0: str, log_levels: Collection[str]) -> bool:
    """C3: abnormal evidence *of s0*."""
    if fact.service != s0:
        return False
    if fact.modality == "log":
        return fact.severity.upper() in log_levels
    if fact.modality == "trace":
        return fact.duration_ms is not None and fact.baseline_ms is not None and fact.duration_ms > fact.baseline_ms
    return False


def decide(
    raw_verdict: Verdict,
    confidence: float,
    cited: Sequence[EvidenceFact],
    s0: str,
    tier: Tier,
    config: PolicyConfig,
) -> PolicyDecision:
    """Final verdict from the raw one. `cited` = evidence the judge cited that exists in the context."""
    threshold = config.threshold(tier)
    if raw_verdict != "TRUE_ALERT":
        return PolicyDecision(raw_verdict, threshold)
    if config.require_evidence and not cited:
        return PolicyDecision("UNCERTAIN", threshold, downgraded_by_evidence_rule=True)
    if confidence < config.theta_local:
        return PolicyDecision("UNCERTAIN", threshold, downgraded_by_threshold=True)
    if confidence < threshold:
        return PolicyDecision("UNCERTAIN", threshold, downgraded_by_gating=True)
    anchors = tuple(f.event_id for f in cited if is_abnormal(f, s0, config.anchor_log_levels))
    if config.anchoring and not anchors:
        return PolicyDecision("UNCERTAIN", threshold, downgraded_by_anchoring=True)
    return PolicyDecision("TRUE_ALERT", threshold, anchor_ids=anchors)


def apply_policy(
    judged: JudgedAlert, cited: Sequence[EvidenceFact], tier: Tier, config: PolicyConfig
) -> JudgedAlert:
    """`judged` with the CTAV verdict; `raw_verdict` and the judge's debug are kept.

    A judge error (manual review) stays UNCERTAIN whatever its raw label."""
    if judged.debug.get("status") == "manual_review":
        decision = PolicyDecision("UNCERTAIN", config.threshold(tier))
    else:
        decision = decide(judged.raw_verdict, judged.confidence, cited, judged.service, tier, config)
    return judged.model_copy(
        update={
            "verdict": decision.verdict,
            "routing_tier": tier,
            "threshold_applied": decision.threshold_applied,
            "downgraded_by_evidence_rule": decision.downgraded_by_evidence_rule,
            "downgraded_by_gating": decision.downgraded_by_gating,
            "downgraded_by_anchoring": decision.downgraded_by_anchoring,
            "debug": {
                **judged.debug,
                "downgraded_by_threshold": decision.downgraded_by_threshold,
                "anchor_ids": list(decision.anchor_ids),
            },
        }
    )
