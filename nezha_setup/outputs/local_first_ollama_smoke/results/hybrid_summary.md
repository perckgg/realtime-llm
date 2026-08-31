# Experiment Summary: hybrid

| Metric | Value |
|---|---:|
| `precision` | 0.625 |
| `recall` | 1.0 |
| `f1` | 0.7692 |
| `false_positive_rate` | 0.1714 |
| `tp` | 10 |
| `fp` | 6 |
| `tn` | 29 |
| `fn` | 0 |
| `evaluated_windows` | 45 |
| `candidate_alerts` | 19 |
| `routed_alerts` | 16 |
| `alerts` | 19 |
| `llm_calls` | 6 |
| `llm_calls_avoided` | 39 |
| `llm_budget_exhausted` | 13 |
| `input_tokens` | 5386 |
| `output_tokens` | 1330 |
| `context_tokens` | 720 |
| `avg_retrieved_context_count` | 2.6667 |
| `avg_context_tokens` | 16.0 |
| `candidates_with_context` | 16 |
| `context_coverage_rate` | 0.8421 |
| `context_rescue_checked` | 41 |
| `context_rescue_promoted` | 15 |
| `api_fallback_calls` | 4 |
| `local_llm_valid_json` | 3 |
| `llm_providers` | ['gemini', 'ollama'] |
| `json_valid_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `avg_detector_latency_ms` | 10.9572 |
| `avg_retrieval_latency_ms` | 91.6506 |
| `avg_llm_latency_ms` | 4585.012 |
| `avg_end_to_end_latency_ms` | 6853.7818 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `hybrid_by_service.csv` |
| `by_fault_type` | see `hybrid_by_fault_type.csv` |
| `llm_cost_pricing_source` | not_configured |
| `estimated_input_cost_usd` | 0.0 |
| `estimated_output_cost_usd` | 0.0 |
| `estimated_llm_cost_usd` | 0.0 |
