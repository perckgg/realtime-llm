# Experiment Summary: step7_view_a_paper_500_hybrid_bm25_top6

| Metric | Value |
|---|---:|
| `precision` | 1.0 |
| `recall` | 0.34 |
| `f1` | 0.5075 |
| `false_positive_rate` | 0.0 |
| `tp` | 34 |
| `fp` | 0 |
| `tn` | 400 |
| `fn` | 66 |
| `evaluated_windows` | 500 |
| `candidate_alerts` | 489 |
| `routed_alerts` | 34 |
| `alerts` | 489 |
| `llm_calls` | 120 |
| `llm_calls_avoided` | 380 |
| `llm_budget_exhausted` | 369 |
| `input_tokens` | 109256 |
| `output_tokens` | 26357 |
| `context_tokens` | 1738 |
| `avg_retrieved_context_count` | 0.554 |
| `avg_context_tokens` | 3.476 |
| `candidates_with_context` | 55 |
| `context_coverage_rate` | 0.1125 |
| `context_rescue_checked` | 0 |
| `context_rescue_promoted` | 0 |
| `api_fallback_calls` | 0 |
| `model_fallback_calls` | 0 |
| `local_llm_valid_json` | 0 |
| `llm_providers` | ['gemini'] |
| `primary_local_models` | [] |
| `fallback_models` | [] |
| `llm_cache_hits` | 119 |
| `actual_api_calls` | 1 |
| `llm_retry_count` | 3 |
| `llm_backoff_sleep_ms` | 15535.4197 |
| `cache_hit_rate` | 0.9917 |
| `scheduler_deferred` | 0 |
| `scheduler_local_only` | 0 |
| `scheduler_api_allowed` | 120 |
| `api_deferred` | 0 |
| `avg_priority_score` | 0.9954 |
| `json_valid_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `avg_detector_latency_ms` | 9.1503 |
| `avg_retrieval_latency_ms` | 20.5649 |
| `avg_llm_latency_ms` | 61.7131 |
| `avg_end_to_end_latency_ms` | 1020.822 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `step7_view_a_paper_500_hybrid_bm25_top6_by_service.csv` |
| `by_fault_type` | see `step7_view_a_paper_500_hybrid_bm25_top6_by_fault_type.csv` |
| `llm_cost_pricing_source` | gemini_flash_lite_published |
| `estimated_input_cost_usd` | 0.0109256 |
| `estimated_output_cost_usd` | 0.0105428 |
| `estimated_llm_cost_usd` | 0.0214684 |
