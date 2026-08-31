# Audit Failure Analysis

Derived from existing Nezha audit JSONL files only. No LLM/API call is made.

Classification uses the existing evaluator rule: `ground_truth == true_alert` is positive and `final_decision == route_alert` is predicted positive.

## By Fault Type

| run | group | windows | candidates | routed | manual_review | tp | fp | tn | fn | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | avg_anomaly_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase4_hybrid_bm25_top6 | cpu_contention | 8 | 6 | 6 | 0 | 6 | 0 | 0 | 2 | 1.0 | 0.75 | 0.8571 | 0.0 | 6 | 0.75 | 4.5 | 0.8616 |
| phase4_hybrid_bm25_top6 | network_delay | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.2497 |
| phase4_hybrid_bm25_top6 | none | 284 | 34 | 13 | 21 | 0 | 13 | 271 | 0 | 0.0 | 0.0 | 0.0 | 0.0458 | 24 | 0.0106 | 0.0493 | 0.5861 |
| phase5_context_rescue | cpu_contention | 8 | 8 | 8 | 0 | 8 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | 8 | 1.0 | 6.0 | 0.9978 |
| phase5_context_rescue | network_delay | 8 | 8 | 8 | 0 | 8 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | 8 | 1.0 | 6.0 | 0.871 |
| phase5_context_rescue | none | 284 | 39 | 9 | 30 | 0 | 9 | 275 | 0 | 0.0 | 0.0 | 0.0 | 0.0317 | 39 | 0.1796 | 0.7711 | 0.5956 |
| real_llm_500w_cache_replay | cpu_consumed | 13 | 13 | 8 | 5 | 8 | 0 | 0 | 5 | 1.0 | 0.6154 | 0.7619 | 0.0 | 8 | 0.6154 | 3.6923 | 0.9965 |
| real_llm_500w_cache_replay | cpu_contention | 29 | 29 | 15 | 10 | 15 | 0 | 0 | 14 | 1.0 | 0.5172 | 0.6818 | 0.0 | 20 | 0.6897 | 4.1379 | 0.998 |
| real_llm_500w_cache_replay | exception | 11 | 11 | 6 | 4 | 6 | 0 | 0 | 5 | 1.0 | 0.5455 | 0.7059 | 0.0 | 8 | 0.7273 | 4.3636 | 0.9987 |
| real_llm_500w_cache_replay | network_delay | 40 | 39 | 14 | 22 | 14 | 0 | 0 | 26 | 1.0 | 0.35 | 0.5185 | 0.0 | 20 | 0.525 | 3.15 | 0.9799 |
| real_llm_500w_cache_replay | none | 400 | 391 | 56 | 335 | 0 | 56 | 344 | 0 | 0.0 | 0.0 | 0.0 | 0.14 | 58 | 0.0075 | 0.025 | 0.9862 |
| real_llm_500w_cache_replay | return | 7 | 7 | 4 | 2 | 4 | 0 | 0 | 3 | 1.0 | 0.5714 | 0.7273 | 0.0 | 6 | 0.8571 | 5.1429 | 0.998 |

## By Service

