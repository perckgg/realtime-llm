# Phase 2 Input Freeze

Generated at UTC: `2026-07-06T03:16:42.436038+00:00`

## Source files

| File | SHA-256 |
|---|---|
| `outputs/phase2/window_index.csv` | `d3900eb9012935f4c5f8f27a9c82c385b9968fe0b179305a3f4febe0e66421e6` |
| `outputs/phase2/baseline_reference.csv` | `3d0a03278be406c5b30a6164fe9493bedf60a22f34f298128b23fb584ec95d8b` |

## Frozen window sets

| Split | Rows | Unique windows | Ground truth | Fault types | Window ID SHA-256 |
|---|---:|---:|---|---|---|
| `debug_50` | 50 | 50 | normal=25, true_alert=25 | cpu_consumed=5, cpu_contention=13, exception=3, network_delay=2, none=25, return=2 | `d0784c65d8e140489e705de593293f50eaed2a0ef50a9d936b869a5c629eb680` |
| `paper_300` | 300 | 300 | normal=284, true_alert=16 | cpu_contention=8, network_delay=8, none=284 | `6e5824396d5918be7c46d34daf5dca67b958e8eb5cbded44b97fe4640620e763` |
| `paper_500` | 500 | 500 | normal=400, true_alert=100 | cpu_consumed=13, cpu_contention=29, exception=11, network_delay=40, none=400, return=7 | `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e` |

## Baseline alignment

| Baseline | Expected split | Audit rows | Unique windows | Matches split |
|---|---|---:|---:|---|
| `detector_only` | `paper_300` | 300 | 300 | True |
| `llm_without_rag` | `paper_300` | 300 | 300 | True |
| `hybrid_bm25_top6` | `paper_300` | 300 | 300 | True |
| `hybrid_bm25_top10` | `paper_300` | 300 | 300 | True |
| `phase5_context_rescue` | `paper_300` | 300 | 300 | True |
| `real_llm_500w_cache_replay` | `paper_500` | 500 | 500 | True |

## Freeze status

Freeze completed successfully. All listed baselines match their expected frozen split.
