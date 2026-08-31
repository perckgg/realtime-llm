from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheLookup:
    hit: bool
    entry: dict[str, Any] | None = None


class ResponseCache:
    """Persistent JSONL response cache keyed by (provider, model, prompt_hash).

    Designed to dramatically reduce real-LLM API usage when re-running
    experiments. Cache hits return the original raw response and usage
    metadata, avoiding 429/quota issues.
    """

    def __init__(self, path: str | Path | None) -> None:
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self._load()

    @property
    def enabled(self) -> bool:
        return self.path is not None

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = entry.get("key")
                if key:
                    self._entries[key] = entry

    @staticmethod
    def make_key(provider: str, model: str, prompt: str, extra: str = "") -> str:
        hasher = hashlib.sha256()
        hasher.update(provider.encode("utf-8"))
        hasher.update(b"|")
        hasher.update(model.encode("utf-8"))
        hasher.update(b"|")
        hasher.update(prompt.encode("utf-8"))
        if extra:
            hasher.update(b"|")
            hasher.update(extra.encode("utf-8"))
        return hasher.hexdigest()

    def get(self, key: str) -> CacheLookup:
        if not self.enabled:
            return CacheLookup(hit=False)
        with self._lock:
            entry = self._entries.get(key)
            return CacheLookup(hit=entry is not None, entry=dict(entry) if entry else None)

    def put(self, key: str, provider: str, model: str, raw: str, usage: dict[str, Any]) -> None:
        if not self.enabled:
            return
        entry = {
            "key": key,
            "provider": provider,
            "model": model,
            "raw": raw,
            "usage": usage,
        }
        with self._lock:
            self._entries[key] = entry
            assert self.path is not None
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


_GLOBAL_CACHE: ResponseCache | None = None


def get_global_cache() -> ResponseCache:
    """Returns a process-wide cache, controlled by LLM_RESPONSE_CACHE env var.

    Set LLM_RESPONSE_CACHE=/path/to/cache.jsonl to enable.
    Set LLM_RESPONSE_CACHE=off to disable.
    Default: disabled.
    """
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is not None:
        return _GLOBAL_CACHE
    path = os.environ.get("LLM_RESPONSE_CACHE", "").strip()
    if not path or path.lower() in {"off", "false", "0", "no"}:
        _GLOBAL_CACHE = ResponseCache(None)
    else:
        _GLOBAL_CACHE = ResponseCache(path)
    return _GLOBAL_CACHE


def reset_global_cache_for_tests() -> None:
    global _GLOBAL_CACHE
    _GLOBAL_CACHE = None
