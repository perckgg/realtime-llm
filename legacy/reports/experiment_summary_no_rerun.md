# Consolidated Experiment Summary Without Rerun

This summary is derived from existing experiment outputs and does not rerun the full LLM pipeline.

## 1. Scope

The summary reorganizes existing outputs into thesis-ready evidence for alert quality, contextual effectiveness, operational cost, operational risk, and real-time feasibility. No full benchmark was rerun, no external LLM API call was made, and no raw dataset was modified.

## 2. Dataset Roles

- Microsoft cloud-monitoring-dataset: useful for metric-only detector baselines because it provides labeled metric anomalies but lacks operational log/trace context.
- IntelligentDDS/Nezha: the main dataset for the hybrid experiment because it contains metrics, logs, traces, and fault injection labels.

## 3. Microsoft Cloud-monitoring Metric-only Baseline

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| detector_only | 49578 | 14686 | 0.1222 | 0.8077 | 0.2122 | 0.2722 | 0 | 0 | 0 | 0 | 0 | Metric-only detector baseline; RAG/API evaluation is intentionally not used for this dataset. |

The Microsoft dataset is used before the Nezha hybrid experiments as a metric-only feasibility benchmark. It quantifies detector recall and false-positive burden on labeled metric time series. Because it lacks real operational logs/traces and produces too many candidates for API judging, only detector-only results are used for this dataset.

## 4. Phase 3 Ablation

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| detector_only | 200 | 35 | 0.1714 | 0.375 | 0.2353 | 0.1576 | 0 |  |  | 0 | 0 | Baseline without LLM/RAG cost. |
| llm_without_rag | 200 | 35 | 0 | 0 | 0 | 0.0815 | 20 |  |  | 0 | 0.0077 | Reduces false positives but loses true positives without context. |
| hybrid | 200 | 35 | 0.25 | 0.375 | 0.3 | 0.0978 | 20 |  |  | 7.281 | 0.0093 | Hybrid RAG variant; compare quality with retrieval/context cost. |
| hybrid_no_gate | 200 | 35 | 0.25 | 0.375 | 0.3 | 0.0978 | 20 |  |  | 5.6047 | 0.0098 | Hybrid RAG variant; compare quality with retrieval/context cost. |

Phase 3 shows that `llm_without_rag` reduces false positives but loses all true positives in this slice. The hybrid variant keeps detector recall while improving precision and FPR, supporting the claim that LLM-as-a-Judge requires operational context.

## 5. Phase 4 Benchmark

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| detector_only | 300 | 40 | 0.15 | 0.375 | 0.2143 | 0.1197 | 0 | 0 | 0 | 0 | 0 | Baseline without LLM/RAG cost. |
| llm_without_rag | 300 | 40 | 0 | 0 | 0 | 0.0352 | 30 | 0 | 0 | 0 | 0.0069 |  |
| hybrid_local_top6 | 300 | 40 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 30 | 0.225 | 0.1667 | 6.4785 | 0.0091 | Hybrid RAG variant; compare quality with retrieval/context cost. |
| hybrid_bm25_top6 | 300 | 40 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 30 | 0.225 | 0.1667 | 11.1465 | 0.0094 | Hybrid RAG variant; compare quality with retrieval/context cost. |
| hybrid_bm25_top10 | 300 | 40 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 30 | 0.225 | 0.2733 | 10.3172 | 0.0106 | More context than top6 but no classification gain in this slice. |

Phase 4 shows that local hybrid RAG variants improve precision, F1, and FPR over detector-only. Increasing top-k from 6 to 10 increases average retrieved context but does not improve classification metrics in this slice.

## 6. Phase 5 Context Rescue

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| context_rescue | 300 | 55 | 0.64 | 1 | 0.7805 | 0.0317 | 55 | 0.4727 | 1.05 | 135.6469 | 0.0201 | Architectural improvement; not a single-variable ablation because rescue behavior and LLM calls changed. |

Context Rescue improves recall and F1 by promoting candidates from log/trace signals. It also increases candidate alerts and LLM calls, so it should be presented as an architectural improvement with a cost trade-off, not as a one-variable ablation.

## 7. Local-first and Fallback

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local_first_ollama_gemini | 45 | 19 | 0.625 | 1 | 0.7692 | 0.1714 | 6 | 0.8421 | 2.6667 | 91.6506 | 4585.012 | Operational feasibility smoke; not the main quality benchmark. |

The local-first smoke test demonstrates workflow feasibility. It preserves recall in this small slice but increases average LLM latency and still requires API fallback, so it should be interpreted as operational feasibility evidence.

## 8. Streaming Replay

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| streaming_hybrid | 50 | 9 | 0.5556 | 0.3333 | 0.4167 | 0.1143 | 9 |  |  | 0.8263 | 0.0198 | Sequential replay smoke; do not compare directly with Phase 4/5 due to different windows/backend. |

Streaming replay mainly verifies sequential processing and avoidance of future context leakage. It should not be compared directly with Phase 4/5 because the number of windows and backend settings differ.

## 9. Cost and Risk Summary

| variant | windows | candidates | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | retrieval_ms | avg_llm_ms | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini25_flash_lite_500w_budget_manual_review_cache_replay | 500 | 490 | 0.4563 | 0.47 | 0.4631 | 0.14 | 120 | 0.1306 | 0.776 | 30.9229 | 0.0605 | Cache replay using existing Gemini decisions; no new external API call. |

The 500-window cache replay shows that cache and budget-aware policy can reorganize existing LLM decisions without new API calls. It also shows why budget-exhausted candidates should be manual-reviewed instead of routed as confirmed alerts.

## 10. Final Interpretation

The strongest current result is that context improves alert validation, especially when Context Rescue uses log/trace evidence to reduce false-negative risk. The main trade-off is higher LLM usage and operational complexity. This positions the system as a cost-aware multi-telemetry AIOps pipeline for alert validation.

## 11. Limitations

- Results are based on existing slices and should not be overclaimed as production-ready.
- Some comparisons are not strict ablations because candidate generation, context retrieval, and LLM budget can change together.
- Real LLM behavior can be non-deterministic and subject to rate limits.
- Streaming replay is a feasibility smoke test, not a full real-time deployment benchmark.
