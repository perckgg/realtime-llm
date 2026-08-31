# PHASE2_EXPERIMENT_CONTRACT.md

> **Phase 2 Experiment Contract**  
> Research direction: **Topology-Aware RAG with Weighted Context Fusion for LLM-based anomaly diagnosis in microservice monitoring**  
> Dataset: **IntelligentDDS/Nezha**  
> Status: Draft v0.2 (bootstrap initialized)

---

## 1. Purpose

This document defines the experimental contract for Phase 2. The purpose is to ensure that all Phase 2 experiments are reproducible, comparable with Phase 1 results, and aligned with the intended paper contribution.

Phase 1 has already validated the feasibility of the hybrid monitoring pipeline:

```text
Metric → Preprocessing → Anomaly Detector → Alert Candidate
→ LLM Gate → RAG Retrieval → LLM-as-a-Judge
→ Decision/Fallback → Audit/Evaluation
```

Phase 2 does **not** restart dataset auditing from scratch. Instead, Phase 2 reuses the existing Nezha audit artifacts, baseline results, and evaluation pipeline from Phase 1, then adds a new retrieval method:

```text
Topology-Aware RAG + Weighted Context Fusion
```

The main goal of Phase 2 is to answer the following research question:

> Can service-topology-aware context retrieval improve the quality of retrieved evidence and downstream LLM-based alert diagnosis compared with BM25/time-based RAG baselines?

---

## 2. Source of Truth

The source of truth for Phase 2 experiments is the existing Phase 1 experiment package and audit outputs.

### 2.1 Reused documents and reports

```text
EXPERIMENT_REPORT_FOR_SUBMISSION.md
DATASET_REPORT.md
reports/audit_failure_analysis.md
reports/audit_failure_by_fault_type.csv
reports/audit_failure_by_service.csv
reports/audit_failure_by_pod.csv
reports/audit_failure_hotspots.csv
reports/consolidated_experiment_metrics.csv
reports/evaluation_criteria_mapping.md
reports/tradeoff_analysis_table.md
reports/experiment_summary_no_rerun.md
reports/thesis_insert_sections.md
```

### 2.2 Reused audit/output folders

```text
nezha_setup/outputs/**/audit/*_audit.jsonl
nezha_setup/outputs/phase3_smoke/ablation/
nezha_setup/outputs/phase4_benchmark/results/
nezha_setup/outputs/phase5_context_rescue/results/
nezha_setup/outputs/real_llm_stratified/
nezha_setup/outputs/local_first_ollama_smoke/
```

### 2.3 Rule

Phase 2 must not mix untracked manual outputs with formal experimental results. Any result used in the paper or thesis must be traceable to:

```text
config file → experiment command → audit JSONL → summary CSV/JSON/MD
```

### 2.4 Phase boundary directories

To avoid mixing Phase 1 and Phase 2 artifacts, the repository uses explicit output namespaces:

```text
outputs/phase1/  # index of historical Phase 1 artifacts (legacy outputs stay in place)
outputs/phase2/  # all new Phase 2 artifacts
```

Code boundary for new implementation:

```text
src/phase1/      # logical inheritance boundary
src/phase2/      # new Stage-2 modules
```

---

## 3. Dataset Policy

### 3.1 Main dataset

The main dataset for Phase 2 is:

```text
IntelligentDDS/Nezha
```

Nezha is selected because it contains the required observability sources for the proposed method:

```text
metric + log + trace + traceid + fault list
```

Phase 1 processed Nezha into metric rows and context events and used it as the primary dataset for hybrid RAG + LLM judge experiments.

### 3.2 Dataset not used for main RAG paper results

The Microsoft cloud-monitoring-dataset is **not** used for the main Phase 2 RAG evaluation because it does not contain real log/trace observability context. It may be mentioned in the thesis as a metric-only feasibility benchmark, but it must not be used as evidence for RAG or topology-aware retrieval effectiveness.

