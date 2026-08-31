# Experiment Summary: local_llama_gemini_lite_1p1n

| Metric | Value |
|---|---:|
| `precision` | 0.5 |
| `recall` | 1.0 |
| `f1` | 0.6667 |
| `false_positive_rate` | 1.0 |
| `tp` | 1 |
| `fp` | 1 |
| `tn` | 0 |
| `fn` | 0 |
| `evaluated_windows` | 2 |
| `candidate_alerts` | 2 |
| `routed_alerts` | 2 |
| `alerts` | 2 |
| `llm_calls` | 2 |
| `llm_calls_avoided` | 0 |
| `llm_budget_exhausted` | 0 |
| `input_tokens` | 210 |
| `output_tokens` | 0 |
| `context_tokens` | 38 |
| `avg_retrieved_context_count` | 3.0 |
| `avg_context_tokens` | 19.0 |
| `candidates_with_context` | 1 |
| `context_coverage_rate` | 0.5 |
| `context_rescue_checked` | 0 |
| `context_rescue_promoted` | 0 |
| `api_fallback_calls` | 2 |
| `model_fallback_calls` | 2 |
| `local_llm_valid_json` | 2 |
| `llm_providers` | ['gemini'] |
| `primary_local_models` | ['ollama:llama3.2:3b'] |
| `fallback_models` | ['gemini:gemini-2.5-flash-lite'] |
| `llm_cache_hits` | 0 |
| `actual_api_calls` | 2 |
| `llm_retry_count` | 0 |
| `llm_backoff_sleep_ms` | 0.0 |
| `cache_hit_rate` | 0.0 |
| `scheduler_deferred` | 0 |
| `scheduler_local_only` | 0 |
| `scheduler_api_allowed` | 2 |
| `api_deferred` | 0 |
| `avg_priority_score` | 0.996 |
| `json_valid_rate` | 0.0 |
| `fallback_rate` | 1.0 |
| `avg_detector_latency_ms` | 12.3411 |
| `avg_retrieval_latency_ms` | 97.4139 |
| `avg_llm_latency_ms` | 35699.6331 |
| `avg_end_to_end_latency_ms` | 65761.7588 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `local_llama_gemini_lite_1p1n_by_service.csv` |
| `by_fault_type` | see `local_llama_gemini_lite_1p1n_by_fault_type.csv` |
| `llm_cost_pricing_source` | not_configured |
| `estimated_input_cost_usd` | 0.0 |
| `estimated_output_cost_usd` | 0.0 |
| `estimated_llm_cost_usd` | 0.0 |
