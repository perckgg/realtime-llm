# Experiment Summary: gemini25_flash_lite_500w_budget_manual_review_cache_replay

| Metric | Value |
|---|---:|
| `precision` | 0.4563 |
| `recall` | 0.47 |
| `f1` | 0.4631 |
| `false_positive_rate` | 0.14 |
| `tp` | 47 |
| `fp` | 56 |
| `tn` | 344 |
| `fn` | 53 |
| `evaluated_windows` | 500 |
| `candidate_alerts` | 490 |
| `routed_alerts` | 103 |
| `alerts` | 490 |
| `llm_calls` | 120 |
| `llm_calls_avoided` | 380 |
| `llm_budget_exhausted` | 370 |
| `input_tokens` | 131046 |
| `output_tokens` | 31296 |
| `context_tokens` | 2339 |
| `avg_retrieved_context_count` | 0.776 |
| `avg_context_tokens` | 4.678 |
| `candidates_with_context` | 64 |
| `context_coverage_rate` | 0.1306 |
| `context_rescue_checked` | 11 |
| `context_rescue_promoted` | 1 |
| `api_fallback_calls` | 0 |
| `model_fallback_calls` | 0 |
| `local_llm_valid_json` | 0 |
| `llm_providers` | ['gemini'] |
| `primary_local_models` | [] |
| `fallback_models` | [] |
| `llm_cache_hits` | 120 |
| `actual_api_calls` | 0 |
| `llm_retry_count` | 0 |
| `llm_backoff_sleep_ms` | 0.0 |
| `cache_hit_rate` | 1.0 |
| `scheduler_deferred` | 0 |
| `scheduler_local_only` | 0 |
| `scheduler_api_allowed` | 120 |
| `api_deferred` | 0 |
| `avg_priority_score` | 0.9948 |
| `json_valid_rate` | 1.0 |
| `fallback_rate` | 0.0 |
| `avg_detector_latency_ms` | 14.6465 |
| `avg_retrieval_latency_ms` | 30.9229 |
| `avg_llm_latency_ms` | 0.0605 |
| `avg_end_to_end_latency_ms` | 45.8358 |
| `retrieval_backends` | ['local_hybrid_bm25'] |
| `retrieval_backend_warnings` | [] |
| `by_service` | see `gemini25_flash_lite_500w_budget_manual_review_cache_replay_by_service.csv` |
| `by_fault_type` | see `gemini25_flash_lite_500w_budget_manual_review_cache_replay_by_fault_type.csv` |
| `llm_cost_pricing_source` | gemini_flash_lite_published_cache_replay |
| `estimated_input_cost_usd` | 0.0131046 |
| `estimated_output_cost_usd` | 0.0125184 |
| `estimated_llm_cost_usd` | 0.025623 |
