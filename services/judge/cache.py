"""Persistent LLM response cache, file-compatible with GD1.

Same JSONL format and key as legacy/src/llm/response_cache.py:

    key = sha256(provider | model | prompt | "max=<max_output_tokens>|t=0")

so GD1's cache files (e.g. legacy/outputs/phase2/step7_rerun/quality_full_budget/
cache/paper_500/*.jsonl) can be read as-is (M3, G-paper). GD2 adds a `repeat`
index (08 SS4.1): `repeat = 0` produces GD1's key unchanged, `repeat = n > 0`
appends "|repeat=n" so a variance run really calls the API again instead of
reading the answer of repeat 0. Entries GD2 writes also carry `model_version`
(what the API reported) and `repeat`; GD1 readers ignore extra fields.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any


def cache_extra(max_output_tokens: int, repeat: int = 0) -> str:
    extra = f"max={max_output_tokens}|t=0"
    return f"{extra}|repeat={repeat}" if repeat else extra


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


class ResponseCache:
    """Append-only JSONL. Reads every file in `read_paths` (later wins) and
    writes new entries to `path`; `path=None` disables writing."""

    def __init__(self, path: Path | None, read_paths: list[Path] | None = None) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        for source in [*(read_paths or []), *([path] if path else [])]:
            if source.exists():
                self._load(source)

    def _load(self, source: Path) -> None:
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("key"):
                    self._entries[entry["key"]] = entry

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._entries.get(key)
            return dict(entry) if entry else None

    def put(self, key: str, entry: dict[str, Any]) -> None:
        record = {"key": key, **entry}
        with self._lock:
            self._entries[key] = record
            if self.path is None:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
