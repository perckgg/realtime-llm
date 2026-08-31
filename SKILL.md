---
name: hybrid-monitoring-experiment
description: Build and evaluate a hybrid real-time monitoring experiment that combines a fast anomaly detector, RAG over logs/events, and LLM-as-a-Judge for alert validation in server/cloud environments.
---

# Hybrid Monitoring Experiment Skill

## Purpose

Use this skill when implementing or modifying the experiment for a hybrid monitoring architecture:

- Fast anomaly detection on metric streams.
- Context retrieval over logs/events.
- LLM-as-a-Judge for semantic alert validation.
- Evaluation of false positive reduction, latency, LLM calls, and token/cost.

The goal is to test feasibility, not to build a production-grade monitoring platform.

---

## Core Architecture

Implement the system as two connected pipelines.

### Metric Pipeline

```text
Metric Stream
    -> Metric Preprocessing
    -> Base Anomaly Detector
    -> Alert Candidate Builder
    -> LLM Gate / Call Policy
    -> Context Retrieval / RAG
    -> Prompt Composer
    -> LLM-as-a-Judge
    -> Decision & Audit
```

### Log/Event Pipeline

```text
Log/Event Stream
    -> Log/Event Preprocessing
    -> Chunking
    -> Embedding
    -> Context Store / Vector Database
```

---

## Required Modules

Create or maintain these modules:

```text
src/
├── ingestion/
├── preprocessing/
├── detectors/
├── retrieval/
├── llm/
├── decision/
└── evaluation/
```

Each module must have clear input/output objects and should not depend on global state.

---

## Implementation Rules

### 1. Configuration-first

Do not hard-code experiment parameters. Read them from:

```text
config/experiment.yaml
```

Expected config sections:

- `data`
- `preprocessing`
- `detector`
- `retrieval`
- `llm_gate`
- `llm`
- `decision`
- `evaluation`

### 2. Metric preprocessing

Implement:

- Timestamp normalization.
- Sliding window.
- Dynamic Z-score or Min-Max normalization.
- Metric window creation.

Expected metric window object:

```python
{
    "window_id": "...",
    "start_time": "...",
    "end_time": "...",
    "node_id": "...",
    "service_id": "...",
    "features": [[...]],
    "feature_names": [...]
}
```

### 3. Base detector

Start with a lightweight detector:

- Isolation Forest, or
- Robust Random Cut Forest if dependency support is available.

Optional later:

- MTAD-GAT
- Graph Deviation Network

Detector output:

```python
{
    "window_id": "...",
    "is_candidate": true,
    "anomaly_score": 0.91,
    "detector_label": "anomaly",
    "top_features": [...]
}
```

### 4. Alert candidate builder

Build a structured alert candidate from detector output.

Required fields:

- `alert_id`
- `time_window`
- `node_id`
- `service_id`
- `anomaly_score`
- `metric_snapshot`

### 5. LLM Gate / Call Policy

Never call the LLM for every metric window.

Use policy:

```text
score < low_threshold:
    ignore or log only

low_threshold <= score < high_threshold:
    call LLM-as-a-Judge

score >= high_threshold:
    alert directly or call LLM depending on config
```

Track how many LLM calls were avoided.

### 6. Log/Event preprocessing

Implement:

- Timestamp normalization.
- Deduplication.
- Regex filtering.
- Metadata extraction.

Required metadata:

- `timestamp`
- `node_id`
- `service_id`
- `pod_id` if available
- `severity`
- `event_type`

### 7. Retrieval

Use hybrid retrieval:

1. Metadata filtering:
   - `time_window`
   - `node_id`
   - `service_id`
   - `severity`
   - `event_type`
2. Vector similarity search.
3. Return top-k logs/events.

Do not rely only on cosine similarity.

### 8. Prompt composer

Prompt must include:

- LLM role.
- Alert candidate.
- Metric snapshot.
- Anomaly score.
- Top-k logs/events.
- Strict JSON output instruction.

Keep prompts short enough to control token usage.

### 9. LLM output schema

The LLM must return only JSON matching:

```json
{
  "label": "true_alert | false_positive | uncertain",
  "severity": "P1 | P2 | P3 | none",
  "confidence": 0.0,
  "evidence": ["log_id_or_event_id"],
  "reason": "short explanation",
  "recommended_action": "short action"
}
```

Use Pydantic or equivalent validation.

If validation fails, route to fallback.

### 10. Decision layer

Decision rules:

```text
JSON/API error:
    fallback to detector alert

label = false_positive:
    suppress alert

label = true_alert:
    route alert

label = uncertain or confidence < threshold:
    mark for manual review
```

### 11. Audit logging

Always write audit records.

Required fields:

- `alert_id`
- `window_id`
- `anomaly_score`
- `retrieved_context_ids`
- `prompt_token_count`
- `completion_token_count`
- `detector_latency_ms`
- `retrieval_latency_ms`
- `llm_latency_ms`
- `final_decision`
- `fallback_status`

---

## Required Experiment Modes

Implement three modes:

### detector_only

```text
Metric -> Detector -> Decision
```

### llm_without_rag

```text
Metric -> Detector -> LLM -> Decision
```

### hybrid

```text
Metric -> Detector -> RAG -> LLM -> Decision
```

---

## Evaluation Metrics

Compute and save:

### Classification

- Precision
- Recall
- F1-score
- False Positive Rate
- False Positive Reduction

### Runtime

- Detector latency
- Retrieval latency
- LLM latency
- End-to-end latency
- Throughput

### LLM cost

- Number of LLM calls
- Calls avoided by gate
- Input tokens
- Output tokens
- Estimated cost
- JSON valid rate
- Fallback rate

### Retrieval

- Top-k context count
- Retrieval latency
- Context token count

---

## Testing Requirements

Add tests for:

- Sliding window creation.
- Normalization.
- Detector interface.
- Metadata filtering.
- Retriever top-k behavior.
- Prompt schema.
- LLM JSON validation.
- Fallback behavior.

Do not call real LLM APIs in tests. Use mocks.

---

## Coding Style

- Prefer readable Python.
- Use type hints.
- Use dataclasses or Pydantic models for structured payloads.
- Keep functions small and testable.
- Store outputs under `outputs/`.
- Do not silently swallow exceptions; log them and route to fallback if needed.
- Update README when changing commands or project structure.

---

## Deliverables

When completing a task, ensure the repository contains:

- Runnable pipeline.
- Config file.
- Sample data loader.
- At least one detector implementation.
- Local vector store implementation.
- Prompt composer.
- LLM judge wrapper with mock support.
- Decision/fallback layer.
- Evaluation report script.
- Tests for core modules.
