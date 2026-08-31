from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.time_utils import isoformat


@dataclass
class TraceSpan:
    trace_id: str
    span_id: str
    parent_id: str
    service_id: str
    pod_id: str
    operation: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    source_file: str


@dataclass
class EdgeStats:
    source_service: str
    target_service: str
    span_count: int = 0
    trace_ids: set[str] = field(default_factory=set)
    durations_ms: list[float] = field(default_factory=list)
    operations: Counter[str] = field(default_factory=Counter)
    source_files: Counter[str] = field(default_factory=Counter)
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    def add(self, child: TraceSpan) -> None:
        self.span_count += 1
        self.trace_ids.add(child.trace_id)
        if math.isfinite(child.duration_ms):
            self.durations_ms.append(child.duration_ms)
        if child.operation:
            self.operations[child.operation] += 1
        self.source_files[child.source_file] += 1
        if self.first_seen is None or child.start_time < self.first_seen:
            self.first_seen = child.start_time
        if self.last_seen is None or child.end_time > self.last_seen:
            self.last_seen = child.end_time

    def to_row(self) -> dict[str, Any]:
        durations = sorted(self.durations_ms)
        avg_duration_ms = statistics.fmean(durations) if durations else 0.0
        p95_duration_ms = percentile(durations, 0.95) if durations else 0.0
        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "weight": self.span_count,
            "trace_count": len(self.trace_ids),
            "span_count": self.span_count,
            "avg_duration_ms": round(avg_duration_ms, 3),
            "p95_duration_ms": round(p95_duration_ms, 3),
            "first_seen": isoformat(self.first_seen) if self.first_seen else "",
            "last_seen": isoformat(self.last_seen) if self.last_seen else "",
            "sample_operations": ";".join(op for op, _ in self.operations.most_common(5)),
            "source_files": ";".join(path for path, _ in self.source_files.most_common(5)),
        }


@dataclass
class ServiceGraph:
    nodes: set[str]
    edges: dict[tuple[str, str], EdgeStats]
    summary: dict[str, Any]

    def sorted_edges(self) -> list[EdgeStats]:
        return sorted(
            self.edges.values(),
            key=lambda edge: (-edge.span_count, edge.source_service, edge.target_service),
        )


def build_service_graph(
    dataset_root: Path,
    processed_metrics_path: Path | None = None,
    processed_logs_path: Path | None = None,
) -> ServiceGraph:
    nodes = set()
    nodes.update(read_services_from_metrics(processed_metrics_path))
    nodes.update(read_services_from_logs(processed_logs_path))

    edges: dict[tuple[str, str], EdgeStats] = {}
    trace_file_count = 0
    trace_row_count = 0
    parent_link_count = 0
    same_service_parent_links = 0
    root_span_count = 0
    malformed_span_count = 0
    trace_ids: set[str] = set()

    for trace_path in iter_trace_files(dataset_root):
        trace_file_count += 1
        spans: dict[str, TraceSpan] = {}
        children: list[TraceSpan] = []
        with trace_path.open("r", encoding="utf-8-sig", newline="") as f:
            for raw in csv.DictReader(f):
                trace_row_count += 1
                span = parse_trace_span(raw, trace_path, dataset_root)
                if span is None:
                    malformed_span_count += 1
                    continue
                nodes.add(span.service_id)
                trace_ids.add(span.trace_id)
                spans[span.span_id] = span
                children.append(span)

        for child in children:
            if child.parent_id.lower() == "root":
                root_span_count += 1
                continue
            parent = spans.get(child.parent_id)
            if parent is None:
                continue
            parent_link_count += 1
            nodes.add(parent.service_id)
            if parent.service_id == child.service_id:
                same_service_parent_links += 1
                continue
            key = (parent.service_id, child.service_id)
            edge = edges.get(key)
            if edge is None:
                edge = EdgeStats(source_service=parent.service_id, target_service=child.service_id)
                edges[key] = edge
            edge.add(child)

    undirected_edges = make_undirected_edges(edges)
    connected_components = compute_connected_components(nodes, undirected_edges)
    summary = {
        "dataset_root": display_path(dataset_root),
        "trace_files": trace_file_count,
        "trace_rows": trace_row_count,
        "malformed_trace_rows": malformed_span_count,
        "trace_count": len(trace_ids),
        "service_count": len(nodes),
        "directed_edge_count": len(edges),
        "undirected_edge_count": len(undirected_edges),
        "parent_link_count": parent_link_count,
        "cross_service_parent_link_count": sum(edge.span_count for edge in edges.values()),
        "same_service_parent_link_count": same_service_parent_links,
        "root_span_count": root_span_count,
        "isolated_service_count": len(isolated_services(nodes, undirected_edges)),
        "isolated_services": isolated_services(nodes, undirected_edges),
        "connected_component_count": len(connected_components),
        "largest_component_size": max((len(component) for component in connected_components), default=0),
        "top_directed_edges": [edge.to_row() for edge in ServiceGraph(nodes, edges, {}).sorted_edges()[:10]],
    }
    return ServiceGraph(nodes=nodes, edges=edges, summary=summary)


