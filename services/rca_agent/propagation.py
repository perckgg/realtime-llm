"""RCA task 2, level 1: backward 1-hop root-cause localisation (01 SS6.5). Pure algorithm, no LLM.

Level 2 (an LLM reasoning over the whole call chain) was cut (QD-037) and is not implemented.

Failures travel against the call direction: when `a` calls `b` (edge a -> b of the directed
service graph) and `b` is broken, `a` gets slow or fails. So from every alerted service of an
incident the rule looks one hop *down the call direction*:

1. `A` = the alerted services of the incident. A service is "abnormal" when it is in `A`
   (`sign = "alert"`), or when it is in `A` or the detector flagged one of its windows inside the
   incident's time span (`sign = "candidate"`; the caller passes those services in).
2. Every alerted service `s` blames its abnormal direct callees; with none, it blames itself.
   `s` casts one vote, split evenly over what it blames.
3. score(v) = votes(v) / |A|. Ranking: score (desc), then the service's highest anomaly score in
   the incident span (desc), then name. Alerted services that received no vote follow in the same
   order, so that Hit@3 can still find them.

Votes are counted per alerted *service*, never per alert, and are divided by |A|: a detector that
raises more candidates on another split (more alerts per service) does not change the ranking.

Baseline of H5 (registered at `be2b985`): "the service with the highest anomaly score in the
incident" -- `rank_by_anomaly_score`, over the incident's own alerts.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Literal

from packages.graph.service_graph import ServiceGraph

Sign = Literal["alert", "candidate"]
SIGNS: tuple[Sign, ...] = ("alert", "candidate")


@dataclass(frozen=True)
class RankedService:
    service: str
    score: float  # share of the alerted services' votes, in [0, 1]
    anomaly_score: float
    alerted: bool
    blamed_by: tuple[str, ...]  # alerted services whose vote reached this one


def rank_by_anomaly_score(alert_scores: Mapping[str, float]) -> list[str]:
    """Baseline: alerted services by their highest alert anomaly score (desc), then name."""
    return [s for s, _ in sorted(alert_scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def backward_one_hop(
    alerted: Collection[str],
    graph: ServiceGraph,
    anomaly_scores: Mapping[str, float],
    abnormal: Collection[str] = (),
) -> list[RankedService]:
    """`alerted`: services of the incident; `abnormal`: further services with an abnormal sign
    (empty for `sign = "alert"`); `anomaly_scores`: highest anomaly score per service in the
    incident span (missing = 0). Returns every voted service, then the unvoted alerted ones."""
    alerted_set = set(alerted)
    if not alerted_set:
        return []
    abnormal_set = alerted_set | set(abnormal)
    directed = graph.directed
    votes: dict[str, float] = {}
    blamed_by: dict[str, list[str]] = {}
    for service in sorted(alerted_set):
        callees = sorted(c for c in directed.successors(service) if c in abnormal_set) if service in directed else []
        targets = callees or [service]
        for target in targets:
            votes[target] = votes.get(target, 0.0) + 1.0 / len(targets)
            blamed_by.setdefault(target, []).append(service)
    ranked = [
        RankedService(
            service=s,
            score=votes.get(s, 0.0) / len(alerted_set),
            anomaly_score=float(anomaly_scores.get(s, 0.0)),
            alerted=s in alerted_set,
            blamed_by=tuple(blamed_by.get(s, ())),
        )
        for s in set(votes) | alerted_set
    ]
    return sorted(ranked, key=lambda r: (-round(r.score, 12), -r.anomaly_score, r.service))


def propagation_path(ranked: list[RankedService], graph: ServiceGraph) -> list[str]:
    """Root cause first, then the alerted services it explains (its direct callers that voted
    for it, then the other alerted services), i.e. the order in which the failure spreads."""
    if not ranked:
        return []
    root = ranked[0]
    path = [root.service]
    for service in root.blamed_by:
        if service not in path:
            path.append(service)
    for item in ranked[1:]:
        if item.alerted and item.service not in path:
            path.append(item.service)
    return path
