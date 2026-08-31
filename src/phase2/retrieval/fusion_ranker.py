from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from src.retrieval.context_store import StoredContext


EPSILON = 1e-9


@dataclass(frozen=True)
class FusionWeights:
    alpha: float = 0.4
    beta: float = 0.3
    gamma: float = 0.3

    def __post_init__(self) -> None:
        values = (self.alpha, self.beta, self.gamma)
        if any(value < 0.0 for value in values):
            raise ValueError("Fusion weights must be non-negative")
        if not math.isclose(sum(values), 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Fusion weights must sum to 1.0")


@dataclass
class FusionCandidate:
    context: StoredContext
    bm25_raw: float
    graph_distance: int | None
    source_flags: set[str]
    bm25_norm: float = 0.0
    time_sim: float = 0.0
    graph_sim: float = 0.0
    score_final: float = 0.0


class FusionRanker:
    def __init__(self, weights: FusionWeights | None = None, tau_seconds: float = 300.0) -> None:
        self.weights = weights or FusionWeights()
        if tau_seconds <= 0:
            raise ValueError("tau_seconds must be positive")
        self.tau_seconds = tau_seconds

    def rank(
        self,
        candidates: list[FusionCandidate],
        alert_time: datetime,
        top_k: int,
    ) -> list[FusionCandidate]:
        if top_k <= 0:
            return []
        if not candidates:
            return []

        bm25_values = [candidate.bm25_raw for candidate in candidates]
        bm25_min = min(bm25_values)
        bm25_max = max(bm25_values)
        for candidate in candidates:
            candidate.bm25_norm = normalize_bm25(candidate.bm25_raw, bm25_min, bm25_max)
            candidate.time_sim = time_sim(candidate.context.event.timestamp, alert_time, self.tau_seconds)
            candidate.graph_sim = graph_sim(candidate.graph_distance)
            candidate.score_final = clamp01(
                self.weights.alpha * candidate.bm25_norm
                + self.weights.beta * candidate.time_sim
                + self.weights.gamma * candidate.graph_sim
            )

        ranked = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score_final,
                -candidate.bm25_norm,
                -candidate.time_sim,
                candidate.graph_distance if candidate.graph_distance is not None else 10**9,
                candidate.context.event.doc_id,
            ),
        )
        return ranked[:top_k]


def normalize_bm25(value: float, bm25_min: float, bm25_max: float) -> float:
    if bm25_max <= bm25_min:
        return 1.0 if value > 0.0 else 0.0
    return clamp01((value - bm25_min) / (bm25_max - bm25_min + EPSILON))


def time_sim(timestamp: datetime, alert_time: datetime, tau_seconds: float) -> float:
    distance = abs((timestamp - alert_time).total_seconds())
    return clamp01(math.exp(-distance / tau_seconds))


def graph_sim(distance: int | None) -> float:
    if distance is None:
        return 0.0
    return clamp01(1.0 / (1.0 + distance))


def clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))
