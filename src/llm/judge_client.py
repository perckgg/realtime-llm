from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib import request

from src.llm.prompt_composer import estimate_tokens
from src.llm.response_cache import get_global_cache
from src.llm.schema import JudgeDecision, validate_judge_json


@dataclass
class ProviderResponse:
    raw: str
    usage: dict[str, Any]
    cache_hit: bool = False
    actual_api_call: bool = False
    retry_count: int = 0
    backoff_sleep_ms: float = 0.0
    model: str | None = None


@dataclass
class JudgeResult:
    decision: JudgeDecision | None
    raw_response: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    valid_json: bool
    error: str | None = None
    token_source: str = "estimated"
    provider: str = "unknown"
    model: str = "unknown"
    api_fallback_used: bool = False
    api_fallback_reason: str | None = None
    api_fallback_error: str | None = None
    local_result_valid_json: bool | None = None
    local_result_label: str | None = None
    local_result_confidence: float | None = None
    model_route: str = "primary"
    primary_local_model: str | None = None
    fallback_model: str | None = None
    model_fallback_used: bool = False
    model_fallback_reason: str | None = None
    cache_hit: bool = False
    actual_api_call: bool = False
    retry_count: int = 0
    backoff_sleep_ms: float = 0.0


class JudgeClient:
    def __init__(
        self,
        provider: str = "mock",
        model: str = "mock-judge",
        max_output_tokens: int = 512,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 5,
    ) -> None:
        self.provider = provider
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def judge(self, prompt: str, contexts: list[dict[str, Any]] | None = None, **_: Any) -> JudgeResult:
        started = time.perf_counter()
        prompt_tokens = estimate_tokens(prompt)
        response = ProviderResponse(raw="", usage={})
        try:
            if self.provider == "mock":
                raw = self._mock_response(contexts or [])
                actual_prompt_tokens = prompt_tokens
                actual_completion_tokens = estimate_tokens(raw)
                token_source = "estimated"
            elif self.provider == "gemini":
                response = self._gemini_response(prompt)
                raw, usage = response.raw, response.usage
                actual_prompt_tokens = int(usage.get("promptTokenCount", prompt_tokens))
                actual_completion_tokens = int(
                    usage.get("candidatesTokenCount", usage.get("completionTokenCount", estimate_tokens(raw)))
                )
                token_source = "gemini_usage_metadata" if usage else "estimated"
            elif self.provider == "ollama":
                response = self._ollama_response(prompt)
                raw, usage = response.raw, response.usage
                actual_prompt_tokens = int(usage.get("prompt_eval_count", prompt_tokens))
                actual_completion_tokens = int(usage.get("eval_count", estimate_tokens(raw)))
                token_source = "ollama_usage_metadata" if usage else "estimated"
            elif self.provider in {"openrouter", "groq", "openai_compatible"}:
                response = self._openai_compatible_response(prompt)
                raw, usage = response.raw, response.usage
                actual_prompt_tokens = int(usage.get("prompt_tokens", prompt_tokens) or prompt_tokens)
                actual_completion_tokens = int(usage.get("completion_tokens", estimate_tokens(raw)) or estimate_tokens(raw))
                token_source = f"{self.provider}_usage_metadata" if usage else "estimated"
            elif self.provider == "cohere":
                response = self._cohere_response(prompt)
                raw, usage = response.raw, response.usage
                actual_prompt_tokens = int(usage.get("input_tokens", prompt_tokens) or prompt_tokens)
                actual_completion_tokens = int(usage.get("output_tokens", estimate_tokens(raw)) or estimate_tokens(raw))
                token_source = "cohere_usage_metadata" if usage else "estimated"
            else:
                raise NotImplementedError(f"Unsupported LLM provider: {self.provider}")
        except Exception as exc:
            latency = (time.perf_counter() - started) * 1000
            error_text = str(exc)
            actual_api_call = response.actual_api_call or (
                self.provider in {"gemini", "groq", "openrouter", "openai_compatible", "cohere"}
                and "is not set" not in error_text
            )
            retry_count = int(getattr(exc, "retry_count", response.retry_count))
            backoff_sleep_ms = float(getattr(exc, "backoff_sleep_ms", response.backoff_sleep_ms))
            return JudgeResult(
                decision=None,
                raw_response="",
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                latency_ms=latency,
                valid_json=False,
                error=str(exc),
                token_source="estimated",
                provider=self.provider,
                model=response.model or self.model,
                cache_hit=response.cache_hit,
                actual_api_call=actual_api_call,
                retry_count=retry_count,
                backoff_sleep_ms=backoff_sleep_ms,
            )
        try:
            decision = validate_judge_json(raw)
            valid = True
            error = None
        except Exception as exc:
            decision = None
            valid = False
            error = str(exc)
        latency = (time.perf_counter() - started) * 1000
        return JudgeResult(
            decision=decision,
            raw_response=raw,
            prompt_tokens=actual_prompt_tokens,
            completion_tokens=actual_completion_tokens,
            latency_ms=latency,
            valid_json=valid,
            error=error,
            token_source=token_source,
            provider=self.provider,
            model=response.model or self.model,
            cache_hit=response.cache_hit,
            actual_api_call=response.actual_api_call,
            retry_count=response.retry_count,
            backoff_sleep_ms=response.backoff_sleep_ms,
        )

    def _gemini_response(self, prompt: str) -> ProviderResponse:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        cache = get_global_cache()
        extra = f"max={self.max_output_tokens}|t=0"
        cache_key = cache.make_key("gemini", self.model, prompt, extra=extra) if cache.enabled else ""
        if cache.enabled:
            cached = cache.get(cache_key)
            if cached.hit and cached.entry:
                return ProviderResponse(
                    str(cached.entry.get("raw", "")),
                    dict(cached.entry.get("usage") or {}),
                    cache_hit=True,
                    model=self.model,
                )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": self.max_output_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
                "responseMimeType": "application/json",
                "responseSchema": {
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
                },
            },
        }
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        api_response = _urlopen_json_with_retry(req, retries=self.max_retries, timeout_seconds=self.timeout_seconds)
        response_payload = api_response.payload
        candidates = response_payload.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {response_payload}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(str(part.get("text", "")) for part in parts).strip()
        if not text:
            raise RuntimeError(f"Gemini returned empty text: {response_payload}")
        usage = response_payload.get("usageMetadata") or {}
        if cache.enabled:
            cache.put(cache_key, "gemini", self.model, text, usage)
        return ProviderResponse(
            text,
            usage,
            actual_api_call=True,
            retry_count=api_response.retry_count,
            backoff_sleep_ms=api_response.backoff_sleep_ms,
            model=self.model,
        )

    def _ollama_response(self, prompt: str) -> ProviderResponse:
        cache = get_global_cache()
        extra = f"max={self.max_output_tokens}|t=0"
        cache_key = cache.make_key("ollama", self.model, prompt, extra=extra) if cache.enabled else ""
        if cache.enabled:
            cached = cache.get(cache_key)
            if cached.hit and cached.entry:
                return ProviderResponse(
                    str(cached.entry.get("raw", "")),
                    dict(cached.entry.get("usage") or {}),
                    cache_hit=True,
                    model=self.model,
                )
        base_url = (self.base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": _ollama_judge_schema(),
            "options": {
                "temperature": 0,
                "num_predict": self.max_output_tokens,
            },
        }
        req = request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = str(payload.get("response", "")).strip()
        if not text:
            raise RuntimeError(f"Ollama returned empty response: {payload}")
        if cache.enabled:
            cache.put(cache_key, "ollama", self.model, text, payload)
        return ProviderResponse(text, payload, actual_api_call=False, model=self.model)

    def _openai_compatible_response(self, prompt: str) -> ProviderResponse:
        provider_config = _openai_provider_config(self.provider, self.base_url)
        api_key = os.environ.get(provider_config["api_key_env"], "")
        if not api_key:
            raise RuntimeError(f"{provider_config['api_key_env']} is not set.")
        model = _model_or_env(self.model, provider_config.get("model_env"), provider_config["default_model"])
        self.model = model
        cache = get_global_cache()
        extra = f"max={self.max_output_tokens}|t=0|json_object"
        cache_key = cache.make_key(self.provider, model, prompt, extra=extra) if cache.enabled else ""
        if cache.enabled:
            cached = cache.get(cache_key)
            if cached.hit and cached.entry:
                return ProviderResponse(
                    str(cached.entry.get("raw", "")),
                    dict(cached.entry.get("usage") or {}),
                    cache_hit=True,
                    model=model,
                )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only a valid JSON object matching the requested alert-judge schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        if self.provider == "openrouter":
            headers.update(
                {
                    "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost"),
                    "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "Hybrid Monitoring Experiment"),
                }
            )
        req = request.Request(
            provider_config["url"],
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        api_response = _urlopen_json_with_retry(req, retries=self.max_retries, timeout_seconds=self.timeout_seconds)
        response_payload = api_response.payload
        choices = response_payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"{self.provider} returned no choices: {response_payload}")
        message = choices[0].get("message") or {}
        text = str(message.get("content", "")).strip()
        if not text:
            raise RuntimeError(f"{self.provider} returned empty content: {response_payload}")
        usage = dict(response_payload.get("usage") or {})
        if cache.enabled:
            cache.put(cache_key, self.provider, model, text, usage)
        return ProviderResponse(
            text,
            usage,
            actual_api_call=True,
            retry_count=api_response.retry_count,
            backoff_sleep_ms=api_response.backoff_sleep_ms,
            model=model,
        )

    def _cohere_response(self, prompt: str) -> ProviderResponse:
        api_key = os.environ.get("COHERE_API_KEY", "")
        if not api_key:
            raise RuntimeError("COHERE_API_KEY is not set.")
        model = _model_or_env(self.model, "COHERE_MODEL", "command-r-08-2024")
        self.model = model
        cache = get_global_cache()
        extra = f"max={self.max_output_tokens}|t=0|json_object"
        cache_key = cache.make_key("cohere", model, prompt, extra=extra) if cache.enabled else ""
        if cache.enabled:
            cached = cache.get(cache_key)
            if cached.hit and cached.entry:
                return ProviderResponse(
                    str(cached.entry.get("raw", "")),
                    dict(cached.entry.get("usage") or {}),
                    cache_hit=True,
                    model=model,
                )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        req = request.Request(
            (self.base_url or "https://api.cohere.com/v2/chat").rstrip("/"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        api_response = _urlopen_json_with_retry(req, retries=self.max_retries, timeout_seconds=self.timeout_seconds)
        response_payload = api_response.payload
        text = _cohere_text(response_payload)
        if not text:
            raise RuntimeError(f"Cohere returned empty content: {response_payload}")
        usage = _cohere_usage(response_payload)
        if cache.enabled:
            cache.put(cache_key, "cohere", model, text, usage)
        return ProviderResponse(
            text,
            usage,
            actual_api_call=True,
            retry_count=api_response.retry_count,
            backoff_sleep_ms=api_response.backoff_sleep_ms,
            model=model,
        )

    def _mock_response(self, contexts: list[dict[str, Any]]) -> str:
        severe = [ctx for ctx in contexts if ctx.get("severity") in {"ERROR", "CRITICAL"}]
        slow_trace = [
            ctx
            for ctx in contexts
            if ctx.get("severity") == "WARN" or "duration_ms=" in str(ctx.get("message", ""))
        ]
        deployment = [ctx for ctx in contexts if ctx.get("event_type") == "deployment"]
        if severe:
            label = "true_alert"
            severity = "P2"
            confidence = 0.92
            evidence = [ctx["doc_id"] for ctx in severe[:2]]
            reason = "Error logs align with the anomalous metric window."
            action = "Investigate service errors and resource saturation."
        elif slow_trace:
            label = "true_alert"
            severity = "P3"
            confidence = 0.84
            evidence = [ctx["doc_id"] for ctx in slow_trace[:2]]
            reason = "Trace latency context aligns with the anomalous metric window."
            action = "Inspect slow spans and the affected service dependency path."
        elif deployment:
            label = "false_positive"
            severity = "none"
            confidence = 0.88
            evidence = [ctx["doc_id"] for ctx in deployment[:2]]
            reason = "Metric increase aligns with a successful deployment event."
            action = "Suppress alert and continue monitoring."
        else:
            label = "uncertain"
            severity = "P3"
            confidence = 0.55
            evidence = []
            reason = "Insufficient contextual evidence."
            action = "Send to manual review."
        return json.dumps(
            {
                "label": label,
                "severity": severity,
                "confidence": confidence,
                "evidence": evidence,
                "reason": reason,
                "recommended_action": action,
            }
        )


@dataclass
class HttpJsonResponse:
    payload: dict[str, Any]
    retry_count: int = 0
    backoff_sleep_ms: float = 0.0


class HttpJsonRequestError(RuntimeError):
    def __init__(self, message: str, retry_count: int, backoff_sleep_ms: float) -> None:
        super().__init__(message)
        self.retry_count = retry_count
        self.backoff_sleep_ms = backoff_sleep_ms


def _urlopen_json_with_retry(req: request.Request, retries: int, timeout_seconds: float = 60.0) -> HttpJsonResponse:
    """POST with retry on 429/5xx.

    - Parses Google-style `retryDelay` from JSON error body when present.
    - Honors HTTP `Retry-After` header.
    - Falls back to exponential backoff with jitter (base 2s, capped 60s).
    """
    last_error: Exception | None = None
    backoff_sleep_ms = 0.0
    for attempt in range(retries + 1):
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                return HttpJsonResponse(
                    json.loads(response.read().decode("utf-8")),
                    retry_count=attempt,
                    backoff_sleep_ms=round(backoff_sleep_ms, 4),
                )
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                raise HttpJsonRequestError(
                    str(exc),
                    retry_count=attempt,
                    backoff_sleep_ms=round(backoff_sleep_ms, 4),
                ) from exc
            sleep_for = _compute_429_backoff(exc, attempt)
            backoff_sleep_ms += sleep_for * 1000
            time.sleep(sleep_for)
            continue
        except URLError as exc:
            last_error = exc
            if attempt >= retries:
                raise HttpJsonRequestError(
                    str(exc),
                    retry_count=attempt,
                    backoff_sleep_ms=round(backoff_sleep_ms, 4),
                ) from exc
            sleep_for = min(60.0, 2.0 * (2 ** attempt)) + random.uniform(0, 1.0)
            backoff_sleep_ms += sleep_for * 1000
            time.sleep(sleep_for)
    if last_error is not None:
        raise HttpJsonRequestError(
            str(last_error),
            retry_count=retries,
            backoff_sleep_ms=round(backoff_sleep_ms, 4),
        ) from last_error
    raise RuntimeError("Gemini request failed without an error.")


def _compute_429_backoff(exc: HTTPError, attempt: int) -> float:
    # 1) Honor Retry-After header if present.
    retry_after = exc.headers.get("Retry-After") if exc.headers else None
    if retry_after:
        try:
            return max(1.0, float(retry_after)) + random.uniform(0, 0.5)
        except ValueError:
            pass
    # 2) Parse Google error body for `retryDelay: "42s"`.
    try:
        body_bytes = exc.read()
    except Exception:
        body_bytes = b""
    if body_bytes:
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = None
        if isinstance(body, dict):
            details = body.get("error", {}).get("details", []) if isinstance(body.get("error"), dict) else []
            for detail in details if isinstance(details, list) else []:
                delay = detail.get("retryDelay") if isinstance(detail, dict) else None
                if isinstance(delay, str):
                    match = re.match(r"^(\d+(?:\.\d+)?)s$", delay.strip())
                    if match:
                        return max(1.0, float(match.group(1))) + random.uniform(0, 0.5)
    # 3) Exponential backoff with jitter, base 2s, cap 60s.
    base = min(60.0, 2.0 * (2 ** attempt))
    return base + random.uniform(0, 1.0)


def _openai_provider_config(provider: str, base_url: str | None) -> dict[str, str]:
    if provider == "groq":
        return {
            "api_key_env": "GROQ_API_KEY",
            "model_env": "GROQ_MODEL",
            "default_model": "llama-3.1-8b-instant",
            "url": (base_url or "https://api.groq.com/openai/v1/chat/completions").rstrip("/"),
        }
    if provider == "openrouter":
        return {
            "api_key_env": "OPENROUTER_API_KEY",
            "model_env": "OPENROUTER_MODEL",
            "default_model": "google/gemini-2.0-flash-exp:free",
            "url": (base_url or "https://openrouter.ai/api/v1/chat/completions").rstrip("/"),
        }
    return {
        "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
        "model_env": "OPENAI_COMPATIBLE_MODEL",
        "default_model": "model",
        "url": (base_url or os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "")).rstrip("/"),
    }


def _model_or_env(model: str, env_name: str | None, default: str) -> str:
    if model and model != "mock-judge":
        return model
    if env_name and os.environ.get(env_name):
        return str(os.environ[env_name])
    return default


def _cohere_text(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, list):
            return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict)).strip()
        if isinstance(content, str):
            return content.strip()
    text = payload.get("text")
    return str(text).strip() if text else ""


def _cohere_usage(payload: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage") or {}
    if not isinstance(usage, dict):
        return {}
    tokens = usage.get("tokens") if isinstance(usage.get("tokens"), dict) else usage
    return dict(tokens or {})


def _ollama_judge_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": ["true_alert", "false_positive", "uncertain"]},
            "severity": {"type": "string", "enum": ["P1", "P2", "P3", "none"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"},
            "recommended_action": {"type": "string"},
        },
        "required": ["label", "severity", "confidence", "evidence", "reason", "recommended_action"],
        "additionalProperties": False,
    }
