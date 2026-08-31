# Step 7 View A Report

| Split | Variant | Windows | Candidates | Precision | Recall | F1 | FPR | LLM Calls | API Calls | Cache Hits | Cache Hit Rate | Context Coverage | Avg Ctx | Retrieval ms | LLM ms | Est. Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| paper_300 | hybrid_bm25_top6 | 300 | 40 | 1.0 | 0.25 | 0.4 | 0.0 | 40 | 1 | 39 | 0.975 | 0.2 | 0.16 | 11.4327 | 30.0292 | 0.0052102 |
| paper_300 | topology_aware_fusion_top6 | 300 | 40 | 0.1905 | 0.25 | 0.2162 | 0.0599 | 40 | 1 | 39 | 0.975 | 1.0 | 0.8 | 10.1107 | 12.8359 | 0.014592 |
| paper_500 | hybrid_bm25_top6 | 500 | 489 | 1.0 | 0.34 | 0.5075 | 0.0 | 120 | 1 | 119 | 0.9917 | 0.1125 | 0.554 | 20.5649 | 61.7131 | 0.0214684 |
| paper_500 | topology_aware_fusion_top6 | 500 | 489 | 0.5823 | 0.46 | 0.514 | 0.0825 | 120 | 1 | 119 | 0.9917 | 0.2454 | 1.44 | 18.5192 | 6.64 | 0.0401765 |

## paper_300

- Window rows: 300
- Window hash: `6e5824396d5918be7c46d34daf5dca67b958e8eb5cbded44b97fe4640620e763`
- Service count: 1
- Ground truth counts: `{"normal": 284, "true_alert": 16}`
- Fault type counts: `{"cpu_contention": 8, "network_delay": 8, "none": 284}`
- Topology delta vs BM25: precision -0.8095, recall 0.0, f1 -0.1838, fpr 0.0599, context coverage 0.8, avg ctx 0.64, retrieval ms -1.322.

## paper_500

- Window rows: 500
- Window hash: `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`
- Service count: 56
- Ground truth counts: `{"normal": 400, "true_alert": 100}`
- Fault type counts: `{"cpu_consumed": 13, "cpu_contention": 29, "exception": 11, "network_delay": 40, "none": 400, "return": 7}`
- Topology delta vs BM25: precision -0.4177, recall 0.12, f1 0.0065, fpr 0.0825, context coverage 0.1329, avg ctx 0.886, retrieval ms -2.0457.

