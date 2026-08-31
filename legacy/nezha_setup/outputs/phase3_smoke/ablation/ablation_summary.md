# Ablation Study Summary

| Variant | Windows | Candidates | Precision | Recall | F1 | FPR | FP Reduction | LLM Calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| detector_only | 200 | 35 | 0.1714 | 0.375 | 0.2353 | 0.1576 | 0.0 | 0 |
| llm_without_rag | 200 | 35 | 0.0 | 0.0 | 0.0 | 0.0815 | 0.4828 | 20 |
| hybrid | 200 | 35 | 0.25 | 0.375 | 0.3 | 0.0978 | 0.3793 | 20 |
| hybrid_no_gate | 200 | 35 | 0.25 | 0.375 | 0.3 | 0.0978 | 0.3793 | 20 |