### 3.3 Dataset audit status

Dataset audit is considered completed before Phase 2. Phase 2 starts from existing audit artifacts and does not repeat the dataset audit step unless a data integrity issue is discovered.

---

## 4. Phase 2 Main Contribution

The proposed Phase 2 method is:

```text
Topology-Aware Weighted Context Fusion
```

The method extends the existing BM25/time-based retrieval pipeline by incorporating service dependency topology into context ranking.

The core scoring function is:

```text
Score_final(c, q)
= α · BM25_norm(c, q)
+ β · TimeSim(c, t0)
+ γ · GraphSim(sc, s0)
```

Where:

```text
c  = context candidate
q  = query generated from an alert
t0 = alert timestamp
s0 = alerted service
sc = service associated with context candidate c
```

### 4.1 BM25 normalization

```text
BM25_norm(c, q)
= (BM25(c, q) − BM25_min) / (BM25_max − BM25_min + ε)
```

Where BM25 scores are normalized within the candidate pool of the same alert. The candidate pool includes lexical candidates and graph-expanded candidates.

### 4.2 Temporal similarity

```text
TimeSim(c, t0) = exp(− |tc − t0| / τ_time)
```

This score assigns higher values to context events closer to the alert timestamp.

### 4.3 Graph similarity

```text
GraphSim(sc, s0) = 1 / (1 + dG(sc, s0))
```

Where `dG(sc, s0)` is the shortest-path distance between the context service and the alerted service on the undirected projection of the service dependency graph.

Special cases:

```text
dG = 0 → GraphSim = 1.0
dG = 1 → GraphSim = 0.5
dG = ∞ → GraphSim = 0.0
```

The undirected projection is used only for retrieval ranking. The original directed service dependency graph should be preserved for later fault propagation or RCA analysis.

### 4.4 Weight constraints

```text
α, β, γ ≥ 0
α + β + γ = 1
```

Since all component scores are bounded in `[0, 1]` and the weights form a convex combination, the final score is also bounded in `[0, 1]`.

---

## 5. Experiment Scope

Phase 2 experiments are divided into three levels.

### 5.1 Level A — Retrieval-only evaluation

Goal: evaluate whether topology-aware fusion retrieves better context before involving the LLM.

This level does not call an external LLM.

Methods:

```text
M0: BM25-only
M1: BM25 + TimeSim
M2: BM25 + GraphSim
M3: BM25 + TimeSim + GraphSim
```

Main proposed method:

```text
M3: BM25 + TimeSim + GraphSim
```

### 5.2 Level B — LLM decision evaluation

Goal: evaluate whether better retrieval improves downstream alert validation / anomaly diagnosis.

Methods:

```text
Detector-only
LLM without RAG
Hybrid BM25 top-6
Hybrid BM25 top-10
Topology-Aware Fusion top-6
Context Rescue
```

Important note:

```text
Context Rescue is an architecture-enhanced baseline, not a retrieval-only ablation.
```

### 5.3 Level C — Weight ablation

Goal: evaluate the effect of α, β, and γ.

Planned settings:

```text
A0: α=1.00, β=0.00, γ=0.00  # BM25 only
A1: α=0.50, β=0.50, γ=0.00  # BM25 + Time
A2: α=0.50, β=0.00, γ=0.50  # BM25 + Graph
A3: α=0.40, β=0.30, γ=0.30  # Balanced
A4: α=0.35, β=0.25, γ=0.40  # Topology-heavy
```

The final selected weights must be selected on a validation split or reported as ablation settings. The test set must not be used for tuning.

---

## 6. Window Selection Policy

Phase 2 should use the same style of stratified window selection as Phase 1 real-LLM experiments.

### 6.1 Debug run

```text
50 windows
Purpose: validate graph construction, candidate expansion, fusion score, output schema
```

### 6.2 Paper-small run

