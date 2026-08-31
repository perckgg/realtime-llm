# Experiment Summary: step7_view_a_paper_300_hybrid_bm25_top6

| Metric | Value |
|---|---:|
| `precision` | 1.0 |
| `recall` | 0.25 |
| `f1` | 0.4 |
| `false_positive_rate` | 0.0 |
| `tp` | 4 |
| `fp` | 0 |
| `tn` | 284 |
| `fn` | 12 |
| `evaluated_windows` | 300 |
| `candidate_alerts` | 40 |
| `routed_alerts` | 4 |
| `alerts` | 40 |
| `llm_calls` | 40 |
| `llm_calls_avoided` | 260 |
| `llm_budget_exhausted` | 0 |
| `input_tokens` | 26414 |
| `output_tokens` | 6422 |
| `context_tokens` | 288 |
| `avg_retrieved_context_count` | 0.16 |
| `avg_context_tokens` | 0.96 |
| `candidates_with_context` | 8 |
| `context_coverage_rate` | 0.2 |
| `context_rescue_checked` | 0 |
| `context_rescue_promoted` | 0 |
| `api_fallback_calls` | 0 |
| `model_fallback_calls` | 0 |
| `local_llm_valid_json` | 0 |
| `llm_providers` | ['gemini'] |
| `primary_local_models` | [] |
| `fallback_models` | [] |
| `llm_cache_hits` | 39 |
| `actual_api_calls` | 1 |
| `llm_retry_count` | 1 |
| `llm_backoff_sleep_ms` | 2562.8284 |
| `cache_hit_rate` | 0.975 |
| `scheduler_deferred` | 0 |
| `scheduler_local_only` | 0 |
| `scheduler_api_allowed` | 40 |
| `api_deferred` | 0 |
| `avg_priority_score` | 0.9761 |
| `json_valid_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `avg_detector_latency_ms` | 8.2724 |
| `avg_retrieval_latency_ms` | 11.4327 |
| `avg_llm_latency_ms` | 30.0292 |
| `avg_end_to_end_latency_ms` | 551.8214 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `step7_view_a_paper_300_hybrid_bm25_top6_by_service.csv` |
| `by_fault_type` | see `step7_view_a_paper_300_hybrid_bm25_top6_by_fault_type.csv` |
| `llm_cost_pricing_source` | gemini_flash_lite_published |
| `estimated_input_cost_usd` | 0.0026414 |
| `estimated_output_cost_usd` | 0.0025688 |
| `estimated_llm_cost_usd` | 0.0052102 |
