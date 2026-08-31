# Phase 4 Benchmark Summary

| Variant | Windows | Candidates | Precision | Recall | F1 | FPR | FP Reduction | LLM Calls | Context Coverage | Avg Ctx | Retrieval ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| detector_only | 300 | 40 | 0.15 | 0.375 | 0.2143 | 0.1197 | 0.0 | 0 | 0.0 | 0.0 | 0.0 |
| llm_without_rag | 300 | 40 | 0.0 | 0.0 | 0.0 | 0.0352 | 0.7059 | 30 | 0.0 | 0.0 | 0.0 |
| hybrid_local_top6 | 300 | 40 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.225 | 0.1667 | 6.4785 |
| hybrid_bm25_top6 | 300 | 40 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.225 | 0.1667 | 11.1465 |
| hybrid_bm25_top10 | 300 | 40 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 0.6176 | 30 | 0.225 | 0.2733 | 10.3172 |