```text
300 windows
Purpose: compare against Phase 4 and Phase 5 style baselines
```

### 6.3 Paper-main run

```text
500 windows
Purpose: evaluate at the same scale as the existing real-LLM 500-window run
Suggested split: 100 positive + 400 negative if available from the existing stratified setup
```

### 6.4 Required fault-type coverage

The selected window set should include, where available:

```text
network_delay
cpu_contention
cpu_consumed
exception
return
none
```

`network_delay` must be analyzed separately because Phase 1 failure analysis identified it as a difficult fault type and a major source of false negatives.

---

## 7. Baseline Policy

### 7.1 Baselines inherited from Phase 1

The following baselines should be reused from existing Phase 1 outputs when possible:

```text
detector_only
llm_without_rag
hybrid_bm25_top6
hybrid_bm25_top10
phase5_context_rescue
real_llm_500w_cache_replay
```

### 7.2 Baseline interpretation

| Baseline | Role in Phase 2 |
|---|---|
| detector_only | Metric-only baseline |
| llm_without_rag | Shows that LLM without retrieved context is unreliable |
| hybrid_bm25_top6 | Main BM25 RAG baseline |
| hybrid_bm25_top10 | Tests whether more context alone improves results |
| phase5_context_rescue | Strong architecture-enhanced baseline |
| real_llm_500w_cache_replay | Large-scale cached LLM reference run |

### 7.3 Fairness rule

The proposed Topology-Aware Fusion method must be evaluated on the same window set as the selected BM25 baseline.

If a baseline uses a different window set or different budget policy, this must be explicitly stated.

---

## 8. Proposed Method Output Schema

Each Phase 2 output record should extend the existing audit schema with topology-aware retrieval fields.

Required fields:

```json
{
  "run_id": "...",
  "window_id": "...",
  "alert_id": "...",
  "timestamp": "...",
  "service_id": "...",
  "node_id": "...",
  "fault_type": "...",
  "ground_truth": "...",
  "anomaly_score": 0.0,
  "retrieval_backend": "topology_aware_fusion",
  "top_k": 6,
  "alpha": 0.4,
  "beta": 0.3,
  "gamma": 0.3,
  "candidate_pool_size": 0,
  "bm25_candidate_count": 0,
  "graph_candidate_count": 0,
  "duplicates_removed": 0,
  "retrieved_context_count": 0,
  "context_coverage": false,
  "retrieval_latency_ms": 0.0,
  "avg_graph_distance": 0.0,
  "final_decision": "route_alert|suppress|manual_review",
  "llm_calls": 0,
  "actual_api_calls": 0,
  "cache_hits": 0,
  "json_valid": true
}
```

Each retrieved context should include:

```json
{
  "context_id": "...",
  "context_type": "log|trace|metric",
  "context_service": "...",
  "context_timestamp": "...",
  "bm25_raw": 0.0,
  "bm25_norm": 0.0,
  "time_sim": 0.0,
  "graph_distance": 0,
  "graph_sim": 0.0,
  "score_final": 0.0,
  "rank": 1,
  "content_preview": "..."
}
```

---

## 9. Metrics

### 9.1 Classification metrics

```text
Precision
Recall
F1
False Positive Rate
FP reduction vs detector
Manual review rate
```

### 9.2 Retrieval metrics

```text
Context coverage
Retrieved context count
Avg context tokens
Retrieval latency
```

### 9.3 Topology-aware metrics

```text
Graph coverage
Avg graph distance
Graph candidate count
Topology-expanded context ratio
Network-delay context coverage
```

### 9.4 LLM/cost metrics

```text
LLM calls
Actual API calls
Cache hits
Cache hit rate
JSON valid rate
Input tokens
Output tokens
Estimated cost
Average LLM latency
```

### 9.5 Required breakdowns

All main metrics should be broken down by:

```text
fault_type
service_id
pod/node_id, if available
```

The following breakdown is required:

```text
network_delay vs non-network_delay
```

---

## 10. Decision and Budget Policy

Phase 2 should inherit the safer decision policy from the corrected Phase 1 setup.

### 10.1 LLM budget exhausted

```yaml
decision:
  llm_budget_exhausted_action: manual_review
```

Rationale: an alert that has not been confirmed by LLM due to budget exhaustion should not be counted as a confirmed routed alert.

### 10.2 Evidence guard

```yaml
decision:
  require_evidence_for_true_alert: true
```

If the LLM predicts `true_alert` but provides no supporting evidence, the decision should be downgraded to manual review rather than routed directly.

### 10.3 Cache policy

LLM response cache should be enabled for repeated runs.

```text
Cache-enabled replay results must report actual_api_calls separately from logical LLM calls.
```

---

## 11. Planned Config Files

Suggested Phase 2 config files:

```text
nezha_setup/config/experiment_phase2_retrieval_only_topology.yaml
nezha_setup/config/experiment_phase2_topology_fusion_300w.yaml
nezha_setup/config/experiment_phase2_topology_fusion_500w.yaml
nezha_setup/config/experiment_phase2_alpha_beta_gamma_ablation.yaml
nezha_setup/config/experiment_phase2_topology_cache_replay.yaml
```

---

## 12. Planned Scripts

Suggested implementation scripts:

```text
scripts/build_phase2_manifest.py
scripts/build_service_graph.py
scripts/run_phase2_retrieval_eval.py
scripts/run_phase2_topology_fusion.py
scripts/run_phase2_ablation.py
scripts/generate_phase2_paper_tables.py
scripts/generate_phase2_figures.py
```

Suggested source modules:

```text
src/retrieval/graph_builder.py
src/retrieval/topology_candidate_expander.py
src/retrieval/fusion_ranker.py
src/retrieval/topology_aware_retriever.py
src/evaluation/topology_metrics.py
```

---

## 13. Required Output Files

### 13.1 Manifest and graph outputs

```text
outputs/phase2/audit_manifest.json
outputs/phase2/window_index.csv
outputs/phase2/service_graph_edges.csv
outputs/phase2/service_graph_summary.json
outputs/phase2/service_graph_directed.json
outputs/phase2/service_graph_undirected.json
```

### 13.2 Retrieval-only outputs

```text
outputs/phase2/retrieval/phase2_retrieval_summary.csv
outputs/phase2/retrieval/phase2_retrieval_by_fault_type.csv
outputs/phase2/retrieval/phase2_retrieval_by_service.csv
outputs/phase2/retrieval/topk_contexts.jsonl
```

### 13.3 LLM decision outputs

```text
outputs/phase2/topology_fusion/results/hybrid_summary.md
outputs/phase2/topology_fusion/results/hybrid_summary.csv
outputs/phase2/topology_fusion/results/hybrid_results.json
outputs/phase2/topology_fusion/audit/topology_fusion_audit.jsonl
```

### 13.4 Ablation outputs

```text
outputs/phase2/ablation/alpha_beta_gamma_ablation.csv
outputs/phase2/ablation/ablation_by_fault_type.csv
outputs/phase2/ablation/ablation_summary.md
```

### 13.5 Paper-ready outputs

```text
outputs/phase2/paper_tables/main_result_table.csv
outputs/phase2/paper_tables/fault_type_breakdown.csv
outputs/phase2/paper_tables/ablation_table.csv
outputs/phase2/paper_tables/cost_latency_table.csv
outputs/phase2/figures/f1_comparison.png
outputs/phase2/figures/context_coverage_comparison.png
outputs/phase2/figures/network_delay_recall.png
outputs/phase2/figures/alpha_beta_gamma_ablation.png
outputs/phase2/figures/service_graph_example.png
```

---

## 14. Main Paper Tables

### 14.1 Main comparison table

```text
Method | Precision | Recall | F1 | FPR | Context Coverage | Retrieval Latency | LLM Calls
```

