"""Judge backends: one fixed Gemini model over the API and `mock`.

Judge of every GD2 experiment: `JUDGE_MODEL` = `gemini-2.5-flash` (QD-021,
replacing `gemini-2.5-flash-lite` of QD-013). `PAPER_MODEL` =
`gemini-2.5-flash-lite` is only used to replay the paper's cache (G-paper).
The model is always passed explicitly -- there is no default -- so no caller
switches model by accident.

`GeminiBackend` is GD1's `JudgeClient._gemini_response`
(legacy/src/llm/judge_client.py): same request (temperature 0, thinking
budget 0, JSON response schema), same cache key, same retry policy (429/5xx
and network errors, honouring Retry-After / retryDelay, exponential backoff
capped at 60 s). Thread-safe (QD-019): the harness judges candidates from
several worker threads; every HTTP attempt, retries included, takes a slot
from one shared `RateLimiter` (default 200 calls/min, Tier-1 quota is
1,000+ RPM for Flash models), and the cache is lock-protected. Retries are capped (`max_retries`); when they run out the
backend returns an error and LLMJudge records the alert for manual review --
it never falls back to another model. A cache hit needs no API key, so a
cached run (and the defence demo) works offline.

`MockBackend` is GD1's `_mock_response`, kept only for the G-port gate.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field
from http.client import HTTPException
from typing import Any, Protocol
from urllib import request
from urllib.error import HTTPError

from services.judge.cache import ResponseCache, cache_extra, make_key

JUDGE_MODEL = "gemini-2.5-flash"  # QD-021
PAPER_MODEL = "gemini-2.5-flash-lite"  # QD-013; the paper's cache (G-paper) only
# USD per 1M tokens (input, output), Google's published standard-tier prices
# as known on 2026-10-19 -- verify against the billing page; used for estimates only.
PRICES_PER_1M = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
    # QD-022: third-party price trackers, 2026-10-20 (introductory until 2026-12-31,
    # expected to double in 2027) -- not from Google's page; estimates only.
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.8-flash": (0.75, 3.75),
}

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "label": {"type": "STRING", "enum": ["true_alert", "false_positive", "uncertain"]},
        "severity": {"type": "STRING", "enum": ["P1", "P2", "P3", "none"]},
        "confidence": {"type": "NUMBER"},
        "evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
        "reason": {"type": "STRING"},
        "recommended_action": {"type": "STRING"},
    },
    "required": ["label", "severity", "confidence", "evidence", "reason", "recommended_action"],
}


@dataclass
class BackendResponse:
    raw: str
    usage: dict[str, Any] = field(default_factory=dict)
    cache_hit: bool = False
    cache_key: str | None = None
    actual_api_call: bool = False
    retry_count: int = 0
    model_version: str | None = None
    error: str | None = None


class JudgeBackend(Protocol):
    name: str  # recorded as JudgedAlert.judge_backend

    def complete(self, prompt: str, contexts: list[dict[str, Any]], repeat: int = 0) -> BackendResponse: ...


class MockBackend:
    """GD1 mock judge: ERROR/CRITICAL context -> true_alert P2; slow trace ->
    true_alert P3; deployment -> false_positive; else uncertain."""

    name = "mock"

    def complete(self, prompt: str, contexts: list[dict[str, Any]], repeat: int = 0) -> BackendResponse:
        severe = [ctx for ctx in contexts if ctx.get("severity") in {"ERROR", "CRITICAL"}]
        slow_trace = [
            ctx
            for ctx in contexts
            if ctx.get("severity") == "WARN" or "duration_ms=" in str(ctx.get("message", ""))
        ]
        deployment = [ctx for ctx in contexts if ctx.get("event_type") == "deployment"]
        if severe:
            label, severity, confidence = "true_alert", "P2", 0.92
            evidence = [ctx["doc_id"] for ctx in severe[:2]]
            reason = "Error logs align with the anomalous metric window."
            action = "Investigate service errors and resource saturation."
        elif slow_trace:
            label, severity, confidence = "true_alert", "P3", 0.84
            evidence = [ctx["doc_id"] for ctx in slow_trace[:2]]
            reason = "Trace latency context aligns with the anomalous metric window."
            action = "Inspect slow spans and the affected service dependency path."
        elif deployment:
            label, severity, confidence = "false_positive", "none", 0.88
            evidence = [ctx["doc_id"] for ctx in deployment[:2]]
            reason = "Metric increase aligns with a successful deployment event."
            action = "Suppress alert and continue monitoring."
        else:
            label, severity, confidence = "uncertain", "P3", 0.55
            evidence = []
            reason = "Insufficient contextual evidence."
            action = "Send to manual review."
        raw = json.dumps(
            {
                "label": label,
                "severity": severity,
                "confidence": confidence,
                "evidence": evidence,
                "reason": reason,
                "recommended_action": action,
            }
        )
        return BackendResponse(raw=raw, model_version="mock")


class RateLimiter:
    """At most `per_minute` acquisitions per minute across threads, evenly
    spaced (one slot every 60 / per_minute s); `per_minute <= 0` disables it."""

    def __init__(self, per_minute: int) -> None:
        self.interval = 60.0 / per_minute if per_minute > 0 else 0.0
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self) -> None:
        if not self.interval:
            return
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next)
            self._next = slot + self.interval
        if slot > now:
            time.sleep(slot - now)


class GeminiBackend:
    def __init__(
        self,
        cache: ResponseCache,
        model: str,
        max_output_tokens: int = 1024,  # GD1 Step 7 (paper) value; part of the cache key
        timeout_seconds: float = 60.0,
        max_retries: int = 5,
        max_calls_per_minute: int = 200,  # QD-019; GD1 used 15 (free tier)
        api_key: str | None = None,
    ) -> None:
        self.cache = cache
        self.model = model
        self.name = model
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.limiter = RateLimiter(max_calls_per_minute)
        self._api_key = api_key

    def cache_key(self, prompt: str, repeat: int = 0) -> str:
        return make_key("gemini", self.model, prompt, cache_extra(self.max_output_tokens, repeat))

    def complete(self, prompt: str, contexts: list[dict[str, Any]], repeat: int = 0) -> BackendResponse:
        key = self.cache_key(prompt, repeat)
        entry = self.cache.get(key)
        if entry is not None:
            return BackendResponse(
                raw=str(entry.get("raw", "")),
                usage=dict(entry.get("usage") or {}),
                cache_hit=True,
                cache_key=key,
                model_version=entry.get("model_version"),
            )
        api_key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return BackendResponse(raw="", cache_key=key, error="cache miss and GEMINI_API_KEY is not set")
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": self.max_output_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
            },
        }
        req = request.Request(
            GEMINI_URL.format(model=self.model),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            body, retries = _post_json_with_retry(req, self.max_retries, self.timeout_seconds, self.limiter)
        except _RequestFailed as exc:
            return BackendResponse(
                raw="", cache_key=key, actual_api_call=True, retry_count=exc.retry_count, error=str(exc)
            )
        candidates = body.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(str(part.get("text", "")) for part in parts).strip()
        if not text:
            return BackendResponse(
                raw="", cache_key=key, actual_api_call=True, retry_count=retries,
                error=f"Gemini returned no text: {json.dumps(body)[:500]}",
            )
        usage = body.get("usageMetadata") or {}
        model_version = body.get("modelVersion")
        if model_version and model_version != self.model:
            # QD-020: some Gemini ids are silently served by a newer model
            # (gemini-3.7-flash -> gemini-3.8-flash on 2026-10-19). A run must
            # be judged by one model, so stop instead of mixing; not cached.
            raise ModelVersionMismatch(f"requested {self.model!r}, API served {model_version!r}")
        self.cache.put(
            key,
            {
                "provider": "gemini",
                "model": self.model,
                "raw": text,
                "usage": usage,
                "model_version": model_version,
                "repeat": repeat,
            },
        )
        return BackendResponse(
            raw=text, usage=usage, cache_key=key, actual_api_call=True,
            retry_count=retries, model_version=model_version,
        )

class ModelVersionMismatch(RuntimeError):
    """The API answered with a different model than the one configured (QD-020)."""


class _RequestFailed(RuntimeError):
    def __init__(self, message: str, retry_count: int) -> None:
        super().__init__(message)
        self.retry_count = retry_count


def _post_json_with_retry(
    req: request.Request, retries: int, timeout_seconds: float, limiter: RateLimiter | None = None
) -> tuple[dict[str, Any], int]:
    """GD1 `_urlopen_json_with_retry`: retry 429/5xx and network errors, at most `retries` times."""
    for attempt in range(retries + 1):
        if limiter is not None:
            limiter.acquire()
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8")), attempt
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                raise _RequestFailed(f"HTTP {exc.code}: {exc.reason}", attempt) from exc
            time.sleep(_backoff_seconds(exc, attempt))
        except (OSError, HTTPException) as exc:
            # URLError, and also errors raised while reading the body (TimeoutError,
            # ConnectionResetError, RemoteDisconnected, IncompleteRead), which urllib does not wrap
            if attempt >= retries:
                raise _RequestFailed(str(exc), attempt) from exc
            time.sleep(min(60.0, 2.0 * (2**attempt)) + random.uniform(0, 1.0))
    raise _RequestFailed("request failed without an error", retries)


def _backoff_seconds(exc: HTTPError, attempt: int) -> float:
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after:
        try:
            return max(1.0, float(retry_after)) + random.uniform(0, 0.5)
        except ValueError:
            pass
    try:
        body = json.loads(exc.read().decode("utf-8"))
    except (OSError, ValueError):
        body = None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        for detail in body["error"].get("details", []) or []:
            delay = detail.get("retryDelay") if isinstance(detail, dict) else None
            if isinstance(delay, str):
                match = re.match(r"^(\d+(?:\.\d+)?)s$", delay.strip())
                if match:
                    return max(1.0, float(match.group(1))) + random.uniform(0, 0.5)
    return min(60.0, 2.0 * (2**attempt)) + random.uniform(0, 1.0)
