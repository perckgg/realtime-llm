# Full-paper Improvement Plan

## 1. Current research position

The current Phase 2 package is reproducible and thesis-ready:

- View A and View B use the frozen `paper_500` split.
- Step 8 provides four paper tables and five figures.
- Step 9 passes all 14 checks and all five hard-stop conditions.
- The current result is a trade-off, not an aggregate win:
  - topology improves full-budget recall from `0.5800` to `0.7400`;
  - `network_delay` recall improves from `0.3750` to `0.7000`;
  - aggregate F1 decreases from `0.7030` to `0.4759`;
  - FPR increases from `0.0175` to `0.3425`;
  - estimated cost increases from `0.0628` to `0.1669` USD.

The full-paper objective is therefore not to hide the negative result. It is to determine whether topology-aware evidence can retain its recall benefit after decision calibration, and whether that result is stable and externally valid.

## 2. Target contribution

The desired contribution is:

> A calibrated topology-aware evidence retrieval and alert-validation method that improves difficult-fault recall without an unacceptable increase in false positives, cost, or manual review.

The paper must remain a measured trade-off study if the calibration gates are not met.

## 3. Research questions

| ID | Research question |
|---|---|
| RQ1 | Why does topology-aware context increase false positives on normal windows? |
| RQ2 | Can evidence and routing calibration preserve the `network_delay` recall gain while controlling FPR? |
| RQ3 | Are the View A results stable across independent fresh-cache LLM runs? |
| RQ4 | Does the calibrated method generalize to a second workload or dataset? |
| RQ5 | What quality gain is obtained per API call, token, and millisecond? |

## 4. Full-paper success gates

All gates are evaluated on a held-out multi-service test split that is not used for calibration.

### Minimum defensible calibrated-result gate

```text
Network-delay recall delta vs BM25 >= +0.15
Aggregate FPR <= BM25 FPR + 0.03
Aggregate F1 >= BM25 F1 - 0.02
Estimated cost <= 1.5x BM25 cost
JSON valid rate >= 0.99
```

### Strong aggregate-improvement gate

```text
Bootstrap 95% CI for F1 delta is above 0
McNemar p < 0.05 and favors calibrated topology
Recall is not lower than BM25
FPR is not higher than BM25 by more than 0.02
```

If only the minimum gate passes, the paper claim remains fault-specific. If the strong gate passes, the paper may claim aggregate downstream improvement on the evaluated workloads.

## 5. Work packages

### WP0 — Freeze the current baseline

Purpose: prevent later experiments from overwriting the accepted Step 9 package.

Deliverables:

```text
outputs/phase2/quality_gate/step9_quality_gate_report.json
outputs/phase2/paper_tables/
outputs/phase2/figures/
outputs/phase2/step7_rerun/
outputs/phase2/step7_view_b/
```

Actions:

1. Record hashes for the final tables, reports, configs, and audit JSONL.
2. Treat current View A/View B outputs as the immutable baseline.
3. Write all improvement experiments under `outputs/full_paper/`.

### WP1 — False-positive mechanism analysis

Purpose: explain the 137 normal-window false alerts produced by full-budget topology.

Required analysis dimensions:

- service mismatch between alert and retrieved evidence;
- graph-only versus BM25-supported evidence;
- topology-context ratio;
- graph distance;
- LLM confidence;
- evidence count and evidence-service consistency;
- normal-window operational patterns that resemble injected faults.

Planned artifact:

```text
outputs/full_paper/error_analysis/topology_false_positive_cases.csv
outputs/full_paper/error_analysis/topology_false_positive_categories.md
```

Exit criterion: at least 90% of topology false positives are assigned to an explicit, reproducible category.

### WP2 — Offline policy calibration

Purpose: reduce API cost by replaying existing full-budget LLM outputs before making new calls.

Candidate policies:

1. Confidence thresholds: `0.80`, `0.85`, `0.90`, `0.95`.
2. Require at least one evidence item from the alert service.
3. Require BM25 support in addition to graph-only evidence.
4. Reject or send to manual review when negative evidence conflicts with the alert.
5. Cap routing when topology-only context ratio exceeds a tuned threshold.
6. Require consistency between fault type, top metric features, and evidence service.

Selection protocol:

- create a new multi-service calibration split;
- never tune on the held-out final split;
- optimize F1 subject to the minimum FPR and recall gates;
- select at most two policies for fresh-LLM confirmation.

Planned implementation:

```text
scripts/full_paper/analyze_topology_false_positives.py
scripts/full_paper/replay_policy_calibration.py
outputs/full_paper/calibration/policy_sweep.csv
outputs/full_paper/calibration/selected_policies.json
```

### WP3 — Freeze a full-paper split v2

The existing `paper_300` split is unsuitable for tuning because it contains one service. Create non-overlapping, stratified, multi-service sets:

```text
calibration_300_v2
test_500_v2
```

Stratify by:

- ground truth;
- fault type;
- service;
- dataset date/source;
- normal versus injected-fault windows.

