"""RCA task 1: group confirmed alerts into incidents (01 SS6.5). Pure algorithm, no LLM.

1. Sort the alerts by time and cut where two consecutive alerts are more than
   `t_group_seconds` apart (single-linkage sliding window).
2. Inside each time cluster, take the subgraph of the service dependency graph
   induced by the alerted services (undirected: a call in either direction links them).
3. Each connected component is one Incident. Alerts of the same service always share
   one; a service missing from the graph forms its own.

`t_group_seconds` comes from the caller's config (01 SS6.5 default: 300 s).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import networkx as nx

from packages.graph.service_graph import ServiceGraph
from packages.schemas.models import Incident, JudgedAlert


def time_clusters(alerts: Sequence[JudgedAlert], t_group_seconds: float) -> list[list[JudgedAlert]]:
    if t_group_seconds < 0:
        raise ValueError("t_group_seconds must be >= 0")
    ordered = sorted(alerts, key=lambda a: (a.ts, a.alert_id))
    clusters: list[list[JudgedAlert]] = []
    for alert in ordered:
        if clusters and (alert.ts - clusters[-1][-1].ts).total_seconds() <= t_group_seconds:
            clusters[-1].append(alert)
        else:
            clusters.append([alert])
    return clusters


def _incident_id(run_id: str, alert_ids: Sequence[str]) -> str:
    digest = hashlib.sha256("\n".join([run_id, *alert_ids]).encode("utf-8")).hexdigest()
    return f"inc-{digest[:16]}"


def group_alerts(
    alerts: Sequence[JudgedAlert], graph: ServiceGraph, run_id: str, t_group_seconds: float
) -> list[Incident]:
    """Incidents ordered by start time; inside one, alerts and services are sorted."""
    undirected = graph.undirected
    incidents: list[Incident] = []
    for cluster in time_clusters(alerts, t_group_seconds):
        services = {a.service for a in cluster}
        sub = nx.Graph()
        sub.add_nodes_from(services)
        sub.add_edges_from(undirected.subgraph(services & set(undirected.nodes)).edges)
        for component in sorted(nx.connected_components(sub), key=lambda c: min(c)):
            members = sorted((a for a in cluster if a.service in component), key=lambda a: (a.ts, a.alert_id))
            alert_ids = [a.alert_id for a in members]
            edges = sorted(tuple(sorted(e)) for e in sub.subgraph(component).edges)
            incidents.append(
                Incident(
                    incident_id=_incident_id(run_id, alert_ids),
                    run_id=run_id,
                    alert_ids=alert_ids,
                    services=sorted(component),
                    start_ts=members[0].ts,
                    end_ts=members[-1].ts,
                    grouping_reason={"temporal_window_sec": t_group_seconds, "graph_edges_used": [list(e) for e in edges]},
                )
            )
    return sorted(incidents, key=lambda i: (i.start_ts, i.incident_id))
