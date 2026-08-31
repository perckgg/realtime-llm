# Step 7 View A Report

| Split | Regime | Variant | Windows | Precision | Recall | F1 | FPR | Manual Review | Auto Coverage | Selective F1 | LLM F1 | LLM Calls | API Calls | Cache Hits | Candidate Ctx Coverage | Retrieval Attempt Coverage | Est. Cost USD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| paper_500 | quality_full_budget | hybrid_bm25_top6 | 500 | 0.8923 | 0.58 | 0.703 | 0.0175 | 0.782 | 0.218 | 0.7891 | 0.7117 | 489 | 489 | 0 | 0.2249 | 0.2249 | 0.0627953 |
| paper_500 | quality_full_budget | topology_aware_fusion_top6 | 500 | 0.3507 | 0.74 | 0.4759 | 0.3425 | 0.22 | 0.78 | 0.4884 | 0.479 | 489 | 489 | 0 | 1.0 | 1.0 | 0.1669426 |

## paper_500

- Window rows: 500
- Window hash: `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`
- Budget regime: `quality_full_budget` (`max_total_calls=500`)
- LLM: `gemini/gemini-2.5-flash-lite`
- Service count: 56
- Ground truth counts: `{"normal": 400, "true_alert": 100}`
- Fault type counts: `{"cpu_consumed": 13, "cpu_contention": 29, "exception": 11, "network_delay": 40, "none": 400, "return": 7}`
- Topology delta vs BM25: precision -0.5416, recall 0.16, f1 -0.2271, fpr 0.325, context coverage 0.7751, avg ctx 4.74, retrieval ms -6.7655.

