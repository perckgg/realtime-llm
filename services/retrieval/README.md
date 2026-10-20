# services/retrieval

**Làm gì.** Lấy bằng chứng (log/trace) cho một `AlertCandidate` theo `RetrievalStrategy`
(`01` §5.3). Sau QĐ-011 chỉ còn hai strategy:

| Strategy | File | Mốc | Trạng thái |
|---|---|---|---|
| `bm25_hybrid` — baseline, port GĐ1 | `bm25_hybrid.py` | M1 | Xong (QĐ-016) |
| `hybrid_bm25_graph` — C1 Fusion Score topology | `hybrid_bm25_graph.py` | M3 | Xong (QĐ-021); cờ `bm25_pool` = `global` (paper, parity) / `window` (GĐ2) |
| `none` — LLM-không-RAG (baseline H0, không phải phương pháp retrieval) | `no_retrieval.py` | M4 | Xong (QĐ-026); prompt trùng prompt của candidate có retrieval rỗng ⇒ chung cache |

`registry.py` — `build_strategy(config["retrieval"], store)` và `build_budget(...)`. Thêm
strategy = cập nhật registry + `01` §6.3 + bảng `debug` ở `03` §1.3 (R-F1).

**Chạy thế nào.**

```python
from packages.schemas.evidence import NezhaEvidenceStore
from services.retrieval.registry import build_budget, build_strategy

cfg = {"type": "bm25_hybrid", "top_k": 6, "params": {}}
result = build_strategy(cfg, NezhaEvidenceStore()).retrieve(candidate, build_budget(cfg))
```

`pool="window"` (mặc định): bằng chứng của `s_0` trong ±8 phút từ kho Nezha đầy đủ.
`pool="global"` + `extra_query_terms`: đúng hành vi GĐ1 trên corpus GĐ1, chỉ cho cổng
chặn (`scripts/check_gd1_parity.py`).

**Input/Output.** `AlertCandidate` + `RetrievalBudget` → `RetrievalResult` (`events:
list[ContextEvent]`, `debug` ghi truy vấn, kích thước pool; mỗi event ghi rank và điểm
thành phần). Test: `tests/test_bm25_hybrid.py`.
