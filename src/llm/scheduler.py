from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from src.models import AlertCandidate


@dataclass
class LLMRouteDecision:
    action: str
    reason: str
    priority_score: float
    delay_seconds: float = 0.0
    api_deferred: bool = False


class LLMRequestScheduler:
    """Priority-aware routing for expensive or rate-limited API LLM calls.

    This is intentionally in-memory for experiment runs. It gives the pipeline
    realistic API behavior without introducing a database-backed queue yet.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self.enabled = bool(cfg.get("enabled", False))
        self.high_priority_threshold = float(cfg.get("high_priority_threshold", 0.95))
        self.defer_below_priority = float(cfg.get("defer_below_priority", 0.80))
        self.cooldown_on_429_seconds = float(cfg.get("cooldown_on_429_seconds", 120.0))
        self.low_priority_action = str(cfg.get("low_priority_action", "local_only"))
        self.cooldown_action = str(cfg.get("cooldown_action", "local_only"))
        self.anomaly_weight = float(cfg.get("anomaly_weight", 0.75))
        self.context_weight = float(cfg.get("context_weight", 0.20))
        self.service_weights = {
            str(service): float(weight)
            for service, weight in dict(cfg.get("service_weights", {})).items()
        }
        self.api_cooldown_until = 0.0

    def plan(
        self,
        alert: AlertCandidate,
        *,
        context_signal_score: float = 0.0,
        provider: str = "unknown",
        api_calls_made: int = 0,
        max_api_calls: int = 0,
    ) -> LLMRouteDecision:
        priority = self.priority_score(alert, context_signal_score)
        if not self.enabled:
            return LLMRouteDecision("call", "scheduler_disabled", priority)

        now = time.time()
        if self.api_cooldown_until > now:
            return self._limited_decision(provider, "api_cooldown_active", priority, self.api_cooldown_until - now)

        if alert.anomaly_score >= self.high_priority_threshold or priority >= self.high_priority_threshold:
            return LLMRouteDecision("call", "high_priority", priority)

        if max_api_calls and api_calls_made >= max_api_calls:
            return self._limited_decision(provider, "api_budget_exhausted", priority, 0.0)

        if priority < self.defer_below_priority:
            return self._limited_decision(provider, "below_defer_priority", priority, 0.0, self.low_priority_action)

        return LLMRouteDecision("call", "priority_allows_api", priority)

    def record_result(self, error: str | None, actual_api_call: bool) -> None:
        if not actual_api_call or not error:
            return
        if "429" in error or "Too Many Requests" in error:
            self.api_cooldown_until = max(self.api_cooldown_until, time.time() + self.cooldown_on_429_seconds)

    def priority_score(self, alert: AlertCandidate, context_signal_score: float = 0.0) -> float:
        service_boost = self.service_weights.get(alert.service_id, 0.0)
        score = (
            self.anomaly_weight * float(alert.anomaly_score)
            + self.context_weight * max(0.0, min(1.0, float(context_signal_score)))
            + service_boost
        )
        score = max(score, float(alert.anomaly_score))
        return round(max(0.0, min(1.0, score)), 4)

    def _limited_decision(
        self,
        provider: str,
        reason: str,
        priority: float,
        delay_seconds: float,
        preferred_action: str | None = None,
    ) -> LLMRouteDecision:
        action = preferred_action or self.cooldown_action
        if action == "local_only" and provider != "local_first":
            action = "defer"
        if action not in {"local_only", "defer"}:
            action = "defer"
        return LLMRouteDecision(
            action=action,
            reason=reason,
            priority_score=priority,
            delay_seconds=round(max(0.0, delay_seconds), 4),
            api_deferred=True,
        )
