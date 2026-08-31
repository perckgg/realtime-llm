# PHASE2_FULL_EXECUTION_PLAN.md

> **Full Execution Plan for Phase 2 Experiments**  
> Direction: **Topology-Aware RAG + Weighted Context Fusion for LLM-based anomaly diagnosis in microservice monitoring**  
> Dataset: **IntelligentDDS/Nezha**  
> Status: Draft v1.0  
> Scope: Executable plan based on `PHASE2_EXPERIMENT_CONTRACT.md`, assuming Nezha audit is already completed.

---

## 0. Objective

This document defines the executable Phase 2 plan for running experiments, generating paper-ready results, and preparing thesis-ready artifacts.

Phase 2 does **not** restart dataset auditing. It reuses Phase 1 audit artifacts, baseline summaries, and hybrid monitoring pipeline, then adds the new contribution:

```text
Topology-Aware RAG + Weighted Context Fusion
```

The main experimental objective is:

> To evaluate whether service-topology-aware context retrieval improves evidence retrieval quality and downstream LLM-based alert diagnosis compared with BM25/time-based RAG baselines.

The plan follows the contract structure:

```text
Freeze input → Build service graph → Implement topology-aware retrieval
→ Retrieval-only evaluation → α/β/γ ablation
→ Hybrid pipeline integration → LLM decision evaluation
→ Paper tables/figures → Quality gate → Submission/thesis packaging
```

---

## 1. Phase 2 Execution Timeline

| Step | Task | Expected Output |
|---:|---|---|
| 1 | Freeze baseline and input split | `window_index.csv`, `baseline_reference.csv`, `baseline_repro_check.md` |
| 2 | Build service topology graph | service graph CSV/JSON artifacts |
| 3 | Implement topology-aware retrieval core | candidate expansion, fusion ranking, retriever module |
| 4 | Run Level A retrieval-only evaluation | retrieval summary and breakdown CSV files |
| 5 | Run Level C α/β/γ ablation | ablation CSV/MD outputs |
| 6 | Integrate retriever into hybrid pipeline and audit schema | new backend `topology_aware_fusion` |
| 7 | Run Level B LLM decision evaluation | hybrid summary, results JSON, audit JSONL |
| 8 | Generate paper-ready tables and figures | main result tables and figures |
| 9 | Run quality gate | traceability and consistency checks |
| 10 | Package submission/thesis insert | Phase 2 report sections and claim boundary |

---

## 2. Milestones

### M1 — Graph + Retriever Core

Required artifacts:

```text
outputs/phase2/service_graph_summary.json
outputs/phase2/retrieval/candidate_pool_debug.jsonl
outputs/phase2/retrieval/topk_contexts_debug.jsonl
```

Success condition:

```text
The system can build the service graph, expand candidates using topology, compute BM25_norm, TimeSim, GraphSim, and Score_final, then output ranked top-k contexts.
```

---

### M2 — Retrieval-only + Ablation

Required artifacts:

```text
outputs/phase2/retrieval/phase2_retrieval_summary.csv
outputs/phase2/retrieval/phase2_retrieval_by_fault_type.csv
outputs/phase2/ablation/alpha_beta_gamma_ablation.csv
outputs/phase2/ablation/ablation_by_fault_type.csv
```

Success condition:

```text
BM25-only, BM25+Time, BM25+Graph, and full fusion are compared on the same window set, with separate analysis for network_delay.
```

---

### M3 — LLM Evaluation + Audit

Required artifacts:

```text
outputs/phase2/topology_fusion/audit/topology_fusion_audit.jsonl
outputs/phase2/topology_fusion/results/hybrid_summary.csv
outputs/phase2/topology_fusion/results/hybrid_results.json
```

Success condition:

```text
Topology-Aware Fusion is integrated into the existing hybrid pipeline and evaluated against selected baselines under the same split and documented budget policy.
```

---

### M4 — Paper-ready Package

Required artifacts:

```text
outputs/phase2/paper_tables/main_result_table.csv
outputs/phase2/paper_tables/fault_type_breakdown.csv
outputs/phase2/paper_tables/ablation_table.csv
outputs/phase2/paper_tables/cost_latency_table.csv
outputs/phase2/figures/f1_comparison.png
outputs/phase2/figures/context_coverage_comparison.png
outputs/phase2/figures/network_delay_recall.png
outputs/phase2/figures/alpha_beta_gamma_ablation.png
```

Success condition:

```text
The Phase 2 experiment package is ready to support paper writing and thesis result chapters.
```

---

## 3. Step 1 — Freeze Baseline and Input Split

### Purpose

Before implementing the proposed method, freeze all inputs and baseline references to ensure fair comparison and reproducibility.

### Tasks

```text
[ ] Lock outputs/phase2/window_index.csv for 300-window and 500-window settings
[ ] Lock outputs/phase2/baseline_reference.csv
[ ] Ensure every method uses the same split
[ ] Recompute baseline metrics from baseline_reference.csv
[ ] Compare recomputed metrics with Phase 1 report numbers
[ ] Record source run/config for each baseline row
[ ] Mark smoke/debug runs as non-paper results
```

### Baselines to include

```text
detector_only
llm_without_rag
hybrid_bm25_top6
hybrid_bm25_top10
phase5_context_rescue
real_llm_500w_cache_replay, if 500-window comparison is used
```

### Important rule

`Context Rescue` must be labeled as an **architecture-enhanced baseline**, not as a retrieval-only ablation, because it changes candidate promotion behavior and LLM call conditions.

### Deliverables

```text
outputs/phase2/window_index.csv
outputs/phase2/baseline_reference.csv
outputs/phase2/baseline_repro_check.md
```

### Quality checks

```text
[ ] Baseline rows have source config and source output path
[ ] 300-window and 500-window splits are explicitly identified
[ ] Baseline metrics can be recomputed from stored CSV/JSON files
[ ] Proposed method will run on the same window set as the BM25 baseline
```

---

## 4. Step 2 — Build Service Topology Graph

### Purpose

Build the service dependency graph required by `GraphSim(sc, s0)` and topology-aware candidate expansion.

### Tasks

```text
[ ] Implement src/retrieval/graph_builder.py
[ ] Load Nezha trace/span data
[ ] Extract caller/callee or parent-child span relationships
[ ] Build directed service dependency graph
[ ] Build undirected projection for retrieval ranking
[ ] Compute shortest-path distance dG(sc, s0)
[ ] Handle disconnected graph pairs: dG = ∞ → GraphSim = 0
[ ] Compute graph-level summary statistics
[ ] Validate service coverage for alerts and context candidates
```

### Required graph validation metrics

```text
num_services
num_directed_edges
num_undirected_edges
num_connected_components
isolated_services
alert_service_graph_coverage
context_service_graph_coverage
disconnected_pair_ratio
```

### Deliverables

```text
outputs/phase2/service_graph_edges.csv
outputs/phase2/service_graph_directed.json
outputs/phase2/service_graph_undirected.json
outputs/phase2/service_graph_summary.json
```

### Quality checks

```text
[ ] Directed graph preserves original caller/callee direction
[ ] Undirected projection is used only for retrieval ranking
[ ] Directed graph remains available for later RCA/fault propagation analysis
[ ] Services in alerts can be mapped to graph nodes
[ ] Services in context candidates can be mapped to graph nodes
```

---

## 5. Step 3 — Implement Topology-Aware Retrieval Core

### Purpose

Implement the proposed retrieval backend:

```text
topology_aware_fusion
```

This backend expands candidates using service topology and ranks them using Weighted Context Fusion.

### Source modules

```text
src/retrieval/topology_candidate_expander.py
src/retrieval/fusion_ranker.py
src/retrieval/topology_aware_retriever.py
```

### Candidate pool definition

```text
C = C_BM25 ∪ C_graph
```

Where:

```text
C_BM25 = candidates retrieved by existing BM25/time-based retrieval
C_graph = candidates from services near the alerted service in the service graph
```

### Fusion formula

```text
Score_final(c, q)
= α · BM25_norm(c, q)
+ β · TimeSim(c, t0)
+ γ · GraphSim(sc, s0)
```