| run | group | windows | candidates | routed | manual_review | tp | fp | tn | fn | precision | recall | f1 | fpr | llm_calls | context_coverage | avg_context | avg_anomaly_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase4_hybrid_bm25_top6 | cartservice | 300 | 40 | 19 | 21 | 6 | 13 | 271 | 10 | 0.3158 | 0.375 | 0.3429 | 0.0458 | 30 | 0.03 | 0.1667 | 0.5844 |
| real_llm_500w_cache_replay | frontend | 20 | 20 | 15 | 3 | 7 | 8 | 1 | 4 | 0.4667 | 0.6364 | 0.5385 | 0.8889 | 20 | 0.55 | 3.3 | 0.9979 |
| real_llm_500w_cache_replay | shippingservice | 18 | 18 | 14 | 3 | 6 | 8 | 1 | 3 | 0.4286 | 0.6667 | 0.5217 | 0.8889 | 15 | 0.3889 | 2.3333 | 0.9931 |
| real_llm_500w_cache_replay | checkoutservice | 18 | 18 | 18 | 0 | 8 | 10 | 0 | 0 | 0.4444 | 1.0 | 0.6154 | 1.0 | 18 | 0.4444 | 2.6667 | 0.9988 |
| real_llm_500w_cache_replay | emailservice | 12 | 12 | 8 | 1 | 2 | 6 | 0 | 4 | 0.25 | 0.3333 | 0.2857 | 1.0 | 12 | 0.5833 | 3.5 | 0.9958 |
| phase5_context_rescue | cartservice | 300 | 55 | 25 | 30 | 16 | 9 | 275 | 0 | 0.64 | 1.0 | 0.7805 | 0.0317 | 55 | 0.2233 | 1.05 | 0.6137 |
| real_llm_500w_cache_replay | paymentservice | 17 | 17 | 15 | 1 | 7 | 8 | 1 | 1 | 0.4667 | 0.875 | 0.6087 | 0.8889 | 17 | 0.5294 | 2.9412 | 0.9946 |
| real_llm_500w_cache_replay | ts-food-service | 19 | 19 | 0 | 19 | 0 | 0 | 11 | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9971 |
| real_llm_500w_cache_replay | adservice | 16 | 16 | 0 | 16 | 0 | 0 | 8 | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9984 |
| real_llm_500w_cache_replay | currencyservice | 12 | 12 | 10 | 1 | 4 | 6 | 0 | 2 | 0.4 | 0.6667 | 0.5 | 1.0 | 12 | 0.5 | 3.0 | 0.9986 |
| real_llm_500w_cache_replay | recommendationservice | 18 | 16 | 15 | 1 | 9 | 6 | 2 | 1 | 0.6 | 0.9 | 0.72 | 0.75 | 16 | 0.5556 | 3.3333 | 0.9807 |
| real_llm_500w_cache_replay | productcatalogservice | 10 | 10 | 5 | 5 | 1 | 4 | 2 | 3 | 0.2 | 0.25 | 0.2222 | 0.6667 | 5 | 0.1 | 0.6 | 0.9983 |
| real_llm_500w_cache_replay | ts-basic-service | 6 | 6 | 0 | 6 | 0 | 0 | 2 | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9985 |
| real_llm_500w_cache_replay | ts-travel-service | 18 | 18 | 0 | 18 | 0 | 0 | 15 | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9974 |
| real_llm_500w_cache_replay | cartservice | 13 | 5 | 3 | 1 | 3 | 0 | 7 | 3 | 1.0 | 0.5 | 0.6667 | 0.0 | 5 | 0.5385 | 2.9231 | 0.6894 |
| real_llm_500w_cache_replay | ts-route-service | 10 | 10 | 0 | 10 | 0 | 0 | 8 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9914 |
| real_llm_500w_cache_replay | ts-security-service | 10 | 10 | 0 | 10 | 0 | 0 | 8 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9935 |
| real_llm_500w_cache_replay | ts-contacts-service | 9 | 9 | 0 | 9 | 0 | 0 | 7 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9898 |
| real_llm_500w_cache_replay | ts-verification-code-service | 8 | 8 | 0 | 8 | 0 | 0 | 6 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9914 |
| real_llm_500w_cache_replay | ts-preserve-service | 6 | 6 | 0 | 6 | 0 | 0 | 5 | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.9968 |

## FP/FN Hotspots

