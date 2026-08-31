# packages/llm

Not yet implemented (Phase 2, Week 3 — port from `legacy/src/llm/` unchanged).

- `router.py` — local-first routing (Ollama llama3.2:3b first, Gemini Flash Lite fallback)
- `cache.py` — response cache, key = `sha256(prompt + model + temperature + max_tokens)` (R-A5)