Where:

```text
BM25_norm(c, q)
= (BM25(c, q) − BM25_min) / (BM25_max − BM25_min + ε)

TimeSim(c, t0)
= exp(− |tc − t0| / τ_time)

GraphSim(sc, s0)
= 1 / (1 + dG(sc, s0))
```

Weight constraints:

```text
α, β, γ ≥ 0
α + β + γ = 1
```

### Tasks

```text
[x] Implement topology candidate expansion
[x] Implement duplicate removal by context_id
[x] Implement BM25 normalization within candidate pool
[x] Implement TimeSim
[x] Implement GraphSim
[x] Implement Score_final
[x] Validate Score_final ∈ [0,1]
[x] Log score components for each retrieved context
[x] Output ranked top-k contexts
```

### Debug outputs

```text
outputs/phase2/retrieval/candidate_pool_debug.jsonl
outputs/phase2/retrieval/topk_contexts_debug.jsonl
```

### Example candidate pool debug record

```json
{
  "window_id": "...",
  "alert_service": "...",
  "bm25_candidate_count": 60,
  "graph_candidate_count": 40,
  "duplicates_removed": 8,
  "candidate_pool_size": 92
}
```

### Example ranked context record

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

### Quality checks

```text
[x] BM25_min/BM25_max are computed per candidate pool
[x] ε is used to avoid division by zero
[x] GraphSim = 0 when dG = ∞
[x] Score_final is bounded in [0,1]
[x] top_k output is deterministic for same input/config
```

---

## 6. Step 4 — Run Level A: Retrieval-only Evaluation

### Purpose

Evaluate context retrieval quality before involving the LLM. This isolates the contribution of Topology-Aware Fusion from LLM behavior, budget limits, and cache effects.

### Methods

```text
M0 = BM25-only
M1 = BM25 + TimeSim
M2 = BM25 + GraphSim
M3 = BM25 + TimeSim + GraphSim
```

### Execution order

```text
[x] Run 50-window debug
[x] Run 300-window paper-small evaluation
[x] If outputs are valid, run 500-window paper-main evaluation
```

### Metrics

```text
Context coverage
Retrieved context count
Avg context tokens
Retrieval latency
Graph coverage
Avg graph distance
Graph candidate count
Topology-expanded context ratio
Network-delay context coverage
```

### Required breakdowns

```text
fault_type
service_id
network_delay vs non-network_delay
```

### Deliverables

```text
outputs/phase2/retrieval/phase2_retrieval_summary.csv
outputs/phase2/retrieval/phase2_retrieval_by_fault_type.csv
outputs/phase2/retrieval/phase2_retrieval_by_service.csv
outputs/phase2/retrieval/topk_contexts.jsonl
```

### Quality checks

```text
[x] All methods use the same window set
[x] M0/M1/M2/M3 use the same top_k setting unless explicitly documented
[x] No external LLM calls are made in Level A
[x] Retrieval latency is measured separately from LLM latency
```

---

## 7. Step 5 — Run Level C: α/β/γ Ablation

### Purpose

Evaluate how lexical relevance, temporal proximity, and graph proximity contribute to the final retrieval score.

### Ablation settings

```text
A0: α=1.00, β=0.00, γ=0.00  # BM25 only
A1: α=0.50, β=0.50, γ=0.00  # BM25 + Time
A2: α=0.50, β=0.00, γ=0.50  # BM25 + Graph
A3: α=0.40, β=0.30, γ=0.30  # Balanced
A4: α=0.35, β=0.25, γ=0.40  # Topology-heavy
```

### Execution rule

```text
[x] Run A0..A4 on 300-window split first
[x] Analyze network_delay vs non-network_delay
[x] Select 1–2 best settings
[x] Confirm selected settings on 500-window split
```

### Metrics

```text
Precision, if decision-level evaluation is included
Recall, if decision-level evaluation is included
F1, if decision-level evaluation is included
FPR, if decision-level evaluation is included
Context coverage
Retrieval latency
Network-delay recall or coverage
Avg graph distance
```

### Deliverables

