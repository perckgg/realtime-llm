# Evaluation Criteria Mapping

This document maps existing experiment outputs to thesis evaluation criteria. It is derived from existing files and does not rerun the full LLM pipeline.

## 1. Alert Quality

Alert quality measures whether the pipeline identifies true alerts while reducing false alarms. The main metrics are precision, recall, F1-score, false positive rate, TP, FP, and FN. These metrics are used in Phase 3, Phase 4, Phase 5, local-first smoke tests, and streaming replay.

## 2. Contextual Effectiveness

Contextual effectiveness evaluates whether retrieved log/trace context improves LLM decisions. The main metrics are context coverage, average retrieved context count, context token count, retrieval latency, and evidence hit@k when explicit evidence matching is available. In the current outputs, context coverage and average context are the strongest available proxies.

## 3. Operational Cost

Operational cost captures the extra runtime and monetary cost introduced by retrieval and LLM judging. The main metrics are LLM calls, actual API calls, cache hits, input/output tokens, retrieval latency, average LLM latency, and estimated cost. These metrics connect model quality improvements to practical deployment constraints.

## 4. Operational Risk and Reliability

Operational risk covers failure modes such as invalid JSON, API fallback, timeout, rate limit, exhausted LLM budget, hallucination risk, and unsupported decisions. In this repository, the most important reported metrics are JSON valid rate, fallback rate, API fallback calls, cache hit rate, retry/backoff metrics, and manual-review behavior when LLM budget is exhausted.

## 5. Real-time / Streaming Feasibility

Real-time feasibility asks whether the pipeline can process telemetry sequentially without future context leakage. Streaming replay, watermark behavior, end-to-end latency, and throughput-related latency metrics are used for this criterion. The current streaming result is a feasibility smoke test, not a direct quality benchmark against Phase 4/5.

## 6. Mapping from Experiments to Criteria

| Criterion Group | Research Question | Metrics | Used In |
|---|---|---|---|
| Alert Quality | Does the system correctly identify true alerts and reduce false alarms? | Precision, Recall, F1, FPR, TP, FP, FN | Phase 3, Phase 4, Phase 5 |
| Contextual Effectiveness | Does RAG/log/trace context improve decision quality? | Context coverage, avg context, retrieval latency, evidence hit@k if available | Phase 3, Phase 4, Phase 5 |
| Operational Cost | How expensive is the improvement? | LLM calls, API calls, token usage, retrieval latency, average LLM latency | Phase 4, Phase 5, Local-first |
| Operational Risk | What can fail during deployment? | fallback rate, JSON valid rate, timeout, 429/rate-limit, hallucination/unsupported decision risk | Local-first, scheduler/cache, real LLM tests |
| Real-time Feasibility | Can the system process data sequentially without future leakage? | streaming replay, watermark, E2E latency | Streaming replay |

## 7. Interpretation Guidelines for Thesis Writing

- Treat cost and risk as evaluation criteria, not only implementation notes.
- When a method improves F1 or recall, also report the additional LLM calls, retrieval latency, token usage, and fallback/manual-review behavior.
- Do not compare streaming replay directly against Phase 4/5 quality numbers because the window count and backend settings differ.
- Present Context Rescue as an architectural improvement, not as a single-variable ablation, because it changes candidate generation and increases LLM calls.
- Avoid claiming production readiness. The current evidence supports feasibility and trade-off analysis.