def iter_trace_files(dataset_root: Path) -> Iterable[Path]:
    for subdir in ("rca_data", "construct_data"):
        root = dataset_root / subdir
        if not root.exists():
            continue
        yield from sorted(root.glob("*\\trace\\*_trace.csv"))


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def parse_trace_span(raw: dict[str, str], trace_path: Path, dataset_root: Path) -> TraceSpan | None:
    try:
        start_ns = int(raw["StartTimeUnixNano"])
        end_ns = int(raw["EndTimeUnixNano"])
        start_time = datetime.fromtimestamp(start_ns / 1_000_000_000, tz=timezone.utc)
        end_time = datetime.fromtimestamp(end_ns / 1_000_000_000, tz=timezone.utc)
        pod_id = raw.get("PodName") or "unknown"
        span = TraceSpan(
            trace_id=str(raw.get("TraceID") or ""),
            span_id=str(raw.get("SpanID") or ""),
            parent_id=str(raw.get("ParentID") or ""),
            service_id=service_from_pod(pod_id),
            pod_id=pod_id,
            operation=str(raw.get("OperationName") or "unknown"),
            start_time=start_time,
            end_time=end_time,
            duration_ms=max(0.0, (end_ns - start_ns) / 1_000_000),
            source_file=str(trace_path.relative_to(dataset_root)).replace("\\", "/"),
        )
    except (KeyError, ValueError, OSError):
        return None
    if not span.trace_id or not span.span_id or not span.parent_id:
        return None
    return span


def service_from_pod(pod_id: str) -> str:
    parts = pod_id.split("-")
    if len(parts) >= 3 and is_replica_hash(parts[-2]) and is_pod_suffix(parts[-1]):
        return "-".join(parts[:-2])
    if len(parts) >= 2 and is_pod_suffix(parts[-1]):
        return "-".join(parts[:-1])
    return pod_id


def is_replica_hash(value: str) -> bool:
    return len(value) >= 5 and all(char.isalnum() for char in value)


def is_pod_suffix(value: str) -> bool:
    return 4 <= len(value) <= 6 and all(char.isalnum() for char in value)


def read_services_from_metrics(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    services = set()
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            service = row.get("service_id")
            if service:
                services.add(service)
    return services


def read_services_from_logs(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    services = set()
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            service = row.get("service_id")
            if service:
                services.add(str(service))
    return services


def make_undirected_edges(edges: dict[tuple[str, str], EdgeStats]) -> dict[tuple[str, str], dict[str, Any]]:
    combined: dict[tuple[str, str], dict[str, Any]] = {}
    for (source, target), edge in edges.items():
        key = tuple(sorted((source, target)))
        item = combined.setdefault(
            key,
            {
                "service_a": key[0],
                "service_b": key[1],
                "weight": 0,
                "directed_edges": [],
            },
        )
        item["weight"] += edge.span_count
        item["directed_edges"].append(
            {
                "source_service": source,
                "target_service": target,
                "weight": edge.span_count,
                "trace_count": len(edge.trace_ids),
            }
        )
    return combined


def graph_adjacency(nodes: set[str], undirected_edges: dict[tuple[str, str], dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {node: [] for node in sorted(nodes)}
    for (service_a, service_b), edge in undirected_edges.items():
        adjacency[service_a].append({"service": service_b, "weight": edge["weight"]})
        adjacency[service_b].append({"service": service_a, "weight": edge["weight"]})
    for neighbors in adjacency.values():
        neighbors.sort(key=lambda item: (-item["weight"], item["service"]))
    return adjacency


def isolated_services(nodes: set[str], undirected_edges: dict[tuple[str, str], dict[str, Any]]) -> list[str]:
    connected = set()
    for source, target in undirected_edges:
        connected.add(source)
        connected.add(target)
    return sorted(nodes - connected)


def compute_connected_components(
    nodes: set[str], undirected_edges: dict[tuple[str, str], dict[str, Any]]
) -> list[list[str]]:
    adjacency = {node: set() for node in nodes}
    for source, target in undirected_edges:
        adjacency[source].add(target)
        adjacency[target].add(source)

    seen = set()
    components = []
    for node in sorted(nodes):
        if node in seen:
            continue
        queue = deque([node])
        seen.add(node)
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))
    components.sort(key=lambda component: (-len(component), component[0] if component else ""))
    return components


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    index = (len(values) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[int(index)]
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def write_graph_outputs(graph: ServiceGraph, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_edges_csv(output_dir / "service_graph_edges.csv", graph.sorted_edges())

    directed = {
        "nodes": [{"id": node} for node in sorted(graph.nodes)],
        "edges": [edge.to_row() for edge in graph.sorted_edges()],
    }
    write_json(output_dir / "service_graph_directed.json", directed)

    undirected_edges = make_undirected_edges(graph.edges)
    undirected = {
        "nodes": [{"id": node} for node in sorted(graph.nodes)],
        "edges": sorted(undirected_edges.values(), key=lambda item: (-item["weight"], item["service_a"], item["service_b"])),
        "adjacency": graph_adjacency(graph.nodes, undirected_edges),
    }
    write_json(output_dir / "service_graph_undirected.json", undirected)
    write_json(output_dir / "service_graph_summary.json", graph.summary)


def write_edges_csv(path: Path, edges: list[EdgeStats]) -> None:
    fieldnames = [
        "source_service",
        "target_service",
        "weight",
        "trace_count",
        "span_count",
        "avg_duration_ms",
        "p95_duration_ms",
        "first_seen",
        "last_seen",
        "sample_operations",
        "source_files",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for edge in edges:
            writer.writerow(edge.to_row())


def write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