```text
outputs/phase2/ablation/alpha_beta_gamma_ablation.csv
outputs/phase2/ablation/ablation_by_fault_type.csv
outputs/phase2/ablation/ablation_summary.md
```

### Quality checks

```text
[x] Test set is not used for weight tuning
[x] Weight settings satisfy α, β, γ ≥ 0 and α + β + γ = 1
[x] Results clearly separate retrieval-only metrics from LLM decision metrics
```

---

## 8. Step 6 — Integrate into Hybrid Pipeline and Audit Schema

### Purpose

Attach `topology_aware_fusion` to the existing hybrid monitoring flow and ensure the audit schema captures all fields required by the Phase 2 contract.

### Tasks

```text
[x] Register retrieval_backend = topology_aware_fusion
[x] Connect topology-aware retriever to current hybrid pipeline
[x] Ensure decision policy inherits corrected Phase 1 policy
[x] Enable require_evidence_for_true_alert=true
[x] Enable llm_budget_exhausted_action=manual_review
[x] Extend audit schema with topology-aware fields
[x] Validate output JSONL schema
```

### Required audit fields

```text
candidate_pool_size
bm25_candidate_count
graph_candidate_count
duplicates_removed
bm25_norm
time_sim
graph_distance
graph_sim
score_final
retrieval_latency_ms
context_coverage
llm_calls
actual_api_calls
cache_hits
final_decision
json_valid
```

### Deliverables

```text
src/phase2/retrieval/topology_aware_retriever.py
src/phase2/retrieval/pipeline_adapter.py
updated audit schema or audit writer
nezha_setup/config/experiment_phase2_topology_fusion_300w.yaml
nezha_setup/config/experiment_phase2_topology_fusion_500w.yaml
```

### Quality checks

```text
[x] Existing BM25 backend still works
[x] New backend can be selected by config
[x] Audit JSONL includes all required fields
[x] Missing graph data does not crash the pipeline
[x] Cache/API call fields are separated
```

---

## 9. Step 7 — Run Level B: LLM Decision Evaluation

### Purpose

Evaluate whether improved retrieval leads to better downstream LLM-based alert validation/anomaly diagnosis.

### Baselines

```text
detector_only
llm_without_rag
hybrid_bm25_top6
hybrid_bm25_top10
topology_aware_fusion_top6
context_rescue
```

### Fairness requirement

Two result views should be produced:

#### View A — Retrieval-fair comparison

```text
BM25 top6 vs Topology-Aware Fusion top6
Same window set
Same top_k
Same LLM budget
Same decision policy
```

Current status:

```text
[x] Step 7 View A runner implemented at scripts/phase2/run_step7_view_a.py
[x] paper_300 and paper_500 run on frozen split with real/cache Gemini
[x] Report generated at outputs/phase2/step7_view_a/step7_view_a_report.md
[x] View B runner implemented at scripts/phase2/run_step7_view_b.py
[x] View B architecture-level comparison completed on frozen paper_500
[x] View B report generated at outputs/phase2/step7_view_b/step7_view_b_report.md
```

Before running Step 7, fix the Step 6 smoke-run limitation:

```text
[x] Use frozen windows from outputs/phase2/window_index.csv, not sequential max_windows slicing
[x] Add a runner that maps frozen window_id values to run_pipeline window_indices
[x] Verify paper_300/paper_500 selected row counts and window_id hashes match input_freeze.json
[x] Verify service/fault distribution matches frozen split before interpreting F1
```

#### View B — Architecture-level comparison

```text
Detector-only
LLM without RAG
BM25 top6
Topology-Aware Fusion top6
Context Rescue
```

In View B, Context Rescue must be clearly marked as architecture-enhanced.

### Execution order

```text
[x] Run 300-window evaluation first
[x] Validate audit and summary outputs
[x] Run 500-window cache-enabled evaluation
[x] Compare against baseline_reference.csv in the separated architecture-reference block
```

### Metrics

```text
Precision
Recall
F1
FPR
FP reduction vs detector
Manual review rate
LLM calls
Actual API calls
Cache hits
Cache hit rate
Context coverage
Avg context count
Retrieval latency
JSON valid rate
Input/output tokens
Estimated cost
```

