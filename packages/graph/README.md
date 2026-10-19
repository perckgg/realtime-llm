# packages/graph

**Làm gì.** Service dependency graph dựng từ trace Nezha (NetworkX), port
`legacy/src/phase2/retrieval/graph_builder.py` (`02` §1.3). Giữ cả đồ thị có hướng (đường gọi,
cho C3) và vô hướng (khoảng cách d_G cho C1) — QĐ-021, V15. Dựng một lần, nạp một lần, không
dựng lại theo cửa sổ (R-B3).

**Chạy thế nào.**

```bash
py scripts/build_service_graph.py   # -> data/graph/service_graph.json (commit) + docs/graph-coverage.md
```

```python
from packages.graph.service_graph import load_graph
graph = load_graph()
graph.distances("cartservice", max_distance=2)       # vô hướng (C1)
graph.distances("frontend", directed=True)            # theo chiều gọi (C3)
```

**Input/Output.** Trace CSV của `rca_data` + `construct_data` → `ServiceGraph` (56 service,
68 cạnh, trùng GĐ1). `load_gd1_graph()` đọc đồ thị của GĐ1 cho chế độ parity. Test:
`tests/test_hybrid_bm25_graph.py`.
