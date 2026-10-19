"""Uncertainty and paired tests for run results (02-data-and-experiment-protocol.md SS5.2).

- `bootstrap_ci`: 95% percentile bootstrap over windows (resample with
  replacement, recompute the metric, take the 2.5 / 97.5 percentiles).
- `bootstrap_confusion_ci`: the same bootstrap for metrics that depend only on
  the confusion matrix. Resampling n windows with replacement is exactly a
  Multinomial(n, cell shares) draw over the four cells, so it is drawn that
  way (numpy) -- same distribution, fast enough for the ~36k windows of `val`.
- `mcnemar_exact`: two-sided exact McNemar test on per-window correctness of
  two methods over the same windows (paper SS4, QD-011).
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def bootstrap_ci(
    rows: Sequence[T],
    metric_fn: Callable[[Sequence[T]], float],
    n_boot: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI of `metric_fn(rows)`. Deterministic for a seed."""
    if not rows:
        return (math.nan, math.nan)
    rng = random.Random(seed)
    n = len(rows)
    values = sorted(metric_fn([rows[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    lo = values[math.floor((alpha / 2) * (n_boot - 1))]
    hi = values[math.ceil((1 - alpha / 2) * (n_boot - 1))]
    return (lo, hi)


def bootstrap_confusion_ci(
    cm: dict[str, int],
    metric_fn: Callable[[dict[str, int]], dict[str, float]],
    n_boot: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> dict[str, tuple[float, float]]:
    """Percentile bootstrap CI of every metric returned by `metric_fn(cm)`."""
    import numpy as np

    cells = ("tp", "fp", "fn", "tn")
    n = sum(cm[c] for c in cells)
    if n == 0:
        return {}
    draws = np.random.default_rng(seed).multinomial(n, [cm[c] / n for c in cells], size=n_boot)
    samples = [metric_fn(dict(zip(cells, map(int, draw), strict=True))) for draw in draws]
    out: dict[str, tuple[float, float]] = {}
    for name in samples[0]:
        values = np.array([sample[name] for sample in samples])
        out[name] = (float(np.quantile(values, alpha / 2)), float(np.quantile(values, 1 - alpha / 2)))
    return out


def mcnemar_exact(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> float:
    """Two-sided exact p-value on the discordant pairs (b = A right / B wrong,
    c = A wrong / B right): 2 * P(X <= min(b, c)), X ~ Binomial(b + c, 0.5), capped at 1."""
    if len(correct_a) != len(correct_b):
        raise ValueError("mcnemar_exact needs paired results over the same windows")
    b = sum(1 for a, other in zip(correct_a, correct_b, strict=True) if a and not other)
    c = sum(1 for a, other in zip(correct_a, correct_b, strict=True) if other and not a)
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)