### Deliverables

```text
outputs/phase2/step7_view_a/step7_view_a_report.md
outputs/phase2/step7_view_a/step7_view_a_report.csv
outputs/phase2/step7_view_a/step7_view_a_report.json
outputs/phase2/step7_view_a/results/
outputs/phase2/step7_view_a/audit/
outputs/phase2/step7_view_b/step7_view_b_report.md
outputs/phase2/step7_view_b/step7_view_b_report.csv
outputs/phase2/step7_view_b/step7_view_b_report.json
outputs/phase2/step7_view_b/results/
outputs/phase2/step7_view_b/audit/
```

### Quality checks

```text
[x] Proposed method uses same split as baseline
[x] Budget policy is documented
[x] Cache hits and actual API calls are reported separately
[x] Manual review is not counted as confirmed route_alert
[x] No smoke/debug run is mixed into main paper table
```

---

## 10. Step 8 — Generate Paper-ready Outputs

### Purpose

Generate tables and figures for paper submission and thesis result chapters.

### Paper tables

```text
outputs/phase2/paper_tables/main_result_table.csv
outputs/phase2/paper_tables/fault_type_breakdown.csv
outputs/phase2/paper_tables/ablation_table.csv
outputs/phase2/paper_tables/cost_latency_table.csv
```

### Required figures

```text
outputs/phase2/figures/f1_comparison.png
outputs/phase2/figures/context_coverage_comparison.png
outputs/phase2/figures/network_delay_recall.png
outputs/phase2/figures/alpha_beta_gamma_ablation.png
outputs/phase2/figures/service_graph_example.png
```

Current status:

```text
[x] Claim-safe generator implemented at scripts/phase2/generate_paper_outputs.py
[x] All four paper tables generated
[x] All five required figures generated
[x] Step 7 full-budget and budget-120 regimes kept separate
[x] View A and View B architecture-level rows explicitly separated
```

### Minimum paper tables

#### Main result table

```text
Method | Precision | Recall | F1 | FPR | Context Coverage | Retrieval Latency | LLM Calls
```

#### Fault type breakdown

```text
Method | Fault Type | Precision | Recall | F1 | FP | FN | Context Coverage
```

#### Ablation table

```text
α | β | γ | Precision | Recall | F1 | FPR | Coverage | Latency | Network-delay Recall
```

#### Cost/latency table

```text
Method | LLM Calls | Actual API Calls | Cache Hits | JSON Valid | Avg LLM Latency | Estimated Cost
```

### Quality checks

```text
[x] Figure labels match paper terminology
[x] Tables separate retrieval-only from LLM decision results
[x] Context Rescue is marked as architecture-enhanced
[x] network_delay analysis is included
[x] Cost/API/cache fields are not conflated
```

---

## 11. Step 9 — Quality Gate Before Finalizing Results

### Purpose

Ensure every result is traceable, reproducible, and defensible.

### Checklist

```text
[x] All paper outputs are under outputs/phase2/
[x] Every result traces to config → command → audit → summary
[x] Baseline numbers match baseline_reference.csv
[x] Proposed method uses the same split as BM25 baseline
[x] Debug/smoke outputs are excluded from paper tables
[x] Context Rescue is labeled as architecture-enhanced baseline
[x] Score_final is always in [0,1]
[x] GraphSim handles dG = ∞ correctly
[x] Cache hits and actual API calls are reported separately
[x] Manual review is not treated as route_alert
[x] No RCA claim is made unless root-cause service labels are explicitly available
[x] All tables specify the window set used: 300w or 500w
[x] All key configs are stored with results
```

Quality gate status:

```text
[x] Runner implemented at scripts/phase2/run_step9_quality_gate.py
[x] All 14 checks passed
[x] All 5 hard-stop conditions passed
[x] Paper result table is finalizable
[x] Report generated at outputs/phase2/quality_gate/step9_quality_gate_report.md
```

### Stop condition

If any of the following fail, do not finalize the paper result table:

```text
baseline reproducibility check
window split consistency
schema validation
Score_final bound check
cache/API separation
```

---

## 12. Step 10 — Package Submission and Thesis Insert

### Purpose

Convert experiment outputs into paper-ready and thesis-ready text sections.

### Paper sections to draft

```text
[x] Introduction
[ ] Related Work
[x] Problem Formulation
[x] Methodology
    [x] Service Dependency Graph Construction
    [x] Topology-aware Candidate Expansion
    [x] Weighted Context Fusion
[x] Experimental Setup
    [x] Dataset
    [x] Baselines
    [x] Metrics
    [x] Implementation Details
[x] Results
    [x] Main comparison
    [x] Fault-type breakdown
    [x] Ablation
    [x] Cost/latency
[x] Discussion
[x] Threats to Validity
[x] Conclusion
```

`Related Work` remains open until citation-backed literature review is completed.

### Thesis sections to update

```text
[x] Phase 2 methodology chapter
[x] Experiment design chapter
[x] Result analysis chapter
[x] System integration chapter
[x] Limitation and future work
```

### Claim boundary

Allowed current claim:

```text
Topology-aware retrieval improves evidence availability and difficult-fault recall, especially for network_delay,
but the current decision policy increases false positives, cost, and aggregate error.
```

Preferred framing:

```text
In microservice monitoring, useful evidence is not only temporally close to an alert, but also topologically close on the service dependency graph.
```

Claims to avoid unless directly measured:

```text
Full root cause analysis
Production real-time readiness
Autonomous remediation
Superiority over all RAG variants
Generalization beyond Nezha without another dataset
```

### Deliverables

```text
[x] EXPERIMENT_REPORT_FOR_SUBMISSION_PHASE2.md
[x] paper/draft.md
[x] reports/phase2_thesis_insert_sections.md
[x] FULL_PAPER_IMPROVEMENT_PLAN.md
```

Step 10 remains open only for citation-backed Related Work and final formatting in the target thesis/paper template.

---

## 13. Final Execution Checklist

```text
[x] Step 1 completed: baseline and input split frozen
[x] Step 2 completed: service graph built and validated
[x] Step 3 completed: topology-aware retrieval implemented
[x] Step 4 completed: retrieval-only evaluation generated
[x] Step 5 completed: α/β/γ ablation generated
[x] Step 6 completed: hybrid pipeline integration and audit schema updated
[x] Step 7 completed: View A and View B LLM decision evaluation generated
[x] Step 8 completed: paper tables and figures generated
[x] Step 9 completed: quality gate passed
[ ] Step 10 completed: submission/thesis package drafted
```

---

## 14. Summary

### Current progress

```text
Execution-plan completion: 9/10 steps (90%)
Experimental pipeline and evidence package: complete
Paper tables, figures, provenance, and quality gate: complete
Submission/thesis packaging: partially available but not consolidated as Step 10
```

The current evidence supports a fault-specific and operating-point trade-off result:

```text
Topology-aware retrieval increases evidence availability and recall, especially for network_delay,
but the current fusion/decision policy increases false positives, cost, and aggregate error.
```

### Next mandatory priority

```text
Step 10: consolidate the submission and thesis package.
```

Required order:

```text
1. Freeze the final View A/View B tables and claim wording.
2. Draft methodology, experimental setup, results, discussion, and threats to validity.
3. Insert the four paper tables and five figures with artifact citations.
4. Produce one final submission report and one thesis-ready result chapter.
5. Run a final document-level consistency pass against the Step 9 report.
```

### Optional research-strengthening track

These items are not required to close the current execution plan, but are the highest-value work for a stronger full paper:

```text
1. Calibrate topology evidence/routing to reduce normal-window false positives.
2. Run at least three independent fresh-cache LLM repetitions.
3. Validate the method on a second dataset or microservice workload.
```

The most important paper priority is now:

```text
Report the measured recall/context benefit together with the FPR/F1/cost degradation;
do not frame topology-aware fusion as the aggregate winner.
```

The most important quality priority is now:

```text
Keep the final manuscript consistent with the passed Step 9 artifact and Nezha-only claim boundary.
```
