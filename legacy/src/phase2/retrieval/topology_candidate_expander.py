from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.models import AlertCandidate
from src.retrieval.context_store import LocalContextStore, StoredContext
from src.time_utils import parse_timestamp


@dataclass(frozen=True)
class GraphCandidate:
    context: StoredContext
    graph_distance: int | None
    source: str


class ServiceTopology:
    def __init__(self, adjacency: dict[str, dict[str, float]]) -> None:
        self.adjacency = adjacency

    @classmethod
    def from_undirected_json(cls, path: Path) -> "ServiceTopology":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        adjacency: dict[str, dict[str, float]] = {}
        for node in data.get("nodes", []):
            node_id = str(node.get("id") or "")
            if node_id:
                adjacency.setdefault(node_id, {})
        for service, neighbors in data.get("adjacency", {}).items():
            service_id = str(service)
            adjacency.setdefault(service_id, {})
            for neighbor in neighbors:
                neighbor_id = str(neighbor.get("service") or "")
                if not neighbor_id:
                    continue
                adjacency.setdefault(neighbor_id, {})
                adjacency[service_id][neighbor_id] = float(neighbor.get("weight") or 1.0)
        return cls(adjacency)

    def shortest_distances(self, service_id: str, max_distance: int | None = None) -> dict[str, int]:
        if not service_id or service_id not in self.adjacency:
            return {}
        distances = {service_id: 0}
        queue = deque([service_id])
        while queue:
            current = queue.popleft()
            current_distance = distances[current]
            if max_distance is not None and current_distance >= max_distance:
                continue
            for neighbor in sorted(self.adjacency.get(current, {})):
                if neighbor in distances:
                    continue
                distances[neighbor] = current_distance + 1
                queue.append(neighbor)
        return distances


class TopologyCandidateExpander:
    def __init__(
        self,
        topology: ServiceTopology,
        max_graph_distance: int = 2,
        time_margin_minutes: int = 5,
        per_service_limit: int = 20,
    ) -> None:
        self.topology = topology
        self.max_graph_distance = max_graph_distance
        self.time_margin = timedelta(minutes=time_margin_minutes)
        self.per_service_limit = per_service_limit

    def expand(self, alert: AlertCandidate, store: LocalContextStore) -> list[GraphCandidate]:
        distances = self.topology.shortest_distances(alert.service_id, self.max_graph_distance)
        if not distances:
            return []

        start = parse_timestamp(alert.time_window["start"]) - self.time_margin
        end = parse_timestamp(alert.time_window["end"]) + self.time_margin
        by_service: dict[str, list[StoredContext]] = {service: [] for service in distances}

        for item in store.items:
            service = item.event.service_id
            if service not in distances:
                continue
            if not (start <= item.event.timestamp <= end):
                continue
            by_service[service].append(item)

        alert_time = alert_reference_time(alert)
        candidates: list[GraphCandidate] = []
        for service, items in by_service.items():
            ranked = sorted(
                items,
                key=lambda item: (
                    abs((item.event.timestamp - alert_time).total_seconds()),
                    item.event.doc_id,
                ),
            )
            for item in ranked[: self.per_service_limit]:
                candidates.append(
                    GraphCandidate(
                        context=item,
                        graph_distance=distances[service],
                        source="graph",
                    )
                )
        candidates.sort(
            key=lambda candidate: (
                candidate.graph_distance if candidate.graph_distance is not None else 10**9,
                abs((candidate.context.event.timestamp - alert_time).total_seconds()),
                candidate.context.event.doc_id,
            )
        )
        return candidates


def alert_reference_time(alert: AlertCandidate) -> datetime:
    start = parse_timestamp(alert.time_window["start"])
    end = parse_timestamp(alert.time_window["end"])
    return start + ((end - start) / 2)


def graph_distance_for_service(topology: ServiceTopology, alert_service: str, context_service: str) -> int | None:
    return topology.shortest_distances(alert_service).get(context_service)


def graph_sim(distance: int | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + distance)
