# Phase 2 Submission Report

## Status

Phase 2 Steps 1–9 are complete. Step 10 packaging is in progress.

```text
Frozen inputs and baselines: complete
Service graph and topology retrieval: complete
Retrieval-only evaluation and ablation: complete
View A and View B LLM evaluation: complete
Paper tables and figures: complete
Step 9 quality gate: pass
Related Work with verified citations: pending
```

## Research question

Does topology-aware evidence retrieval improve downstream LLM alert validation compared with BM25 retrieval under controlled microservice monitoring conditions?

## Method

The method combines:

- metric anomaly detection;
- BM25 lexical retrieval;
- temporal similarity;
- service-graph similarity;
- schema-constrained LLM validation;
- manual-review abstention;
- cache, budget, retry, latency, and cost accounting.

The fusion score is:

\[
Score_{final} = \alpha BM25_{norm} + \beta TimeSim + \gamma GraphSim
\]

## Experimental protocol

- Main dataset: Nezha.
- Main split: `paper_500`.
- Windows: 500.
- Ground truth: 100 true alerts and 400 normal windows.
- Services: 56.
- LLM: `gemini-2.5-flash-lite`.
- Frozen hash: `1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e`.
- View A: retrieval-fair BM25 versus topology.
- View B: architecture-level detector, no-RAG, BM25, topology, and Context Rescue comparison.

## Main View A result

| Regime | Method | Precision | Recall | F1 | FPR | Cost USD |
|---|---|---:|---:|---:|---:|---:|
| Budget 120 | BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.0214684 |
| Budget 120 | Topology top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.0401765 |
| Full budget | BM25 top-6 | 0.8923 | 0.5800 | 0.7030 | 0.0175 | 0.0627953 |
| Full budget | Topology top-6 | 0.3507 | 0.7400 | 0.4759 | 0.3425 | 0.1669426 |

Topology improves recall and context coverage but degrades aggregate F1, FPR, and cost. Full-budget paired statistics favor BM25 overall.

## Fault-specific result

`network_delay` recall improves from `0.3750` to `0.7000`. This is the strongest supported positive result.

## View B result

| Method | F1 | Recall | FPR |
|---|---:|---:|---:|
| LLM without RAG | 0.5662 | 0.6200 | 0.1425 |
| Topology top-6 | 0.5140 | 0.4600 | 0.0825 |
| BM25 top-6 | 0.5075 | 0.3400 | 0.0000 |
| Context Rescue | 0.5075 | 0.3400 | 0.0000 |
| Detector-only | 0.3328 | 0.9800 | 0.9775 |

LLM without RAG has the highest View B F1. Context Rescue does not promote any of the 11 checked detector-negative windows.

## Statistical result

- Budget-120 recall delta: `+0.1200`, 95% CI `[0.0202, 0.2222]`.
- Budget-120 F1 delta: `+0.0065`, 95% CI `[-0.0981, 0.1134]`.
- Full-budget recall delta: `+0.1600`, 95% CI `[0.0460, 0.2737]`.
- Full-budget F1 delta: `-0.2271`, 95% CI `[-0.3210, -0.1320]`.
- Full-budget McNemar: `p=2.61e-19`, favoring BM25 overall.

## Quality gate

Step 9 passes all 14 checks and five hard stops. The current result table is traceable and finalizable.

## Claim boundary

Allowed current claim:

> Topology-aware retrieval improves evidence availability and difficult-fault recall, especially for network delay, but the current decision policy increases false positives, cost, and aggregate error.

Not claimed:

- full root cause analysis;
- production readiness;
- autonomous remediation;
- superiority over all RAG methods;
- generalization beyond Nezha.

## Remaining work

The current package is suitable for a thesis and workshop-oriented submission. A stronger full paper requires:

1. calibrated topology routing;
2. independent fresh-cache repetitions;
3. a second workload or dataset;
4. citation-backed Related Work.

See `FULL_PAPER_IMPROVEMENT_PLAN.md`.

## Primary artifacts

```text
outputs/phase2/step7_rerun/
outputs/phase2/step7_view_b/
outputs/phase2/paper_tables/
outputs/phase2/figures/
outputs/phase2/quality_gate/
reports/phase2_thesis_insert_sections.md
paper/draft.md
```
