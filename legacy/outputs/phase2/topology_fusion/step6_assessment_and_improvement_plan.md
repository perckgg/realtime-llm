# Step 6 Assessment and Improvement Plan

## Current result assessment

Step 6 successfully validates integration, not final effectiveness. The `topology_aware_fusion` backend can be selected by config, runs through the hybrid pipeline, and writes the required topology-aware audit fields.

However, the mock integration F1 is low:

| Run | Windows | TP | FP | FN | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| topology_fusion_300w | 300 | 6 | 34 | 10 | 0.1500 | 0.3750 | 0.2143 | 0.1197 |
| topology_fusion_500w | 500 | 6 | 40 | 10 | 0.1304 | 0.3750 | 0.1935 | 0.0826 |

## Why this F1 should not be treated as the final Phase 2 result

1. The Step 6 run is a smoke/integration run with `provider=mock`; it is not the planned Step 7 LLM/cache decision evaluation.
2. The current Step 6 runner uses `max_windows`, so it takes the first sequential windows from the processed metric stream instead of the frozen `paper_300`/`paper_500` stratified split.
3. The resulting Step 6 windows are service-biased: both 300w and 500w runs contain only `cartservice`.
4. `network_delay` is present in the window set but has zero candidate alerts, so recall for that difficult fault type is 0.0000 before retrieval/LLM can help.
5. The mock judge routes every candidate in the Step 6 run (`manual_review=0`, `suppress=0`), so F1 mostly reflects detector candidate quality rather than topology-aware retrieval quality.

## Impact on experiment quality

The low F1 does affect the narrative if it is presented as a final result. It should not be used to claim that topology-aware fusion improves or fails to improve anomaly diagnosis.

It does not invalidate Phase 2 so far because Step 6's success criterion is integration and audit readiness. The current result shows the next experiment must be fairer before making claims:

- use the frozen Phase 2 window split;
- compare BM25 top-6 and topology-aware top-6 on exactly the same windows;
- use the same LLM budget/cache policy;
- keep `Context Rescue` separate as an architecture-level baseline.

## Improvement plan before and during Step 7

1. Add a frozen-window runner that maps `outputs/phase2/window_index.csv` to `run_pipeline(..., window_indices=...)`.
2. Re-run topology-aware fusion on frozen `paper_300` and `paper_500`, not sequential `max_windows`.
3. Run a retrieval-fair comparison:
   - `hybrid_bm25_top6`
   - `topology_aware_fusion_top6`
   - same frozen split, same top-k, same LLM budget, same decision policy.
4. Run an architecture-level comparison separately:
   - detector-only
   - LLM without RAG
   - BM25 top-6
   - topology-aware fusion top-6
   - context rescue
5. Add tests for frozen split selection:
   - selected `window_id` count matches `input_freeze.json`;
   - selected split is not service-biased by accidental sequential slicing;
   - audit rows match the requested frozen split;
   - audit includes topology fields for candidate rows.
6. Evaluate Step 7 with cache-enabled LLM if available; otherwise label mock results as mock-only and avoid final LLM-quality claims.

## Claim boundary

Allowed after Step 6:

```text
Topology-aware fusion is integrated into the hybrid pipeline and produces auditable topology-aware retrieval fields.
```

Not allowed yet:

```text
Topology-aware fusion improves final alert diagnosis F1/recall/precision.
```

That claim requires Step 7 on a fair frozen split with a real/cache LLM decision run.
