# Step 7 View B Architecture-level Report

- Frozen split: `paper_500` (500 windows)
- Window hash: `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`
- LLM: `gemini/gemini-2.5-flash-lite`
- Budget: `operational_budget_120` (`120` calls)
- Scope: Architecture-level comparison. Context Rescue changes candidate promotion and is not a retrieval-only baseline.

| Method | Architecture enhanced | Precision | Recall | F1 | FPR | FP reduction | Manual review | Context coverage | LLM calls | API calls | Cache hits | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Detector-only | False | 0.2004 | 0.98 | 0.3328 | 0.9775 | 0.0 | 0.0 | 0.0 | 0 | 0 | 0 | 0.0 |
| LLM without RAG | False | 0.521 | 0.62 | 0.5662 | 0.1425 | 0.8542 | 0.74 | 0.0 | 120 | 120 | 0 | 0.0088813 |
| BM25 RAG top-6 | False | 1.0 | 0.34 | 0.5075 | 0.0 | 1.0 | 0.886 | 0.1125 | 120 | 120 | 0 | 0.0214684 |
| Topology-Aware Fusion top-6 | False | 0.5823 | 0.46 | 0.514 | 0.0825 | 0.9156 | 0.768 | 0.2454 | 120 | 120 | 0 | 0.0401765 |
| Context Rescue [architecture-enhanced] | True | 1.0 | 0.34 | 0.5075 | 0.0 | 1.0 | 0.886 | 0.1125 | 120 | 0 | 120 | 0.0214684 |

Context Rescue is architecture-enhanced because it changes candidate promotion before LLM validation.
Manual review is treated as abstention and is never counted as `route_alert`.
