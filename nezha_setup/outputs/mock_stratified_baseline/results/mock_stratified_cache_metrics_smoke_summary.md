# Experiment Summary: mock_stratified_cache_metrics_smoke

| Metric | Value |
|---|---:|
| `precision` | 0.8 |
| `recall` | 1.0 |
| `f1` | 0.8889 |
| `false_positive_rate` | 0.1667 |
| `tp` | 4 |
| `fp` | 1 |
| `tn` | 5 |
| `fn` | 0 |
| `evaluated_windows` | 10 |
| `candidate_alerts` | 9 |
| `routed_alerts` | 5 |
| `alerts` | 9 |
| `llm_calls` | 9 |
| `llm_calls_avoided` | 1 |
| `llm_budget_exhausted` | 0 |
| `input_tokens` | 951 |
| `output_tokens` | 213 |
| `context_tokens` | 179 |
| `avg_retrieved_context_count` | 2.9 |
| `avg_context_tokens` | 17.9 |
| `candidates_with_context` | 5 |
| `context_coverage_rate` | 0.5556 |
| `context_rescue_checked` | 1 |
| `context_rescue_promoted` | 0 |
| `api_fallback_calls` | 0 |
| `local_llm_valid_json` | 0 |
| `llm_providers` | ['mock'] |
| `llm_cache_hits` | 0 |
| `actual_api_calls` | 0 |
| `llm_retry_count` | 0 |
| `llm_backoff_sleep_ms` | 0.0 |
| `cache_hit_rate` | 0.0 |
| `json_valid_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `avg_detector_latency_ms` | 8.3604 |
| `avg_retrieval_latency_ms` | 71.4381 |
| `avg_llm_latency_ms` | 0.0748 |
| `avg_end_to_end_latency_ms` | 80.0503 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `mock_stratified_cache_metrics_smoke_by_service.csv` |
| `by_fault_type` | see `mock_stratified_cache_metrics_smoke_by_fault_type.csv` |
| `llm_cost_pricing_source` | mock_no_cost |
| `estimated_input_cost_usd` | 0.0 |
| `estimated_output_cost_usd` | 0.0 |
| `estimated_llm_cost_usd` | 0.0 |
