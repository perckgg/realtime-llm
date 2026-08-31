# Step 7 View A Rerun Assessment

## Protocol

- Frozen split: `paper_500`
- Windows: 500
- Window hash: `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`
- Services: 56
- Ground truth: 100 true alerts, 400 normal windows
- Model: `gemini-2.5-flash-lite`
- Comparison: BM25 top-6 versus topology-aware fusion top-6
- Cache policy: fresh isolated cache per method and regime
- API execution: all recorded calls are first-pass API calls; cache hits are zero
- Statistical analysis: 10,000 paired bootstrap samples, seed 42, exact McNemar tests

## Main results

| Regime | Method | Precision | Recall | F1 | FPR | Manual review | Retrieval-attempt coverage | API calls | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Budget 120 | BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.8860 | 0.4583 | 120 | 0.0214684 |
| Budget 120 | Topology fusion top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.7680 | 1.0000 | 120 | 0.0401765 |
| Full budget | BM25 top-6 | 0.8923 | 0.5800 | 0.7030 | 0.0175 | 0.7820 | 0.2249 | 489 | 0.0627953 |
| Full budget | Topology fusion top-6 | 0.3507 | 0.7400 | 0.4759 | 0.3425 | 0.2200 | 1.0000 | 489 | 0.1669426 |

## Paired statistical findings

- Under budget 120, topology increases recall by `+0.1200`, with bootstrap 95% CI `[0.0202, 0.2222]`.
- Under budget 120, F1 delta is only `+0.0065`, with 95% CI `[-0.0981, 0.1134]`; there is no reliable aggregate F1 improvement.
- Under full budget, topology increases recall by `+0.1600`, with 95% CI `[0.0460, 0.2737]`.
- Under full budget, topology decreases F1 by `-0.2271`, with 95% CI `[-0.3210, -0.1320]`.
- Full-budget FPR increases by `+0.3250`, with 95% CI `[0.2771, 0.3734]`.
- The full-budget paired correctness difference is significant by exact McNemar test (`p=2.61e-19`) and favors BM25 overall.

## Fault-level finding

The main positive result remains `network_delay`:

| Method | Network-delay recall | TP | FN |
|---|---:|---:|---:|
| BM25 top-6 | 0.3750 | 15 | 25 |
| Topology fusion top-6 | 0.7000 | 28 | 12 |

Topology also improves recall for the other positive fault types, but its normal-window behavior dominates the aggregate result: it routes 137 false alerts, compared with 7 for BM25.

## Manual-review interpretation

- Full-budget BM25 produces 391 manual reviews: 369 are `llm_valid_missing_evidence`, and 22 are other valid but non-routable LLM decisions.
- Full-budget topology produces 110 manual reviews, all from valid but non-routable LLM decisions.
- Topology therefore supplies context much more consistently and reduces abstention, but the current decision policy treats much of that context as positive evidence and over-routes normal windows.

## Conclusion

The rerun removes cache and budget ambiguity. It does not support the claim that topology-aware fusion improves overall downstream diagnosis. It supports a narrower claim:

> Topology-aware retrieval improves evidence availability and recall, particularly for network-delay faults, but the current fusion and decision policy substantially increase false positives, cost, and end-to-end error.

Step 7 View A rerun is complete. View B remains a separate architecture-level comparison.

## Required improvement before Step 8 paper tables

1. Calibrate topology evidence before routing: tune decision confidence, require stronger service/evidence consistency, or add a negative-evidence check.
2. Preserve the full-budget and budget-120 tables as separate operating regimes.
3. Use BM25 as the stronger overall-quality baseline; do not present topology fusion as the aggregate winner.
4. Present `network_delay` as a fault-specific case study and the recall/FPR/cost balance as the main paper result.
5. Complete View B and keep Context Rescue labeled as architecture-enhanced.
