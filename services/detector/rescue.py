"""Rescue Score gate, C5 (01-architecture-design.md SS6.2, 02 SS6.1; M7, QD-033).

    RescueScore(w | A) = eta1 * Lambda_log(w) + eta2 * Phi_topo(w, A) + eta3 * Delta_time(w, A)

A window the detector did not promote (y_IF(w) == 0) becomes an
`AlertCandidate(source="rescue")` when RescueScore >= tau.

- Lambda_log(w) = 1 - exp(-N_err(w) / k_log): error-log density of the window's pod.
- Phi_topo(w, A) = max over active alerted services s_a of 1 / (1 + d(s_w, s_a)), d the
  undirected service-graph distance (0 if A is empty or no alerted service is reachable).
- Delta_time(w, A) = max over active alerts of exp(-|t_w - t_a| / sigma).

A = the pipeline's own alerts (CTAV decisions, never labels) that fired at or before t_w and
at most `active_seconds` earlier -- the incident-grouping window of 01 SS6.5. Every
parameter comes from the caller's config.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

COMPONENTS = ("lambda_log", "phi_topo", "delta_time")


@dataclass(frozen=True)
class ErrorLogRule:
    """Which log lines count in N_err: a severity level or a message pattern (HTTP 5xx, exception)."""

    levels: frozenset[str]
    patterns: tuple[re.Pattern[str], ...]

    @classmethod
    def from_config(cls, spec: Mapping[str, Sequence[str]]) -> ErrorLogRule:
        return cls(
            levels=frozenset(str(level).upper() for level in spec.get("levels", [])),
            patterns=tuple(re.compile(p, re.IGNORECASE) for p in spec.get("patterns", [])),
        )

    def matches(self, severity: str, message: str) -> bool:
        return severity.upper() in self.levels or any(p.search(message) for p in self.patterns)


@dataclass(frozen=True)
class Alert:
    ts: datetime
    service: str


def lambda_log(n_err: int, k_log: float) -> float:
    if k_log <= 0:
        raise ValueError("k_log must be > 0")
    return 1.0 - math.exp(-max(n_err, 0) / k_log)


def active_alerts(alerts: Sequence[Alert], t_w: datetime, active_seconds: float) -> list[Alert]:
    """Alerts with t_w - active_seconds <= t_a <= t_w (causal: no alert from the future)."""
    return [a for a in alerts if 0.0 <= (t_w - a.ts).total_seconds() <= active_seconds]


def phi_topo(service: str, active: Iterable[Alert], distance: Callable[[str, str], int | None]) -> float:
    best = 0.0
    for alert in active:
        d = distance(service, alert.service)
        if d is not None:
            best = max(best, 1.0 / (1.0 + d))
    return best


def delta_time(t_w: datetime, active: Iterable[Alert], sigma_seconds: float) -> float:
    if sigma_seconds <= 0:
        raise ValueError("sigma_seconds must be > 0")
    return max((math.exp(-abs((t_w - a.ts).total_seconds()) / sigma_seconds) for a in active), default=0.0)


@dataclass(frozen=True)
class RescueParams:
    eta1: float
    eta2: float
    eta3: float
    tau: float

    def __post_init__(self) -> None:
        etas = (self.eta1, self.eta2, self.eta3)
        if min(etas) < 0 or not math.isclose(sum(etas), 1.0, abs_tol=1e-9):
            raise ValueError(f"eta must be >= 0 and sum to 1, got {etas}")


def rescue_score(components: Mapping[str, float], params: RescueParams) -> float:
    return (
        params.eta1 * components["lambda_log"]
        + params.eta2 * components["phi_topo"]
        + params.eta3 * components["delta_time"]
    )


def is_rescued(promoted_by_detector: bool, score: float, params: RescueParams) -> bool:
    return not promoted_by_detector and score >= params.tau


def eta_grid(step: float = 0.2) -> list[tuple[float, float, float]]:
    """(eta1, eta2, eta3) on the simplex with the given step (02 SS6.1: 21 points for 0.2)."""
    n = round(1 / step)
    if not math.isclose(n * step, 1.0):
        raise ValueError("1 / step must be an integer")
    return [(round(i * step, 10), round(j * step, 10), round((n - i - j) * step, 10))
            for i in range(n + 1) for j in range(n + 1 - i)]
