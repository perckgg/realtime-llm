# Step 7 View A Report

| Split | Regime | Variant | Windows | Precision | Recall | F1 | FPR | Manual Review | Auto Coverage | Selective F1 | LLM F1 | LLM Calls | API Calls | Cache Hits | Candidate Ctx Coverage | Retrieval Attempt Coverage | Est. Cost USD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| paper_500 | operational_budget_120 | hybrid_bm25_top6 | 500 | 1.0 | 0.34 | 0.5075 | 0.0 | 0.886 | 0.114 | 0.8293 | 0.7083 | 120 | 120 | 0 | 0.1125 | 0.4583 | 0.0214684 |
| paper_500 | operational_budget_120 | topology_aware_fusion_top6 | 500 | 0.5823 | 0.46 | 0.514 | 0.0825 | 0.768 | 0.232 | 0.6765 | 0.6525 | 120 | 120 | 0 | 0.2454 | 1.0 | 0.0401765 |

## paper_500

- Window rows: 500
- Window hash: `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`
- Budget regime: `operational_budget_120` (`max_total_calls=120`)
- LLM: `gemini/gemini-2.5-flash-lite`
- Service count: 56
- Ground truth counts: `{"normal": 400, "true_alert": 100}`
- Fault type counts: `{"cpu_consumed": 13, "cpu_contention": 29, "exception": 11, "network_delay": 40, "none": 400, "return": 7}`
- Topology delta vs BM25: precision -0.4177, recall 0.12, f1 0.0065, fpr 0.0825, context coverage 0.1329, avg ctx 0.886, retrieval ms -4.9915.

