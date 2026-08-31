# Hybrid Monitoring Experiment

This repository implements a feasibility experiment for a hybrid monitoring pipeline:

1. Fast metric anomaly detection.
2. Local RAG over logs/events.
3. LLM-as-a-Judge validation with a mock provider by default.
4. Evaluation of alerts, latency, LLM calls, token usage, and fallback behavior.

## Quick Start

```bash
python experiments/run_baseline.py --config config/experiment.yaml --mode detector_only
python experiments/run_baseline.py --config config/experiment.yaml --mode llm_without_rag
python experiments/run_hybrid.py --config config/experiment.yaml
python experiments/compare_results.py --input outputs/results
```

Run tests:

```bash
py -m unittest discover -s tests
```

Generate thesis-ready evaluation reports from existing outputs only:

```powershell
py -B scripts/generate_evaluation_reports.py
```

Initialize Phase 2 foundation artifacts (manifest + fixed window index + baseline reference):

```powershell
py scripts\phase2\build_phase2_manifest.py
py scripts\phase2\freeze_phase2_inputs.py
py scripts\phase2\build_service_graph.py
py scripts\phase2\run_topology_retrieval_debug.py
py scripts\phase2\run_retrieval_only_eval.py --splits debug_50 paper_300 paper_500
py scripts\phase2\run_alpha_beta_gamma_ablation.py
py experiments\run_phase2_topology_fusion.py --config nezha_setup\config\experiment_phase2_topology_fusion_300w.yaml --output-mode topology_fusion_300w
py experiments\run_phase2_topology_fusion.py --config nezha_setup\config\experiment_phase2_topology_fusion_500w.yaml --output-mode topology_fusion_500w
py scripts\phase2\run_step7_view_b.py
py scripts\phase2\generate_paper_outputs.py
py scripts\phase2\run_step9_quality_gate.py
```

Phase 2 submission and full-paper planning artifacts:

```text
EXPERIMENT_REPORT_FOR_SUBMISSION_PHASE2.md
paper/draft.md
reports/phase2_thesis_insert_sections.md
FULL_PAPER_IMPROVEMENT_PLAN.md
```

Run the Microsoft cloud-monitoring metric-only experiment. This dataset is used for detector-only evaluation; do not use it for RAG or external LLM/API experiments.

```powershell
py cloud_monitor_setup/prepare_cloud_monitor_data.py
py experiments/run_baseline.py --config cloud_monitor_setup/config/experiment_current.yaml --mode detector_only
py -B scripts/summarize_cloud_monitoring_experiment.py
```

Run the Phase 4 benchmark on Nezha:

```bash
py experiments/run_phase4_benchmark.py --config nezha_setup/config/experiment_phase4_benchmark.yaml
```

Run Phase 5 context rescue with the mock judge:

```bash
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase5_context_rescue.yaml
```

Run the Phase 3 Gemini smoke test, assuming `.env` contains `GEMINI_API_KEY`:

```powershell
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase3_gemini_smoke.yaml
```

Run the Phase 5 Gemini smoke test:

```powershell
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_phase5_gemini_smoke.yaml
```

Run local-first Ollama with Gemini fallback:

```powershell
ollama pull qwen2.5:1.5b
$env:GEMINI_API_KEY = ((Get-Content -LiteralPath .env | Where-Object { $_ -match '^GEMINI_API_KEY=' } | Select-Object -First 1) -replace '^GEMINI_API_KEY=', '').Trim()
py experiments/run_hybrid.py --config nezha_setup/config/experiment_local_first_ollama_smoke.yaml
```

Run a stratified real-LLM slice with cache enabled. The runner loads `.env` from this repo. Extra env files such as `C:\Working\IELTSApp\.env` are loaded only when passed explicitly with `--env-file`.

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_groq_stratified.yaml --cache-path nezha_setup/outputs/llm_response_cache.jsonl --output-mode groq_stratified
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_openrouter_stratified.yaml --cache-path nezha_setup/outputs/llm_response_cache.jsonl --output-mode openrouter_stratified
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_cohere_stratified.yaml --cache-path nezha_setup/outputs/llm_response_cache.jsonl --output-mode cohere_stratified
```

Run one-window Gemini smoke tests when checking whether the Gemini quota has recovered:

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_gemini25_flash_one_window.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode gemini25_flash_one_window --cache-path nezha_setup/outputs/llm_response_cache_gemini25_flash_one_window.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_gemini20_flash_one_window.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode gemini20_flash_one_window --cache-path nezha_setup/outputs/llm_response_cache_gemini20_flash_one_window.jsonl
```

Run a minimal Gemini connection test before a larger Step 7 slice. The script auto-loads `.env` from the repo root and uses `GEMINI_API_KEY`:

```powershell
py scripts\test_gemini_connection.py --model gemini-2.5-flash
```

