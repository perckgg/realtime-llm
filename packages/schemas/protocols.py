"""The four interfaces of 01-architecture-design.md SS5.

Signatures are frozen from milestone M1 on: changing one means updating
01 SS5 in the same commit. Strategy- or judge-specific parameters (`hop`,
`decay_factor`, thresholds...) go in the constructor, read from config, never
into these method signatures.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from packages.schemas.models import (
    AlertCandidate,
    JudgedAlert,
    RetrievalBudget,
    RetrievalResult,
    TelemetryWindow,
)


@runtime_checkable
class SourceAdapter(Protocol):
    name: str

    def stream(self) -> Iterator[TelemetryWindow]:
        """Emit windows in time order, respecting the watermark."""
        ...


@runtime_checkable
class Detector(Protocol):
    name: str

    def score(self, window: TelemetryWindow) -> float:
        """Anomaly score normalised to [0, 1]."""
        ...

    def is_candidate(self, window: TelemetryWindow, score: float) -> bool:
        """Apply the threshold. The Rescue Score gate is handled outside."""
        ...


@runtime_checkable
class RetrievalStrategy(Protocol):
    name: str

    def retrieve(self, candidate: AlertCandidate, budget: RetrievalBudget) -> RetrievalResult: ...


@runtime_checkable
class Judge(Protocol):
    name: str

    def evaluate(self, candidate: AlertCandidate, context: RetrievalResult) -> JudgedAlert:
        """Verdict TRUE_ALERT / FALSE_POSITIVE / UNCERTAIN with evidence."""
        ...
