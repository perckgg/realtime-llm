# Nezha Hybrid Monitoring Setup

This folder adapts `data/Nezha` to the hybrid monitoring experiment.

Nezha contains multimodal observability data:

- pod/service metrics under `rca_data/<date>/metric`
- application logs under `rca_data/<date>/log`
- trace spans under `rca_data/<date>/trace`
- injected fault labels under `rca_data/<date>/<date>-fault_list.json`

## Prepare Data

```powershell
py nezha_setup/prepare_nezha_data.py
```

The script writes:

- `nezha_setup/processed/metrics.csv`
- `nezha_setup/processed/logs.jsonl`
- `nezha_setup/processed/summary.json`

Labels are assigned at metric-row level when the row belongs to the injected pod and falls inside the configured fault window.

## Run

```powershell
py experiments/run_baseline.py --config nezha_setup/config/experiment_nezha_smoke.yaml --mode detector_only
py experiments/run_hybrid.py --config nezha_setup/config/experiment_nezha_smoke.yaml
py experiments/compare_results.py --input nezha_setup/outputs/smoke/results
```

The default LLM provider remains `mock` so this setup runs offline. Use a real API only after the data path and evaluation are stable.

Use the configs by scale:

- `experiment_nezha_smoke.yaml`: 50 windows, up to 10 mock LLM calls.
- `experiment_nezha_medium.yaml`: 5,000 windows, up to 200 mock LLM calls.
- `experiment_nezha_full.yaml`: full dataset, up to 1,000 mock LLM calls.
- `experiment_gemini_smoke.yaml`: 50 windows, up to 5 real Gemini calls.

Vector backend note:

- `retrieval.vector_db: local` is the default and uses in-memory hashing.
- `retrieval.vector_db: faiss` or `chroma` is accepted, but currently falls back to local hashing unless the optional dependency and concrete backend integration are enabled.
- For this project, FAISS is the better next backend for fast local experiments; Chroma is more convenient once persistence and collection management matter.

## LLM API Choice

For a low-cost experiment, keep `mock` while tuning detector/RAG thresholds. When switching to a real judge API, prefer:

- Google AI Studio Gemini free tier for the first real API trial.
- Groq free plan for fast OpenAI-compatible chat completion experiments with strict rate limiting.
- OpenRouter free models when you want one OpenAI-like endpoint that can route across multiple free/community models.

Use a small candidate sample first. The current Nezha run can produce tens of thousands of LLM calls if the gate is loose.

Smoke test with Gemini:

```powershell
$env:GEMINI_API_KEY = "<your key>"
py experiments/run_hybrid.py --config nezha_setup/config/experiment_gemini_smoke.yaml
```

The smoke config limits evaluation to 50 metric windows. Increase `evaluation.max_windows` only after checking cost and rate limits.
If Gemini returns `429 Too Many Requests`, lower `llm_gate.max_llm_calls_per_minute`, lower `evaluation.max_llm_calls`, or wait for quota reset before retrying.
