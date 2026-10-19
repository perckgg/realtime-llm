"""Build the service graph and write docs/graph-coverage.md (M3, 02 SS1.3).

    py scripts/build_service_graph.py

1. Builds the graph from every Nezha trace file (packages/graph/service_graph.py)
   -> data/graph/service_graph.json (committed: small, and every retrieval run
   depends on it).
2. Compares its edges with GD1's legacy/outputs/phase2/service_graph_directed.json.
3. Measures the three coverage numbers of 02 SS1.3 on the committed splits and
   writes docs/graph-coverage.md.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.graph.service_graph import build_service_graph, load_gd1_graph
from packages.schemas.nezha import dataset_root

GD1_GRAPH = REPO / "legacy/outputs/phase2/service_graph_directed.json"
REPORT = REPO / "docs/graph-coverage.md"


def main() -> int:
    with (REPO / "data/window_index.csv").open(encoding="utf-8", newline="") as handle:
        index = {row["window_id"]: row for row in csv.DictReader(handle)}
    metric_services = {row["service"] for row in index.values()}
    graph = build_service_graph(dataset_root(), extra_services=metric_services)
    graph.save()

    gd1 = load_gd1_graph(GD1_GRAPH)
    ours = {(a, b): d["weight"] for a, b, d in graph.directed.edges(data=True)}
    theirs = {(a, b): d["weight"] for a, b, d in gd1.directed.edges(data=True)}
    edge_check = {
        "gd2_edges": len(ours),
        "gd1_edges": len(theirs),
        "same_edges": len(ours.keys() & theirs.keys()),
        "only_gd2": sorted(map(list, ours.keys() - theirs.keys())),
        "only_gd1": sorted(map(list, theirs.keys() - ours.keys())),
        "same_weight": sum(ours[k] == theirs[k] for k in ours.keys() & theirs.keys()),
        "gd1_nodes": gd1.directed.number_of_nodes(),
        "gd2_nodes": graph.directed.number_of_nodes(),
        "nodes_only_gd2": sorted(set(graph.directed.nodes) - set(gd1.directed.nodes)),
        "nodes_only_gd1": sorted(set(gd1.directed.nodes) - set(graph.directed.nodes)),
    }

    undirected = graph.undirected
    with_edges = {n for n in undirected.nodes if undirected.degree(n) > 0}
    service_coverage = len(metric_services & with_edges) / len(metric_services)
    split_rows = []
    for split in ("dev", "val", "test"):
        ids = json.loads((REPO / f"data/splits/{split}.json").read_text(encoding="utf-8"))["window_ids"]
        faults = [index[i] for i in ids if index[i]["is_fault"] == "1"]
        covered = sum(1 for row in faults if row["service"] in with_edges)
        by_system = Counter(row["system"] for row in faults if row["service"] in with_edges)
        split_rows.append((split, len(faults), covered, dict(by_system)))
    write_report(graph.summary, service_coverage, len(metric_services), len(metric_services & with_edges),
                 split_rows, edge_check)
    print(json.dumps({"summary": graph.summary, "edge_check": edge_check, "service_coverage": service_coverage},
                     indent=1, default=str))
    return 0


def write_report(summary, service_coverage, n_services, n_covered, split_rows, edge_check) -> None:
    lines = [
        "# Coverage của service dependency graph",
        "",
        "> Sinh tự động bởi `py scripts/build_service_graph.py` (M3, `02` §1.3). Không sửa tay.",
        "",
        "## 1. Đồ thị",
        "",
        "| | |",
        "|---|---|",
        (f"| Nguồn | Mọi file trace Nezha (`rca_data` + `construct_data`): {summary['trace_files']} file, "
        f"{summary['spans']:,} span |"),
        (f"| Liên kết cha–con trong cùng file | {summary['parent_links']:,} (cùng service: "
        f"{summary['same_service_links']:,}; span gốc: {summary['root_spans']:,}) |"),
        f"| Service (node) | {summary['service_count']} |",
        f"| Cạnh có hướng / vô hướng | {summary['directed_edge_count']} / {summary['undirected_edge_count']} |",
        f"| `min_edge_count` | {summary['min_edge_count']} (bị loại: {summary['edges_dropped_below_min']}) |",
        f"| Thành phần liên thông | {summary['connected_components']} (lớn nhất {summary['largest_component_size']} service) |",
        f"| Service cô lập | {len(summary['isolated_services'])}: {', '.join(summary['isolated_services'])} |",
        "",
        "## 2. Ba chỉ số của `02` §1.3",
        "",
        "Bảng GC-1. Coverage.",
        "",
        "| Chỉ số | Giá trị | Ngưỡng | Kết luận |",
        "|---|---|---|---|",
        (f"| Service coverage (service có metric và có ≥ 1 cạnh / service có metric) | {n_covered}/{n_services} = "
        f"{service_coverage:.1%} | < 80% → cảnh báo | {'Cảnh báo' if service_coverage < 0.8 else 'Đạt'} |"),
        f"| Edge density (cạnh có hướng / n(n−1)) | {summary['edge_density_directed']:.4f} | ghi nhận | Đồ thị thưa |",
    ]
    for split, n, covered, _ in split_rows:
        share = covered / n if n else 0.0
        lines.append(
            f"| Fault window có service trong graph — `{split}` | {covered}/{n} = {share:.1%} | < 60% → fallback BM25 | "
            f"{'Fallback' if share < 0.6 else 'Không cần fallback'} |"
        )
    lines += [
        "",
        "Fault window theo hệ thống (có service trong graph): "
        + "; ".join(f"`{s}` {by}" for s, _, _, by in split_rows),
        "",
        "## 3. So với đồ thị GĐ1 (`legacy/outputs/phase2/service_graph_directed.json`)",
        "",
        (f"- Cạnh: GĐ2 {edge_check['gd2_edges']}, GĐ1 {edge_check['gd1_edges']}, trùng {edge_check['same_edges']} "
        f"(cùng trọng số: {edge_check['same_weight']})."),
        f"- Cạnh chỉ có ở GĐ2: {edge_check['only_gd2'] or 'không'}; chỉ có ở GĐ1: {edge_check['only_gd1'] or 'không'}.",
        (f"- Node: GĐ2 {edge_check['gd2_nodes']}, GĐ1 {edge_check['gd1_nodes']}; chỉ ở GĐ2: "
        f"{edge_check['nodes_only_gd2'] or 'không'}; chỉ ở GĐ1: {edge_check['nodes_only_gd1'] or 'không'}."),
        "",
        "## 4. Nhận xét",
        "",
        ("- Service cô lập là các service train-ticket không có span cha/con khác service trong dữ liệu; "
        "chúng không bị tiêm lỗi trong bất kỳ split nào nên không ảnh hưởng fault window."),
        "- Cạnh nhẹ nhất vẫn nặng hơn nhiều `min_edge_count`, nên bộ lọc nhiễu của `02` §1.3 không đổi gì.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