| run | hotspot_type | service_id | node_id | fault_type | windows | fp | fn | tp | precision | recall | candidates | manual_review | top_final_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase4_hybrid_bm25_top6 | fp_hotspot | cartservice | cartservice-579f59597d-wc2lz | none | 284 | 13 | 0 | 0 | 0.0 | 0.0 | 34 | 21 | suppress=250, manual_review=21, route_alert=13 |
| phase4_hybrid_bm25_top6 | fn_hotspot | cartservice | cartservice-579f59597d-wc2lz | network_delay | 8 | 0 | 8 | 0 | 0.0 | 0.0 | 0 | 0 | suppress=8 |
| phase4_hybrid_bm25_top6 | fn_hotspot | cartservice | cartservice-579f59597d-wc2lz | cpu_contention | 8 | 0 | 2 | 6 | 1.0 | 0.75 | 6 | 0 | route_alert=6, suppress=2 |
| phase5_context_rescue | fp_hotspot | cartservice | cartservice-579f59597d-wc2lz | none | 284 | 9 | 0 | 0 | 0.0 | 0.0 | 39 | 30 | suppress=245, manual_review=30, route_alert=9 |
| real_llm_500w_cache_replay | fp_hotspot | checkoutservice | checkoutservice-578fcf4766-9csqn | none | 10 | 10 | 0 | 0 | 0.0 | 0.0 | 10 | 0 | route_alert=10 |
| real_llm_500w_cache_replay | fp_hotspot | frontend | frontend-579b9bff58-t2dbm | none | 9 | 8 | 0 | 0 | 0.0 | 0.0 | 9 | 1 | route_alert=8, manual_review=1 |
| real_llm_500w_cache_replay | fp_hotspot | paymentservice | paymentservice-9cdb6588f-554sm | none | 9 | 8 | 0 | 0 | 0.0 | 0.0 | 9 | 1 | route_alert=8, manual_review=1 |
| real_llm_500w_cache_replay | fp_hotspot | shippingservice | shippingservice-7b598fc7d-lmggd | none | 9 | 8 | 0 | 0 | 0.0 | 0.0 | 9 | 1 | route_alert=8, manual_review=1 |
| real_llm_500w_cache_replay | fp_hotspot | recommendationservice | recommendationservice-6cfdd55578-gfj6q | none | 8 | 6 | 0 | 0 | 0.0 | 0.0 | 6 | 0 | route_alert=6, suppress=2 |
| real_llm_500w_cache_replay | fp_hotspot | currencyservice | currencyservice-cf787dd48-vpjrd | none | 6 | 6 | 0 | 0 | 0.0 | 0.0 | 6 | 0 | route_alert=6 |
| real_llm_500w_cache_replay | fp_hotspot | emailservice | emailservice-55fdc5b988-f6xth | none | 6 | 6 | 0 | 0 | 0.0 | 0.0 | 6 | 0 | route_alert=6 |
| real_llm_500w_cache_replay | fp_hotspot | productcatalogservice | productcatalogservice-668d5f85fb-wckp8 | none | 4 | 4 | 0 | 0 | 0.0 | 0.0 | 4 | 0 | route_alert=4 |
| real_llm_500w_cache_replay | fn_hotspot | ts-food-service | ts-food-service-f5756978c-6sb8t | network_delay | 4 | 0 | 4 | 0 | 0.0 | 0.0 | 4 | 4 | manual_review=4 |
| real_llm_500w_cache_replay | fn_hotspot | adservice | adservice-5f6585d649-fnmft | cpu_consumed | 3 | 0 | 3 | 0 | 0.0 | 0.0 | 3 | 3 | manual_review=3 |
| real_llm_500w_cache_replay | fn_hotspot | currencyservice | currencyservice-cf787dd48-vpjrd | network_delay | 4 | 0 | 2 | 2 | 1.0 | 0.5 | 4 | 1 | route_alert=2, suppress=1, manual_review=1 |
| real_llm_500w_cache_replay | fn_hotspot | emailservice | emailservice-55fdc5b988-f6xth | network_delay | 4 | 0 | 2 | 2 | 1.0 | 0.5 | 4 | 0 | suppress=2, route_alert=2 |
| real_llm_500w_cache_replay | fn_hotspot | frontend | frontend-579b9bff58-t2dbm | exception | 4 | 0 | 2 | 2 | 1.0 | 0.5 | 4 | 1 | route_alert=2, manual_review=1, suppress=1 |
| real_llm_500w_cache_replay | fn_hotspot | frontend | frontend-579b9bff58-t2dbm | return | 4 | 0 | 2 | 2 | 1.0 | 0.5 | 4 | 1 | route_alert=2, manual_review=1, suppress=1 |
| real_llm_500w_cache_replay | fn_hotspot | adservice | adservice-5f6585d649-fnmft | cpu_contention | 2 | 0 | 2 | 0 | 0.0 | 0.0 | 2 | 2 | manual_review=2 |
| real_llm_500w_cache_replay | fn_hotspot | cartservice | cartservice-579f59597d-wc2lz | network_delay | 2 | 0 | 2 | 0 | 0.0 | 0.0 | 1 | 1 | manual_review=1, suppress=1 |
| real_llm_500w_cache_replay | fn_hotspot | emailservice | emailservice-55fdc5b988-f6xth | cpu_contention | 2 | 0 | 2 | 0 | 0.0 | 0.0 | 2 | 1 | suppress=1, manual_review=1 |
| real_llm_500w_cache_replay | fn_hotspot | productcatalogservice | productcatalogservice-668d5f85fb-jhwx9 | exception | 2 | 0 | 2 | 0 | 0.0 | 0.0 | 2 | 2 | manual_review=2 |
| real_llm_500w_cache_replay | fn_hotspot | shippingservice | shippingservice-7b598fc7d-lmggd | cpu_consumed | 2 | 0 | 2 | 0 | 0.0 | 0.0 | 2 | 2 | manual_review=2 |
| real_llm_500w_cache_replay | fn_hotspot | ts-basic-service | ts-basic-service-5dc8d4f9fd-llznp | cpu_contention | 2 | 0 | 2 | 0 | 0.0 | 0.0 | 2 | 2 | manual_review=2 |

