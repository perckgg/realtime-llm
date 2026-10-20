"""LLMJudge -- the `Judge` of 01-architecture-design.md SS5.4.

Builds GD1's prompt (services/judge/prompt.py) from the candidate and its
retrieved context, asks a backend, parses GD1's JSON schema
(legacy/src/llm/schema.py) and turns it into a JudgedAlert.

Decision rules, applied in this order to the LLM's label (`raw_verdict`):

1. Unusable answer (API error after capped retries, invalid JSON) ->
   UNCERTAIN, `debug["status"] = "manual_review"`. GD1 routed invalid JSON as
   an alert ("fallback"); GD2 never turns a failure into TRUE_ALERT. No GD1
   paper_500 answer was invalid, so this does not affect G-paper.
2. `require_evidence`: TRUE_ALERT that cites no evidence id present in the
   context -> UNCERTAIN, `downgraded_by_evidence_rule`. GD1 only checked that
   the list was non-empty; ids not in the context are dropped and kept in
   `debug["invalid_evidence_ids"]` (0 of 489 in GD1's paper_500 BM25 cache).
3. `confidence_threshold` (GD1 `decision.confidence_threshold = 0.80`):
   TRUE_ALERT below it -> UNCERTAIN, `debug["downgraded_by_threshold"]`.
   This is GD1's symmetric threshold; C2 (services/judge/policy.py, M6)
   replaces it with theta_local / theta_topo. FALSE_POSITIVE is kept at any
   confidence, as in GD1 `decide()`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Collection
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from packages.schemas.models import AlertCandidate, JudgedAlert, RetrievalResult, Verdict
from services.judge.backends import BackendResponse, JudgeBackend
from services.judge.prompt import alert_payload, compose_prompt, context_payload

_VERDICTS: dict[str, Verdict] = {
    "true_alert": "TRUE_ALERT",
    "false_positive": "FALSE_POSITIVE",
    "uncertain": "UNCERTAIN",
}


class JudgeDecision(BaseModel):
    """GD1's output schema (legacy/src/llm/schema.py)."""

    label: Literal["true_alert", "false_positive", "uncertain"]
    severity: Literal["P1", "P2", "P3", "none"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    reason: str
    recommended_action: str


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def parse_decision(text: str) -> JudgeDecision:
    return JudgeDecision.model_validate(json.loads(extract_json_object(text)))


class LLMJudge:
    name = "llm_judge"

    def __init__(
        self,
        backend: JudgeBackend,
        require_evidence: bool = True,
        confidence_threshold: float | None = 0.80,
        repeat: int = 0,
        drop_metrics: Collection[str] = (),
    ) -> None:
        self.backend = backend
        self.require_evidence = require_evidence
        self.confidence_threshold = confidence_threshold
        self.repeat = repeat
        self.drop_metrics = frozenset(drop_metrics)

    def evaluate(self, candidate: AlertCandidate, context: RetrievalResult) -> JudgedAlert:
        contexts = [context_payload(event) for event in context.events]
        prompt = compose_prompt(alert_payload(candidate, self.drop_metrics), contexts)
        started = time.perf_counter()
        response = self.backend.complete(prompt, contexts, repeat=self.repeat)
        latency = (time.perf_counter() - started) * 1000

        debug: dict[str, Any] = {
            "retrieval_strategy": context.strategy,
            "repeat": self.repeat,
            "cache_key": response.cache_key,
            "model_version": response.model_version,
            "actual_api_call": response.actual_api_call,
            "retry_count": response.retry_count,
            "prompt_chars": len(prompt),
            **_token_counts(response),
        }
        decision: JudgeDecision | None = None
        error = response.error
        if error is None:
            try:
                decision = parse_decision(response.raw)
            except (ValidationError, ValueError) as exc:
                error = f"invalid judge JSON: {exc}"
        debug["json_valid"] = decision is not None
        debug["error"] = error
        if response.raw:
            debug["raw_response"] = response.raw

        base: dict[str, Any] = {
            "alert_id": f"{candidate.candidate_id}:{context.strategy}:r{self.repeat}",
            "candidate_id": candidate.candidate_id,
            "window_id": candidate.window_id,
            "service": candidate.service,
            "ts": candidate.ts,
            "judge_backend": self.backend.name,
            "llm_latency_ms": latency,
            "cache_hit": response.cache_hit,
            "threshold_applied": self.confidence_threshold,
        }
        if decision is None:
            debug["status"] = "manual_review"
            return JudgedAlert(
                **base,
                verdict="UNCERTAIN",
                raw_verdict="UNCERTAIN",
                confidence=0.0,
                reasoning="",
                evidence_event_ids=[],
                debug=debug,
            )

        raw_verdict = _VERDICTS[decision.label]
        allowed = {event.event_id: event for event in context.events}
        evidence = [event_id for event_id in dict.fromkeys(decision.evidence) if event_id in allowed]
        debug.update(
            {
                "status": "llm_valid",
                "severity": decision.severity,
                "recommended_action": decision.recommended_action,
                "raw_evidence": decision.evidence,
                "invalid_evidence_ids": [e for e in decision.evidence if e not in allowed],
            }
        )
        verdict: Verdict = raw_verdict
        downgraded_evidence = False
        if verdict == "TRUE_ALERT" and self.require_evidence and not evidence:
            verdict, downgraded_evidence = "UNCERTAIN", True
        downgraded_threshold = (
            verdict == "TRUE_ALERT"
            and self.confidence_threshold is not None
            and decision.confidence < self.confidence_threshold
        )
        if downgraded_threshold:
            verdict = "UNCERTAIN"
        debug["downgraded_by_threshold"] = downgraded_threshold

        origins = {allowed[event_id].origin for event_id in evidence}
        evidence_origin: Literal["local", "graph", "mixed", "none"]
        if not origins:
            evidence_origin = "none"
        elif len(origins) > 1:
            evidence_origin = "mixed"
        else:
            evidence_origin = "graph" if "graph" in origins else "local"
        return JudgedAlert(
            **base,
            verdict=verdict,
            raw_verdict=raw_verdict,
            confidence=decision.confidence,
            reasoning=decision.reason,
            evidence_event_ids=evidence,
            downgraded_by_evidence_rule=downgraded_evidence,
            evidence_origin=evidence_origin,
            debug=debug,
        )


def _token_counts(response: BackendResponse) -> dict[str, Any]:
    usage = response.usage
    if "promptTokenCount" in usage:
        return {
            "prompt_tokens": int(usage.get("promptTokenCount", 0)),
            "completion_tokens": int(usage.get("candidatesTokenCount", 0)),
            "token_source": "gemini_usage_metadata",
        }
    return {"prompt_tokens": None, "completion_tokens": None, "token_source": "none"}