Methods:

```text
Detector-only
LLM without RAG
BM25 RAG top-6
BM25 RAG top-10
Topology-Aware Fusion top-6
Context Rescue
```

### 14.2 Fault type breakdown table

```text
Method | Fault Type | Precision | Recall | F1 | FP | FN | Context Coverage
```

Required focus:

```text
network_delay
cpu_contention
none
```

### 14.3 Weight ablation table

```text
α | β | γ | Precision | Recall | F1 | FPR | Coverage | Latency | Network-delay Recall
```

### 14.4 Cost and feasibility table

```text
Method | LLM Calls | Actual API Calls | Cache Hits | JSON Valid | Avg LLM Latency | Estimated Cost
```

---

## 15. Paper Claim Boundaries

Phase 2 paper should make the following claims only if supported by results.

### 15.1 Allowed main claim

```text
Topology-aware context retrieval improves retrieved evidence quality and/or downstream LLM alert diagnosis compared with BM25/time-based RAG baselines on Nezha.
```

### 15.2 Preferred framing

```text
LLM-based anomaly diagnosis in microservices benefits from context that is not only temporally close, but also topologically close.
```

### 15.3 Claims to avoid unless directly measured

Avoid claiming full root cause analysis unless root-cause service labels or equivalent ground truth are explicitly available.

Avoid claiming real-time production readiness. The current scope is controlled experimental evaluation and feasibility-oriented pipeline assessment.

Avoid presenting Context Rescue as a retrieval-only ablation because it changes candidate promotion behavior and LLM budget conditions.

---

## 16. Immediate Implementation Checklist

```text
[x] Create this PHASE2_EXPERIMENT_CONTRACT.md file
[x] Create audit_manifest.json from existing audit outputs
[x] Create window_index.csv for 300/500 selected Nezha windows
[x] Reproduce selected Phase 1 baseline metrics from existing CSV/JSON (via baseline_reference snapshot)
[x] Freeze Phase 2 input window/baseline hashes via input_freeze.json
[x] Implement graph_builder.py
[x] Generate service_graph_edges.csv
[x] Generate service_graph_summary.json
[x] Implement topology_candidate_expander.py
[x] Implement fusion_ranker.py
[x] Implement topology_aware_retriever.py
[x] Generate candidate_pool_debug.jsonl and topk_contexts_debug.jsonl
[x] Run retrieval-only comparison: BM25 vs BM25+Time vs BM25+Graph vs full fusion
[x] Run αβγ ablation
[x] Attach Topology-Aware Fusion to the hybrid pipeline
[ ] Run LLM decision evaluation with cache enabled
[ ] Generate paper tables and figures
[ ] Start paper draft using the final methodology and results
```

---

## 17. Definition of Done

Phase 2 experiment setup is considered ready for paper writing when the following artifacts exist:

```text
[x] PHASE2_EXPERIMENT_CONTRACT.md
[x] audit_manifest.json
[x] window_index.csv
[x] input_freeze.json
[x] service_graph_summary.json
[x] phase2_retrieval_summary.csv
[x] phase2_retrieval_by_fault_type.csv
[x] topology_fusion_audit.jsonl
[x] hybrid_summary.csv for Topology-Aware Fusion
[x] alpha_beta_gamma_ablation.csv
[ ] main_result_table.csv
[ ] fault_type_breakdown.csv
[ ] at least 4 paper-ready figures
```

---

## 18. Notes for Thesis Integration

The thesis can use a broader system framing than the paper.

Paper focus:

```text
Topology-Aware RAG + Weighted Context Fusion
```

Thesis focus:

```text
Metric detector + context rescue + topology-aware retrieval + LLM judge + audit + dashboard
```

Dashboard, local-first scheduling, fallback policies, and cost/cache analysis are useful for the thesis and defense demo, but they should not distract from the paper's main contribution.
