# Topology-Aware Evidence Retrieval for Cost-Aware LLM Alert Validation in Microservices

## Abstract

Metric detectors in microservice systems can produce large alert volumes without sufficient operational evidence. This study evaluates a hybrid pipeline that combines metric anomaly detection, retrieval over logs and traces, and an LLM judge. We introduce topology-aware retrieval that combines lexical relevance, temporal proximity, and service-graph distance. On a frozen 500-window Nezha split, topology-aware retrieval increases full-budget recall from `0.5800` to `0.7400` and improves `network_delay` recall from `0.3750` to `0.7000`. However, aggregate F1 decreases from `0.7030` to `0.4759`, FPR increases from `0.0175` to `0.3425`, and estimated LLM cost increases. An architecture-level comparison also shows that LLM without RAG has the highest F1 under a 120-call budget. These results show that topology improves evidence availability and difficult-fault recall, but evidence and routing calibration are required before claiming aggregate diagnostic improvement.

## 1. Introduction

Microservice monitoring combines high-dimensional metrics, distributed traces, and heterogeneous logs. Metric-only anomaly detectors are fast, but their candidate alerts often lack the evidence required to distinguish true incidents from benign operational variation. LLM-based validation can interpret richer signals, but indiscriminate LLM use creates cost, latency, quota, and reliability risks.

This work studies a cost-aware hybrid design:

1. a metric detector generates candidate alerts;
2. a retrieval layer selects related log and trace evidence;
3. an LLM judge validates or abstains on the candidate;
4. cache, budget, scheduler, and manual-review controls limit operational risk.

The main research question is whether evidence should be selected only by lexical and temporal relevance, or whether service-topology proximity provides useful additional context.

The contributions are:

- a topology-aware retrieval pipeline combining BM25, time similarity, and graph similarity;
- a frozen-window evaluation contract with audit-level provenance;
- retrieval-fair and architecture-level LLM comparisons;
- explicit accounting for manual review, logical calls, API calls, cache hits, latency, and cost;
- a fault-specific analysis showing recall benefit and aggregate false-positive trade-offs.

## 2. Related Work

This section requires a citation-backed revision before submission.

The final review must position the work against:

- graph-aware retrieval and GraphRAG;
- microservice anomaly detection and root-cause localization;
- LLM-based observability and alert triage;
- selective prediction, abstention, and human review;
- cost-aware LLM routing and caching.

The novelty claim must focus on operational evaluation and calibrated evidence use rather than graph retrieval alone.

## 3. Problem Formulation

Let an alert candidate be associated with service \(s_0\), time \(t_0\), metric features, and anomaly score. The retrieval layer selects contexts \(c_i\) from logs and traces.

For each context, the fusion score is:

\[
Score(c_i) = \alpha BM25_{norm}(c_i) + \beta TimeSim(c_i,t_0) + \gamma GraphSim(s_i,s_0)
\]

where:

\[
TimeSim = \exp(-|t_i-t_0|/\tau)
\]

and:

\[
GraphSim =
\begin{cases}
1/(1+d_G(s_i,s_0)), & d_G < \infty \\
0, & d_G = \infty
\end{cases}
\]

The downstream objective is not retrieval score alone. It is to improve alert precision, recall, and F1 while controlling FPR, manual review, latency, tokens, and API cost.

## 4. Methodology

### 4.1 Service dependency graph

The graph is constructed from distributed traces. Directed service-call edges are aggregated with trace count, span count, operation samples, duration statistics, and observation timestamps. The final Phase 2 graph contains 56 services and 68 edges.

### 4.2 Topology-aware candidate expansion

BM25 provides the lexical candidate pool. The topology expander adds contexts from services within a configured graph distance and removes duplicates deterministically.

### 4.3 Weighted fusion

The final ranking combines normalized BM25 relevance, exponential time similarity, and graph similarity. All final scores are clamped to `[0,1]`. The ablation evaluates lexical-only, lexical-time, lexical-graph, balanced, and topology-heavy settings.

### 4.4 LLM validation and abstention

The LLM returns a schema-constrained decision with label, confidence, evidence identifiers, reason, and action. Evidence-free true-alert decisions can be sent to manual review. Budget exhaustion also produces manual review instead of a confirmed routed alert.

### 4.5 Operational controls

The system records logical LLM calls, actual API calls, cache hits, retry/backoff, token usage, retrieval latency, LLM latency, and cost. These fields are never conflated.

## 5. Experimental Setup

### 5.1 Dataset and frozen windows

Nezha metrics, logs, and traces are used for the main hybrid evaluation. The primary split is `paper_500`, containing 100 true-alert and 400 normal windows across 56 services. The frozen window hash is:

```text
1745d09ec60c98b8520a6e38ed614f20e39009c3ac7173468f18658066a7cd9e
```

### 5.2 Baselines

- Detector-only
- LLM without RAG
- BM25 RAG top-6
- BM25 RAG top-10
- Topology-Aware Fusion top-6
- Context Rescue, labeled architecture-enhanced

### 5.3 Evaluation views

View A compares BM25 top-6 and topology top-6 with the same windows, top-k, model, budget, and policy.

View B compares complete architectures on the same frozen windows under an operational 120-call budget. Context Rescue remains explicitly architecture-enhanced.

### 5.4 Metrics

The evaluation reports precision, recall, F1, FPR, TP, FP, FN, manual-review rate, automation coverage, context coverage, retrieval latency, LLM latency, logical calls, API calls, cache hits, token usage, JSON validity, and estimated cost.

## 6. Results

### 6.1 Retrieval-fair View A

| Regime | Method | Precision | Recall | F1 | FPR | Context coverage | Cost USD |
|---|---|---:|---:|---:|---:|---:|---:|
| Budget 120 | BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 | 0.1125 | 0.0214684 |
| Budget 120 | Topology top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 | 0.2454 | 0.0401765 |
| Full budget | BM25 top-6 | 0.8923 | 0.5800 | 0.7030 | 0.0175 | 0.2249 | 0.0627953 |
| Full budget | Topology top-6 | 0.3507 | 0.7400 | 0.4759 | 0.3425 | 1.0000 | 0.1669426 |

At budget 120, topology recall improves by `+0.1200`, but the F1 confidence interval includes zero. At full budget, topology recall improves by `+0.1600`, while F1 decreases by `-0.2271` and exact McNemar testing favors BM25 overall.

### 6.2 Fault-specific result

The strongest positive result is `network_delay`: full-budget recall increases from `0.3750` to `0.7000`. The same topology configuration also routes 137 false alerts on normal windows, compared with seven for BM25.

### 6.3 Architecture-level View B

| Method | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| Detector-only | 0.2004 | 0.9800 | 0.3328 | 0.9775 |
| LLM without RAG | 0.5210 | 0.6200 | 0.5662 | 0.1425 |
| BM25 top-6 | 1.0000 | 0.3400 | 0.5075 | 0.0000 |
| Topology top-6 | 0.5823 | 0.4600 | 0.5140 | 0.0825 |
| Context Rescue | 1.0000 | 0.3400 | 0.5075 | 0.0000 |

LLM without RAG has the highest F1 in View B. Context Rescue checks 11 detector-negative windows but promotes none, so its decisions match BM25 on this split.

### 6.4 Retrieval-only ablation

The weight ablation is retrieval-only. It must not be used as an LLM decision ablation. Graph-enabled settings increase topology-expanded context, while service-context coverage and latency expose the retrieval trade-off.

### 6.5 Cost and latency

Topology increases retrieved evidence and recall but also increases prompt content, model cost, and false-positive review burden. Context Rescue uses BM25 cache replay in View B; its zero API calls are replay-state behavior, not zero first-pass inference cost.

## 7. Discussion

Topology-aware retrieval solves an evidence-availability problem but exposes a decision-calibration problem. The topology method returns context more consistently, reducing evidence-related abstention. However, graph proximity alone does not imply incident relevance. Normal-window contexts can be topologically close and still be unsuitable positive evidence.

The result suggests that retrieval and routing should not be optimized independently. A stronger method should require service consistency, negative-evidence handling, or calibrated confidence before routing.

## 8. Threats to Validity

- The main result uses one Nezha-based workload package.
- Independent repeated LLM runs are not yet available.
- `paper_300` contains one service and is unsuitable as the main topology validation split.
- Context Rescue is architecture-enhanced and not retrieval-fair.
- Cache replay preserves decisions but does not measure first-pass latency or API pressure.
- Root-cause service labels are unavailable, so the study does not claim full RCA.
- The current topology policy was not calibrated on a separate multi-service split.

## 9. Conclusion

Topology-aware retrieval increases evidence availability and difficult-fault recall, particularly for network delay. Under the current decision policy, this benefit is offset by higher false positives, cost, and aggregate error. The study therefore supports a calibrated, fault-specific contribution rather than a claim of universal superiority. Future work should calibrate evidence routing, repeat fresh-cache LLM runs, and validate on another microservice workload.

## Artifact Index

```text
outputs/phase2/step7_rerun/
outputs/phase2/step7_view_b/
outputs/phase2/paper_tables/
outputs/phase2/figures/
outputs/phase2/quality_gate/
FULL_PAPER_IMPROVEMENT_PLAN.md
```