Run priority-aware local-first scheduling with OpenRouter fallback:

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_first_scheduler_openrouter_smoke.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode local_first_scheduler_openrouter_one_window --cache-path nezha_setup/outputs/llm_response_cache_openrouter_stable.jsonl
```

Compare local Ollama models without external API fallback:

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_only_qwen25_3b_one_window.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode local_only_qwen25_3b_one_window
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_only_llama32_3b_one_window.yaml --max-positives 1 --max-negatives 0 --seed 5 --output-mode local_only_llama32_3b_one_window
```

Run the local model cascade strategy. This uses `llama3.2:3b` first and falls back to `qwen2.5:3b` only for invalid JSON, uncertain label, or low confidence.

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_model_cascade_llama_qwen.yaml --max-positives 1 --max-negatives 1 --seed 11 --output-mode local_model_cascade_1p1n
```

Run the lighter single-local strategy with Gemini Flash Lite fallback. This does not run two local models.

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_local_llama_gemini_lite_scheduler.yaml --max-positives 1 --max-negatives 1 --seed 11 --output-mode local_llama_gemini_lite_1p1n --cache-path nezha_setup/outputs/llm_response_cache_gemini_lite_scheduler.jsonl
```

Run the larger Gemini Flash Lite feasibility slice. The default policy sends candidates to manual review after the LLM budget is exhausted instead of routing them as confirmed alerts.

```powershell
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_stratified.yaml --max-positives 100 --max-negatives 400 --seed 21 --output-mode gemini25_flash_lite_500w_paid_key --cache-path nezha_setup/outputs/llm_response_cache_gemini25_flash_lite_500w_paid_key.jsonl
py experiments/run_stratified_real_llm.py --config nezha_setup/config/experiment_real_llm_stratified_cache_replay.yaml --max-positives 100 --max-negatives 400 --seed 21 --output-mode gemini25_flash_lite_500w_budget_manual_review_cache_replay --cache-path nezha_setup/outputs/llm_response_cache_gemini25_flash_lite_500w_paid_key.jsonl
```

## Notes

- The default LLM provider is `mock`, so no external API is called.
- Legacy Phase 1 outputs remain under existing folders (`nezha_setup/outputs/`, `outputs/audit/`, `outputs/results/`).
- Phase 2 writes to the dedicated namespace `outputs/phase2/` to avoid mixing results across phases.
- Phase 3+ configs use a real sklearn `IsolationForestDetector`.
- FAISS is optional; `hybrid_bm25` is the local RAG backend used when native vector dependencies are inconvenient.
- Phase 5 adds context rescue to promote metric-missed candidates when nearby trace/log signals are strong.
- Local-first configs use Ollama `qwen2.5:1.5b` first and fall back to Gemini for low-confidence, uncertain, invalid, or high-severity cases.
- Real-LLM stratified runs can use Groq, OpenRouter, or Cohere. OpenRouter and Cohere were smoke-tested successfully on 2026-06-01; Groq reached the API but returned `403 Forbidden` with the available key/model.
- Gemini `gemini-2.5-flash` and `gemini-2.0-flash` were both smoke-tested with one window on 2026-06-01 and still returned `429 Too Many Requests`.
- Enable `LLM_RESPONSE_CACHE` or pass `--cache-path` to separate first-run API calls from cached reruns and reduce `429`/quota pressure. Cache metrics are reported as `llm_cache_hits`, `actual_api_calls`, and `cache_hit_rate`.
- The optional `llm_scheduler` layer routes high-priority alerts to API fallback, lets local-first handle lower-priority alerts, and defers API work during cooldown or budget exhaustion. Scheduler metrics are reported as `scheduler_deferred`, `scheduler_local_only`, `scheduler_api_allowed`, `api_deferred`, and `avg_priority_score`.
- Local Ollama comparison on 2026-06-01 showed both `qwen2.5:3b` and `llama3.2:3b` produced valid JSON on the same one-window smoke; `llama3.2:3b` was faster in that run.
- Local cascade on 2026-06-01 uses `llama3.2:3b` as primary and `qwen2.5:3b` as conditional fallback. `require_evidence_for_true_alert` prevents evidence-free local true-alert outputs from routing directly.
- Single-local Gemini Lite fallback on 2026-06-01 still received `429` from `gemini-2.5-flash-lite` with the workspace `.env` key. The Gemini error body reported depleted prepayment credits (`RESOURCE_EXHAUSTED`), so this is a project/billing-credit issue rather than a pipeline burst issue.
- After credit was added and the workspace `.env` key was updated, `gemini-2.5-flash-lite` ran successfully. The 3p3n paid-key run is `gemini25_flash_lite_paid_3p3n` under `nezha_setup/outputs/real_llm_stratified/results/`.
- `decision.llm_budget_exhausted_action` defaults to `manual_review`, matching the experiment guide's uncertain/manual-review branch. Set it to `route_alert` only when deliberately measuring the old detector-fallback behavior.

## Phase boundary layout

```text
src/
  phase1/                      # logical boundary for Phase 1 inheritance
  phase2/                      # logical boundary for new Phase 2 modules
  retrieval/                   # existing retrieval baseline implementation

outputs/
  phase1/                      # index for historical Phase 1 artifacts
  phase2/                      # Stage-2 dedicated outputs (new runs only)
```