## Top Pod Failure Rows

| run | service_id | node_id | fault_type | windows | candidates | routed | manual_review | tp | fp | tn | fn | precision | recall | f1 | fpr | llm_calls | avg_anomaly_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase4_hybrid_bm25_top6 | cartservice | cartservice-579f59597d-wc2lz | none | 284 | 34 | 13 | 21 | 0 | 13 | 271 | 0 | 0.0 | 0.0 | 0.0 | 0.0458 | 24 | 0.5861 |
| real_llm_500w_cache_replay | checkoutservice | checkoutservice-578fcf4766-9csqn | none | 10 | 10 | 10 | 0 | 0 | 10 | 0 | 0 | 0.0 | 0.0 | 0.0 | 1.0 | 10 | 0.9985 |
| phase5_context_rescue | cartservice | cartservice-579f59597d-wc2lz | none | 284 | 39 | 9 | 30 | 0 | 9 | 275 | 0 | 0.0 | 0.0 | 0.0 | 0.0317 | 39 | 0.5956 |
| real_llm_500w_cache_replay | frontend | frontend-579b9bff58-t2dbm | none | 9 | 9 | 8 | 1 | 0 | 8 | 1 | 0 | 0.0 | 0.0 | 0.0 | 0.8889 | 9 | 0.998 |
| real_llm_500w_cache_replay | paymentservice | paymentservice-9cdb6588f-554sm | none | 9 | 9 | 8 | 1 | 0 | 8 | 1 | 0 | 0.0 | 0.0 | 0.0 | 0.8889 | 9 | 0.9939 |
| real_llm_500w_cache_replay | shippingservice | shippingservice-7b598fc7d-lmggd | none | 9 | 9 | 8 | 1 | 0 | 8 | 1 | 0 | 0.0 | 0.0 | 0.0 | 0.8889 | 8 | 0.9904 |
| phase4_hybrid_bm25_top6 | cartservice | cartservice-579f59597d-wc2lz | network_delay | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.2497 |
| real_llm_500w_cache_replay | recommendationservice | recommendationservice-6cfdd55578-gfj6q | none | 8 | 6 | 6 | 0 | 0 | 6 | 2 | 0 | 0.0 | 0.0 | 0.0 | 0.75 | 6 | 0.9667 |
| real_llm_500w_cache_replay | currencyservice | currencyservice-cf787dd48-vpjrd | none | 6 | 6 | 6 | 0 | 0 | 6 | 0 | 0 | 0.0 | 0.0 | 0.0 | 1.0 | 6 | 0.9987 |
| real_llm_500w_cache_replay | emailservice | emailservice-55fdc5b988-f6xth | none | 6 | 6 | 6 | 0 | 0 | 6 | 0 | 0 | 0.0 | 0.0 | 0.0 | 1.0 | 6 | 0.995 |
| real_llm_500w_cache_replay | productcatalogservice | productcatalogservice-668d5f85fb-wckp8 | none | 4 | 4 | 4 | 0 | 0 | 4 | 0 | 0 | 0.0 | 0.0 | 0.0 | 1.0 | 4 | 0.9983 |
| real_llm_500w_cache_replay | ts-food-service | ts-food-service-f5756978c-6sb8t | network_delay | 4 | 4 | 0 | 4 | 0 | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.998 |
| real_llm_500w_cache_replay | adservice | adservice-5f6585d649-fnmft | cpu_consumed | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.9997 |
| phase4_hybrid_bm25_top6 | cartservice | cartservice-579f59597d-wc2lz | cpu_contention | 8 | 6 | 6 | 0 | 6 | 0 | 0 | 2 | 1.0 | 0.75 | 0.8571 | 0.0 | 6 | 0.8616 |
| real_llm_500w_cache_replay | currencyservice | currencyservice-cf787dd48-vpjrd | network_delay | 4 | 4 | 2 | 1 | 2 | 0 | 0 | 2 | 1.0 | 0.5 | 0.6667 | 0.0 | 4 | 0.9977 |
| real_llm_500w_cache_replay | emailservice | emailservice-55fdc5b988-f6xth | network_delay | 4 | 4 | 2 | 0 | 2 | 0 | 0 | 2 | 1.0 | 0.5 | 0.6667 | 0.0 | 4 | 0.9958 |
| real_llm_500w_cache_replay | frontend | frontend-579b9bff58-t2dbm | exception | 4 | 4 | 2 | 1 | 2 | 0 | 0 | 2 | 1.0 | 0.5 | 0.6667 | 0.0 | 4 | 0.9978 |
| real_llm_500w_cache_replay | frontend | frontend-579b9bff58-t2dbm | return | 4 | 4 | 2 | 1 | 2 | 0 | 0 | 2 | 1.0 | 0.5 | 0.6667 | 0.0 | 4 | 0.9978 |
| real_llm_500w_cache_replay | adservice | adservice-5f6585d649-fnmft | cpu_contention | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.0 |
| real_llm_500w_cache_replay | cartservice | cartservice-579f59597d-wc2lz | network_delay | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 1 | 0.7084 |
| real_llm_500w_cache_replay | emailservice | emailservice-55fdc5b988-f6xth | cpu_contention | 2 | 2 | 0 | 1 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 2 | 0.9985 |
| real_llm_500w_cache_replay | productcatalogservice | productcatalogservice-668d5f85fb-jhwx9 | exception | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.9985 |
| real_llm_500w_cache_replay | shippingservice | shippingservice-7b598fc7d-lmggd | cpu_consumed | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.9955 |
| real_llm_500w_cache_replay | ts-basic-service | ts-basic-service-5dc8d4f9fd-llznp | cpu_contention | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.9995 |
| real_llm_500w_cache_replay | ts-basic-service | ts-basic-service-5dc8d4f9fd-llznp | network_delay | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.998 |
| real_llm_500w_cache_replay | ts-contacts-service | ts-contacts-service-866bd68c97-dzqgd | network_delay | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.986 |
| real_llm_500w_cache_replay | ts-food-service | ts-food-service-f5756978c-6sb8t | cpu_contention | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.998 |
| real_llm_500w_cache_replay | ts-food-service | ts-food-service-f5756978c-k8vqf | cpu_contention | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.999 |
| real_llm_500w_cache_replay | ts-route-service | ts-route-service-b6c59fb57-dz9bw | network_delay | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.989 |
| real_llm_500w_cache_replay | ts-security-service | ts-security-service-cb9788d56-bdkcx | network_delay | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0.995 |
