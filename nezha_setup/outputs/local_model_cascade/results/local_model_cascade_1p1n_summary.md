# Experiment Summary: local_model_cascade_1p1n

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
| `input_tokens` | 2038 |
| `output_tokens` | 480 |
| `context_tokens` | 38 |
| `avg_retrieved_context_count` | 3.0 |
| `avg_context_tokens` | 19.0 |
| `candidates_with_context` | 1 |
| `context_coverage_rate` | 0.5 |
| `context_rescue_checked` | 0 |
| `context_rescue_promoted` | 0 |
| `api_fallback_calls` | 0 |
| `model_fallback_calls` | 1 |
| `local_llm_valid_json` | 2 |
| `llm_providers` | ['ollama'] |
| `primary_local_models` | ['ollama:llama3.2:3b'] |
| `fallback_models` | ['ollama:qwen2.5:3b'] |
| `llm_cache_hits` | 0 |
| `actual_api_calls` | 0 |
| `llm_retry_count` | 0 |
| `llm_backoff_sleep_ms` | 0.0 |
| `cache_hit_rate` | 0.0 |
| `scheduler_deferred` | 0 |
| `scheduler_local_only` | 0 |
| `scheduler_api_allowed` | 2 |
| `api_deferred` | 0 |
| `avg_priority_score` | 0.996 |
| `json_valid_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `avg_detector_latency_ms` | 18.0936 |
| `avg_retrieval_latency_ms` | 148.7751 |
| `avg_llm_latency_ms` | 70043.9732 |
| `avg_end_to_end_latency_ms` | 70211.3472 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `local_model_cascade_1p1n_by_service.csv` |
| `by_fault_type` | see `local_model_cascade_1p1n_by_fault_type.csv` |
| `llm_cost_pricing_source` | not_configured |
| `estimated_input_cost_usd` | 0.0 |
| `estimated_output_cost_usd` | 0.0 |
| `estimated_llm_cost_usd` | 0.0 |
