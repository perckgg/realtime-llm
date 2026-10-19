"""Service dependency graph from Nezha traces (02-data-and-experiment-protocol.md SS1.3).

Port of GD1's legacy/src/phase2/retrieval/graph_builder.py: for every span with
a parent span in the same trace file, add an edge parent service -> child
service (same-service links skipped); edge weight = number of such spans.
Like GD1, parents are looked up within one per-minute trace file only, and
every service seen in metrics or traces is a node (isolated ones included).
Services come from `packages.schemas.nezha.pod_to_service`, the same mapping
as TelemetryWindow.service (GD1 used its own suffix-stripping rule;
scripts/build_service_graph.py checks that both give the same edges).

Both views are kept (QD-021, V15): the **undirected** graph drives C1's
graph distance d_G (as in the paper), the **directed** call graph is for C3
(evidence on a call path to s0). Edges lighter than `min_edge_count` (02
SS1.3, default 5) are dropped; on Nezha the lightest edge has weight 126, so
nothing is dropped.

Built once (scripts/build_service_graph.py -> data/graph/service_graph.json),
loaded once per process, never rebuilt per window (R-B3).
"""

from __future__ import annotations

import csv
import json
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from packages.schemas.nezha import load_known_services, pod_to_service

GRAPH_PATH = Path(__file__).resolve().parents[2] / "data" / "graph" / "service_graph.json"


@dataclass
class _EdgeStats:
    spans: int = 0
    traces: set[str] = field(default_factory=set)
    durations_ms: list[float] = field(default_factory=list)


@dataclass
class ServiceGraph:
    directed: nx.DiGraph
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def undirected(self) -> nx.Graph:
        """Undirected view; an edge's weight is the sum over both directions (GD1)."""
        graph = nx.Graph()
        graph.add_nodes_from(self.directed.nodes)
        for a, b, data in self.directed.edges(data=True):
            weight = data.get("weight", 1) + (graph[a][b]["weight"] if graph.has_edge(a, b) else 0)
            graph.add_edge(a, b, weight=weight)
        return graph

    def distances(self, service: str, max_distance: int | None = None, directed: bool = False) -> dict[str, int]:
        """Shortest hop count from `service` to every reachable service ({} if unknown).
        Undirected by default (C1); `directed=True` follows call direction."""
        graph = self.directed if directed else self._undirected_cached()
        if service not in graph:
            return {}
        return dict(nx.single_source_shortest_path_length(graph, service, cutoff=max_distance))

    def _undirected_cached(self) -> nx.Graph:
        cached = getattr(self, "_undirected", None)
        if cached is None:
            cached = self.undirected
            object.__setattr__(self, "_undirected", cached)
        return cached

    def to_json(self) -> dict[str, Any]:
        return {
            "nodes": sorted(self.directed.nodes),
            "edges": [
                {"source": a, "target": b, **data}
                for a, b, data in sorted(self.directed.edges(data=True), key=lambda e: (-e[2]["weight"], e[0], e[1]))
            ],
            "summary": self.summary,
        }

    def save(self, path: Path = GRAPH_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_graph(path: Path = GRAPH_PATH) -> ServiceGraph:
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.DiGraph()
    graph.add_nodes_from(data["nodes"])
    for edge in data["edges"]:
        attrs = {k: v for k, v in edge.items() if k not in {"source", "target"}}
        graph.add_edge(edge["source"], edge["target"], **attrs)
    return ServiceGraph(graph, data.get("summary", {}))


def load_gd1_graph(path: Path) -> ServiceGraph:
    """GD1's legacy/outputs/phase2/service_graph_directed.json (parity runs)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.DiGraph()
    graph.add_nodes_from(node["id"] for node in data["nodes"])
    for edge in data["edges"]:
        graph.add_edge(edge["source_service"], edge["target_service"], weight=int(edge["weight"]))
    return ServiceGraph(graph, {"source": str(path)})


def _trace_files(root: Path) -> Iterable[Path]:
    for subdir in ("rca_data", "construct_data"):
        yield from sorted((root / subdir).glob("*/trace/*_trace.csv"))


def build_service_graph(
    root: Path, extra_services: Iterable[str] = (), min_edge_count: int = 5
) -> ServiceGraph:
    """Build the graph from every trace file under `root` (rca_data + construct_data)."""
    known = load_known_services(root)
    service_of: dict[str, str] = {}

    def service(pod: str) -> str:
        if pod not in service_of:
            service_of[pod] = pod_to_service(pod, known)[0]
        return service_of[pod]

    nodes: set[str] = set(extra_services)
    edges: dict[tuple[str, str], _EdgeStats] = {}
    counts = {"trace_files": 0, "spans": 0, "parent_links": 0, "same_service_links": 0, "root_spans": 0}
    for path in _trace_files(root):
        counts["trace_files"] += 1
        spans: dict[str, tuple[str, str]] = {}  # span_id -> (service, trace_id)
        children: list[tuple[str, str, str, float]] = []  # (parent_id, service, trace_id, duration_ms)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                trace_id, span_id, parent_id = raw.get("TraceID"), raw.get("SpanID"), raw.get("ParentID")
                if not (trace_id and span_id and parent_id):
                    continue
                try:
                    duration = max(0.0, (int(raw["EndTimeUnixNano"]) - int(raw["StartTimeUnixNano"])) / 1e6)
                except (KeyError, ValueError):
                    continue
                svc = service(raw.get("PodName") or "unknown")
                counts["spans"] += 1
                nodes.add(svc)
                spans[span_id] = (svc, trace_id)
                children.append((parent_id, svc, trace_id, duration))
        for parent_id, child_service, trace_id, duration in children:
            if parent_id.lower() == "root":
                counts["root_spans"] += 1
                continue
            parent = spans.get(parent_id)
            if parent is None:
                continue
            counts["parent_links"] += 1
            if parent[0] == child_service:
                counts["same_service_links"] += 1
                continue
            stats = edges.setdefault((parent[0], child_service), _EdgeStats())
            stats.spans += 1
            stats.traces.add(trace_id)
            stats.durations_ms.append(duration)

    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    dropped = 0
    for (a, b), stats in edges.items():
        if stats.spans < min_edge_count:
            dropped += 1
            continue
        graph.add_edge(
            a,
            b,
            weight=stats.spans,
            trace_count=len(stats.traces),
            avg_duration_ms=round(statistics.fmean(stats.durations_ms), 3),
        )
    result = ServiceGraph(graph)
    undirected = result.undirected
    isolated = sorted(n for n in undirected.nodes if undirected.degree(n) == 0)
    n = graph.number_of_nodes()
    result.summary = {
        **counts,
        "min_edge_count": min_edge_count,
        "edges_dropped_below_min": dropped,
        "service_count": n,
        "directed_edge_count": graph.number_of_edges(),
        "undirected_edge_count": undirected.number_of_edges(),
        "edge_density_directed": graph.number_of_edges() / (n * (n - 1)) if n > 1 else 0.0,
        "isolated_services": isolated,
        "connected_components": nx.number_connected_components(undirected),
        "largest_component_size": max((len(c) for c in nx.connected_components(undirected)), default=0),
    }
    return result
