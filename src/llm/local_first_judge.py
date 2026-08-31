from __future__ import annotations

import time
from typing import Any

from src.llm.judge_client import JudgeClient, JudgeResult
from src.models import AlertCandidate


class LocalFirstJudgeClient:
    def __init__(
        self,
        local_client: JudgeClient,
        fallback_client: JudgeClient | None,
        confidence_threshold: float = 0.80,
        fallback_on_uncertain: bool = True,
        high_anomaly_fallback_threshold: float = 0.98,
    ) -> None:
        self.local_client = local_client
        self.fallback_client = fallback_client
        self.confidence_threshold = confidence_threshold
        self.fallback_on_uncertain = fallback_on_uncertain
        self.high_anomaly_fallback_threshold = high_anomaly_fallback_threshold
        self.provider = "local_first"
        self.model = f"{local_client.provider}:{local_client.model}"

    def judge(
        self,
        prompt: str,
        contexts: list[dict[str, Any]] | None = None,
        alert: AlertCandidate | None = None,
        allow_api_fallback: bool = True,
    ) -> JudgeResult:
        started = time.perf_counter()
        local_result = self.local_client.judge(prompt, contexts)
        reason = self._fallback_reason(local_result, alert)
        if reason is None or self.fallback_client is None or not allow_api_fallback:
            local_result.api_fallback_used = False
            local_result.api_fallback_reason = None if reason is None else f"api_fallback_blocked:{reason}"
            local_result.local_result_valid_json = local_result.valid_json
            if local_result.decision is not None:
                local_result.local_result_label = local_result.decision.label
                local_result.local_result_confidence = local_result.decision.confidence
            local_result.model_route = "primary"
            local_result.primary_local_model = f"{self.local_client.provider}:{self.local_client.model}"
            local_result.fallback_model = (
                f"{self.fallback_client.provider}:{self.fallback_client.model}" if self.fallback_client else None
            )
            local_result.model_fallback_used = False
            local_result.model_fallback_reason = None if reason is None else f"fallback_blocked:{reason}"
            return local_result

        fallback_result = self.fallback_client.judge(prompt, contexts)
        if fallback_result.error:
            local_result.latency_ms = (time.perf_counter() - started) * 1000
            local_result.api_fallback_used = fallback_is_external_api = self.fallback_client.provider in {
                "gemini",
                "groq",
                "openrouter",
                "openai_compatible",
                "cohere",
            }
            local_result.api_fallback_reason = reason
            local_result.api_fallback_error = fallback_result.error
            local_result.local_result_valid_json = local_result.valid_json
            if local_result.decision is not None:
                local_result.local_result_label = local_result.decision.label
                local_result.local_result_confidence = local_result.decision.confidence
            local_result.model_route = "primary_after_failed_fallback"
            local_result.primary_local_model = f"{self.local_client.provider}:{self.local_client.model}"
            local_result.fallback_model = f"{self.fallback_client.provider}:{self.fallback_client.model}"
            local_result.model_fallback_used = False
            local_result.model_fallback_reason = f"fallback_failed:{reason}"
            local_result.actual_api_call = local_result.actual_api_call or fallback_result.actual_api_call
            local_result.retry_count = local_result.retry_count + fallback_result.retry_count
            local_result.backoff_sleep_ms = local_result.backoff_sleep_ms + fallback_result.backoff_sleep_ms
            return local_result

        fallback_result.latency_ms = (time.perf_counter() - started) * 1000
        fallback_is_external_api = self.fallback_client.provider in {"gemini", "groq", "openrouter", "openai_compatible", "cohere"}
        fallback_result.api_fallback_used = fallback_is_external_api
        fallback_result.api_fallback_reason = reason
        fallback_result.local_result_valid_json = local_result.valid_json
        if local_result.decision is not None:
            fallback_result.local_result_label = local_result.decision.label
            fallback_result.local_result_confidence = local_result.decision.confidence
        fallback_result.model_route = "fallback"
        fallback_result.primary_local_model = f"{self.local_client.provider}:{self.local_client.model}"
        fallback_result.fallback_model = f"{self.fallback_client.provider}:{self.fallback_client.model}"
        fallback_result.model_fallback_used = True
        fallback_result.model_fallback_reason = reason
        return fallback_result

    def _fallback_reason(self, result: JudgeResult, alert: AlertCandidate | None) -> str | None:
        if alert is not None and alert.anomaly_score >= self.high_anomaly_fallback_threshold:
            return "high_anomaly_score"
        if result.error:
            return "local_error"
        if not result.valid_json or result.decision is None:
            return "local_invalid_json"
        if self.fallback_on_uncertain and result.decision.label == "uncertain":
            return "local_uncertain"
        if result.decision.confidence < self.confidence_threshold:
            return "local_low_confidence"
        return None


def build_judge_client(config: dict[str, Any]) -> JudgeClient | LocalFirstJudgeClient:
    provider = str(config.get("provider", "mock"))
    if provider != "local_first":
        return JudgeClient(
            provider=provider,
            model=str(config.get("model", "mock-judge")),
            max_output_tokens=int(config.get("max_output_tokens", 512)),
            base_url=config.get("base_url"),
            timeout_seconds=float(config.get("timeout_seconds", 30.0)),
            max_retries=int(config.get("max_retries", 5)),
        )

    local_client = JudgeClient(
        provider=str(config.get("local_provider", "ollama")),
        model=str(config.get("local_model", "qwen2.5:1.5b")),
        max_output_tokens=int(config.get("local_max_output_tokens", config.get("max_output_tokens", 512))),
        base_url=str(config.get("ollama_base_url", config.get("local_base_url", "http://localhost:11434"))),
        timeout_seconds=float(config.get("local_timeout_seconds", 30.0)),
        max_retries=int(config.get("local_max_retries", config.get("max_retries", 5))),
    )
    fallback_provider = config.get("fallback_provider")
    fallback_client = None
    if fallback_provider:
        fallback_client = JudgeClient(
            provider=str(fallback_provider),
            model=str(config.get("fallback_model", config.get("model", "gemini-2.5-flash"))),
            max_output_tokens=int(config.get("fallback_max_output_tokens", config.get("max_output_tokens", 512))),
            base_url=config.get("fallback_base_url"),
            timeout_seconds=float(config.get("fallback_timeout_seconds", 30.0)),
            max_retries=int(config.get("fallback_max_retries", config.get("max_retries", 5))),
        )
    return LocalFirstJudgeClient(
        local_client=local_client,
        fallback_client=fallback_client,
        confidence_threshold=float(config.get("local_confidence_threshold", 0.80)),
        fallback_on_uncertain=bool(config.get("fallback_on_uncertain", True)),
        high_anomaly_fallback_threshold=float(config.get("high_anomaly_fallback_threshold", 0.98)),
    )