Required checks:

- no shared `window_id`;
- no temporal leakage where practical;
- fixed seed and SHA-256 hashes;
- comparable service/fault distributions;
- all split metadata stored before calibration.

### WP4 — Independent fresh-cache repetitions

Run at least three independent repetitions for:

```text
BM25 top-6
Uncalibrated topology top-6
Best calibrated topology top-6
LLM without RAG
```

Controls:

- same held-out windows;
- same model version, prompt, temperature, and budget;
- separate fresh cache per method and repetition;
- no cache sharing in the reported first-pass cost analysis.

Report:

- mean and standard deviation;
- per-window paired bootstrap confidence intervals;
- exact McNemar tests;
- between-run decision disagreement;
- API calls, retries, tokens, latency, and cost.

Planned artifact:

```text
outputs/full_paper/repetitions/repetition_manifest.json
outputs/full_paper/repetitions/repeated_run_summary.csv
outputs/full_paper/repetitions/paired_statistics.json
```

### WP5 — External validation

Preferred option: controlled Online Boutique deployment using `online_boutique_streaming_setup/`.

Minimum dataset design:

- at least three services;
- normal periods and at least three fault types;
- repeated fault injections;
- metric, log, and trace collection;
- explicit fault interval and affected-service labels;
- frozen train/calibration/test windows.

Minimum external-validation claim gate:

```text
Topology recall gain has the same direction as Nezha
FPR remains within the minimum calibrated-result gate
No dataset-specific prompt or threshold is tuned on the external test set
```

Fallback option: use another public microservice observability dataset with compatible metrics, logs, traces, and fault labels.

### WP6 — Related work and novelty positioning

Perform a citation-backed review of:

- graph-aware retrieval and GraphRAG;
- microservice root-cause localization;
- LLM-based observability and alert triage;
- selective prediction and abstention;
- cost-aware LLM routing.

Required output:

```text
paper/related_work_matrix.csv
paper/related_work.md
```

The novelty statement must identify what differs from graph retrieval alone: frozen operational evaluation, evidence-aware abstention, cache/API accounting, and fault-specific recall/FPR/cost analysis.

## 6. Experiment matrix

| Stage | Split | Methods | LLM mode | Purpose |
|---|---|---|---|---|
| Error analysis | existing `paper_500` | BM25, topology | replay | Explain current false positives |
| Calibration | `calibration_300_v2` | policy variants | replay first | Select at most two policies |
| Confirmation | `test_500_v2` | BM25, topology, calibrated topology, no RAG | fresh API | Main full-paper result |
| Repetition | `test_500_v2` | same four methods | three fresh runs | Stochastic stability |
| External validation | second workload | selected baselines | fresh API | Generalization |

## 7. Statistical protocol

1. Use per-window paired comparisons.
2. Report 10,000-sample paired bootstrap confidence intervals.
3. Use exact McNemar tests for paired correctness.
4. Correct multiple comparisons when evaluating multiple selected policies.
5. Report effect sizes, not only p-values.
6. Keep calibration and test decisions completely separated.
7. Treat manual review as abstention, never as `route_alert`.

## 8. Resource and cost controls

- Use offline replay for threshold and evidence-policy sweeps.
- Limit fresh API confirmation to the selected policies.
- Estimate API calls before every run.
- Store one cache per method, split, and repetition.
- Stop a run if the frozen hash, model, prompt, or config differs.
- Preserve actual API calls separately from logical calls and cache hits.

## 9. Proposed schedule

| Week | Work |
|---|---|
| 1 | WP0 freeze, WP1 false-positive analysis |
| 2 | WP2 offline calibration and policy selection |
| 3 | WP3 split v2 and fresh confirmation |
| 4 | WP4 independent repetitions and statistics |
| 5 | WP5 external dataset collection/evaluation |
| 6 | WP6 related work and manuscript revision |

## 10. Claim ladder

### Current accepted claim

Topology-aware retrieval improves evidence availability and difficult-fault recall, especially for `network_delay`, but increases false positives, cost, and aggregate error under the current policy.

### Claim after minimum calibrated-result gate

Calibrated topology-aware retrieval preserves fault-specific recall gains while controlling false-positive and cost growth on the evaluated workloads.

### Claim after strong aggregate and external-validation gates

Calibrated topology-aware evidence retrieval improves downstream LLM alert validation over BM25 on multiple microservice workloads.

## 11. Definition of done

The full-paper improvement track is complete only when:

```text
[ ] Current Step 9 baseline is hash-frozen
[ ] False-positive categories are documented
[ ] Calibration and held-out splits are frozen and non-overlapping
[ ] At least one calibrated policy passes the minimum result gate
[ ] Three fresh-cache repetitions are complete
[ ] Paired statistics and run disagreement are reported
[ ] A second workload is evaluated
[ ] Related work includes verified citations
[ ] Paper tables and figures are regenerated from full-paper outputs
[ ] A new quality gate passes before claims are updated
```
