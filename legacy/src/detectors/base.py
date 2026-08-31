from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import DetectorResult, MetricWindow


class BaseDetector(ABC):
    @abstractmethod
    def score(self, window: MetricWindow) -> DetectorResult:
        raise NotImplementedError

