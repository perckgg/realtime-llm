"""Builds the Judge from a run config's `judge:` block (eval/configs/*.yaml).

    judge:
      backend: api | mock      # QD-013: one fixed API model; mock only for G-port
      model: gemini-2.5-flash  # QD-021; gemini-2.5-flash-lite only for G-paper
      max_output_tokens: 1024
      require_evidence: true
      confidence_threshold: 0.80
      repeat: 0
      max_calls_per_minute: 200   # shared by all workers (QD-019)
      workers: 8                  # parallel judge threads in the harness (QD-019)
      cache_path: data/llm_cache/gemini.jsonl
      cache_read_paths: []     # extra read-only caches, e.g. GD1's (G-paper)
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from services.judge.backends import JUDGE_MODEL, GeminiBackend, JudgeBackend, MockBackend
from services.judge.cache import ResponseCache
from services.judge.llm_judge import LLMJudge

DEFAULT_CACHE = Path("data/llm_cache/gemini.jsonl")


def build_judge(config: Mapping[str, Any]) -> LLMJudge:
    backend_name = str(config.get("backend", "api"))
    backend: JudgeBackend
    if backend_name == "mock":
        backend = MockBackend()
    elif backend_name == "api":
        model = str(config.get("model", JUDGE_MODEL))
        if not model.startswith("gemini"):
            raise ValueError(f"only Gemini models are supported (QD-013), got {model!r}")
        if float(config.get("temperature", 0)) != 0:
            raise ValueError("temperature must be 0 (QD-013); it is part of the cache key")
        cache = ResponseCache(
            Path(config.get("cache_path") or DEFAULT_CACHE),
            [Path(p) for p in config.get("cache_read_paths") or []],
        )
        backend = GeminiBackend(
            cache,
            model=model,
            max_output_tokens=int(config.get("max_output_tokens", 1024)),
            max_retries=int(config.get("max_retries", 5)),
            max_calls_per_minute=int(config.get("max_calls_per_minute", 200)),
        )
    else:
        raise ValueError(f"unknown judge backend {backend_name!r} (api | mock)")
    threshold = config.get("confidence_threshold", 0.80)
    return LLMJudge(
        backend,
        require_evidence=bool(config.get("require_evidence", True)),
        confidence_threshold=None if threshold is None else float(threshold),
        repeat=int(config.get("repeat", 0)),
    )
