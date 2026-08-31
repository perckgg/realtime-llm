# Step 7 Rerun Paired Analysis

- Bootstrap samples: 10000
- Seed: 42
- Delta direction: topology_aware_fusion_top6 minus hybrid_bm25_top6

| Regime | BM25 F1 | Topology F1 | Delta F1 [95% CI] | BM25 Recall | Topology Recall | Delta Recall [95% CI] | BM25 FPR | Topology FPR | McNemar all p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| operational_budget_120 | 0.5075 | 0.5140 | 0.0065 [-0.0981, 0.1134] | 0.3400 | 0.4600 | 0.1200 [0.0202, 0.2222] | 0.0000 | 0.0825 | 0.00985 |
| quality_full_budget | 0.7030 | 0.4759 | -0.2271 [-0.3210, -0.1320] | 0.5800 | 0.7400 | 0.1600 [0.0460, 0.2737] | 0.0175 | 0.3425 | 2.61e-19 |

McNemar uses paired correctness on the same frozen windows. Manual review remains a non-routed end-to-end decision in this analysis; selective metrics are reported separately in the regime reports.
