"""RCA task 3: one LLM call per Incident -> DiagnosticReport (01 SS6.5, 03 SS2).

The root cause service is NOT chosen by the LLM: it is rank 1 of `propagation.py` (level 1).
Level 2 -- LLM reasoning over the call chain -- was cut (QD-037). The LLM only explains: fault
type, confidence, which evidence supports the diagnosis, and what to look at next.

Validation (03 SS2.1), applied in this order to every LLM answer:
1. no answer / not a JSON object / missing or mistyped field        -> rejected `invalid_json`
2. `confidence` outside [0, 1]                                      -> rejected `confidence_out_of_range`
3. a suggested action that looks like an executable command         -> rejected `executable_action`
4. `require_evidence`: no cited evidence id that was in the prompt  -> rejected `no_evidence`
   (ids the LLM made up are dropped and listed, like the judge's rule of 03 SS1.4)
5. root cause service not in the service graph                      -> published, `suspicious = True`

A rejected answer is never published and never silently dropped: the caller writes it to
`diagnostic_rejected` with the reason. JSON valid rate (03 SS2.2) = published / LLM calls.

Backends: `mock` (deterministic, no network; unit tests and dry runs) and Gemini through the
shared response cache of the judge (AGENTS.md rule 4), same model as the judge.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib import request

from pydantic import BaseModel, ValidationError

from packages.graph.service_graph import ServiceGraph
from packages.schemas.models import (
    ContextEvent,
    DiagnosticReport,
    EvidenceItem,
    Incident,
    JudgedAlert,
    SuggestedAction,
)
from services.judge.backends import (
    GEMINI_URL,
    BackendResponse,
    ModelVersionMismatch,
    RateLimiter,
    _post_json_with_retry,
    _RequestFailed,
)
from services.judge.cache import ResponseCache, cache_extra, make_key
from services.judge.llm_judge import extract_json_object
from services.rca_agent.propagation import RankedService

FAULT_TYPES = ("network_delay", "cpu_contention", "exception", "unknown")  # 03 SS2
PROMPT_VERSION = "rca-summary-v1"

# 03 SS2.1: GD2 only describes what to do. First word of an action (or of a `code` span in it).
COMMAND_WORDS = frozenset(
    "kubectl sudo docker rm systemctl helm pkill bash sh curl wget chmod chown apt apt-get yum dnf "
    "ssh scp git pip npm python python3 sed awk grep cat echo cd mv cp ls ps journalctl iptables "
    "netstat nslookup crictl istioctl terraform ansible".split()
)  # words that also start plain English sentences (make, kill, top, ping...) are left out on purpose
_SHELL_SYNTAX = re.compile(r"(&&|\|\||\$\()")

_PROMPT_RULES = [
    "root_cause_service is given: it was located by an algorithm, do not change or question it.",
    "fault_type must be one of the allowed values; use unknown when the evidence does not decide.",
    "evidence must list 1 to 4 ids taken from allowed_evidence_ids, the ones that best support "
    "the diagnosis. Never invent an id.",
    "propagation_path lists services from the root cause outwards, using only services named in "
    "this prompt.",
    "suggested_actions: 1 to 3 short descriptions of what an engineer should inspect or change. "
    "Plain English sentences only: no shell commands, no code, no backticks.",
    "confidence is a number between 0 and 1.",
    "Return only JSON.",
]

_OUTPUT_SCHEMA = {
    "fault_type": " | ".join(FAULT_TYPES),
    "confidence": 0.0,
    "evidence": ["event_id"],
    "propagation_path": ["service"],
    "suggested_actions": [{"description": "one sentence, max 25 words", "priority": "high | medium | low"}],
}

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "fault_type": {"type": "STRING", "enum": list(FAULT_TYPES)},
        "confidence": {"type": "NUMBER"},
        "evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
        "propagation_path": {"type": "ARRAY", "items": {"type": "STRING"}},
        "suggested_actions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING"},
                    "priority": {"type": "STRING", "enum": ["high", "medium", "low"]},
                },
                "required": ["description", "priority"],
            },
        },
    },
    "required": ["fault_type", "confidence", "evidence", "propagation_path", "suggested_actions"],
}


def prompt_fingerprint() -> str:
    """Hash of everything fixed in the prompt; `rca_final.yaml` pins it so the prompt cannot
    change unnoticed between the val run and the test run."""
    fixed = json.dumps(
        {"version": PROMPT_VERSION, "rules": _PROMPT_RULES, "schema": _OUTPUT_SCHEMA, "response": _RESPONSE_SCHEMA},
        sort_keys=True,
    )
    return hashlib.sha256(fixed.encode("utf-8")).hexdigest()[:16]


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat().replace("+00:00", "Z")


def compose_prompt(
    incident: Incident,
    alerts: Sequence[JudgedAlert],
    ranked: Sequence[RankedService],
    path: Sequence[str],
    evidence: Sequence[ContextEvent],
    call_edges: Sequence[tuple[str, str]],
    excerpt_chars: int = 240,
) -> str:
    """No ground truth and no anomaly-count goes in: only what the pipeline knows online."""
    payload = {
        "role": "SRE incident diagnosis writer",
        "task": (
            "Write the diagnostic report of one incident. The alerts were already validated and "
            "grouped, and the root cause service was already located."
        ),
        "incident": {
            "incident_id": incident.incident_id,
            "start": _iso(incident.start_ts),
            "end": _iso(incident.end_ts),
            "services": list(incident.services),
            "root_cause_service": ranked[0].service if ranked else None,
            "root_cause_ranking": [
                {"service": r.service, "score": round(r.score, 4), "alerted": r.alerted} for r in ranked[:3]
            ],
            "propagation_path_hint": list(path),
            "call_edges": [f"{a} -> {b}" for a, b in call_edges],
        },
        "alerts": [
            {"service": a.service, "ts": _iso(a.ts), "confidence": a.confidence, "judge_reason": a.reasoning[:240]}
            for a in alerts
        ],
        "evidence": [
            {
                "event_id": e.event_id,
                "modality": e.modality,
                "service": e.service,
                "ts": _iso(e.ts),
                "content": e.content[:excerpt_chars],
            }
            for e in evidence
        ],
        "allowed_evidence_ids": [e.event_id for e in evidence],
        "allowed_fault_types": list(FAULT_TYPES),
        "output_schema": _OUTPUT_SCHEMA,
        "rules": _PROMPT_RULES,
    }
    return json.dumps(payload, ensure_ascii=False, indent=1)


# --- backends ------------------------------------------------------------------------------


class SummaryBackend(Protocol):
    name: str

    def complete(self, prompt: str) -> BackendResponse: ...


class MockSummaryBackend:
    """Deterministic answer built from the prompt itself: first two allowed evidence ids,
    `unknown` fault type. For unit tests and dry runs -- never a result of the thesis."""

    name = "mock"

    def complete(self, prompt: str) -> BackendResponse:
        payload = json.loads(prompt)
        raw = json.dumps(
            {
                "fault_type": "unknown",
                "confidence": 0.5,
                "evidence": payload["allowed_evidence_ids"][:2],
                "propagation_path": payload["incident"]["propagation_path_hint"],
                "suggested_actions": [
                    {
                        "description": f"Inspect recent telemetry of {payload['incident']['root_cause_service']}.",
                        "priority": "medium",
                    }
                ],
            }
        )
        return BackendResponse(raw=raw, model_version="mock")


class GeminiSummaryBackend:
    """Same transport, retry policy and cache file as the judge (services/judge/backends.py);
    only the response schema differs. A cache hit needs no API key."""

    def __init__(
        self,
        cache: ResponseCache,
        model: str,
        max_output_tokens: int,
        timeout_seconds: float = 60.0,
        max_retries: int = 5,
        max_calls_per_minute: int = 60,
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

    def cache_key(self, prompt: str) -> str:
        return make_key("gemini", self.model, prompt, cache_extra(self.max_output_tokens))

    def complete(self, prompt: str) -> BackendResponse:
        key = self.cache_key(prompt)
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
        body_out = {
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
            data=json.dumps(body_out).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            body, retries = _post_json_with_retry(req, self.max_retries, self.timeout_seconds, self.limiter)
        except _RequestFailed as exc:
            return BackendResponse(raw="", cache_key=key, actual_api_call=True, retry_count=exc.retry_count, error=str(exc))
        candidates = body.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(str(part.get("text", "")) for part in parts).strip()
        usage = body.get("usageMetadata") or {}
        if not text:
            return BackendResponse(
                raw="", usage=usage, cache_key=key, actual_api_call=True, retry_count=retries,
                error=f"Gemini returned no text: {json.dumps(body)[:500]}",
            )  # fmt: skip
        model_version = body.get("modelVersion")
        if model_version and model_version != self.model:
            raise ModelVersionMismatch(f"requested {self.model!r}, API served {model_version!r}")  # QD-020
        self.cache.put(
            key,
            {"provider": "gemini", "model": self.model, "raw": text, "usage": usage,
             "model_version": model_version, "repeat": 0, "purpose": PROMPT_VERSION},
        )  # fmt: skip
        return BackendResponse(
            raw=text, usage=usage, cache_key=key, actual_api_call=True, retry_count=retries, model_version=model_version
        )


# --- validation ----------------------------------------------------------------------------


class _LLMAnswer(BaseModel):
    fault_type: str
    confidence: float
    evidence: list[str]
    propagation_path: list[str]
    suggested_actions: list[SuggestedAction]


def looks_executable(text: str) -> bool:
    """True when an action reads like a command rather than a description (03 SS2.1)."""
    stripped = text.strip()
    segments = [stripped, *re.findall(r"`+([^`]+)`+", stripped)]
    for segment in segments:
        words = segment.strip().lstrip("$#> ").split()
        if words and words[0].lower().rstrip(":") in COMMAND_WORDS:
            return True
    return bool(_SHELL_SYNTAX.search(stripped)) or "```" in stripped


@dataclass
class SummaryResult:
    incident_id: str
    report: DiagnosticReport | None
    reject_reason: str | None  # None when published
    raw_output: str
    llm_called: bool
    suspicious: bool = False
    invalid_evidence_ids: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return self.report is not None


def validate_answer(
    raw: str,
    incident: Incident,
    root_cause_service: str,
    evidence: Sequence[ContextEvent],
    graph: ServiceGraph,
    llm_backend: str,
    require_evidence: bool = True,
    generated_at: datetime | None = None,
    excerpt_chars: int = 240,
) -> tuple[DiagnosticReport | None, str | None, bool, list[str]]:
    """(report, reject_reason, suspicious, invalid_evidence_ids); exactly one of the first two is set."""
    try:
        parsed = json.loads(extract_json_object(raw))
        if not isinstance(parsed, dict):
            raise ValueError("not a JSON object")
        answer = _LLMAnswer.model_validate(parsed)
    except (ValueError, ValidationError) as exc:
        return None, f"invalid_json: {str(exc)[:200]}", False, []
    if not 0.0 <= answer.confidence <= 1.0:
        return None, f"confidence_out_of_range: {answer.confidence}", False, []
    for action in answer.suggested_actions:
        if looks_executable(action.description):
            return None, f"executable_action: {action.description[:120]}", False, []
    by_id = {e.event_id: e for e in evidence}
    invalid = [eid for eid in answer.evidence if eid not in by_id]
    cited = [by_id[eid] for eid in dict.fromkeys(answer.evidence) if eid in by_id]
    if not cited:
        if require_evidence or not evidence:
            return None, "no_evidence: no cited evidence id is in the prompt", False, invalid
        cited = [evidence[0]]
    suspicious = root_cause_service not in graph.directed
    try:
        report = DiagnosticReport(
            incident_id=incident.incident_id,
            run_id=incident.run_id,
            root_cause_service=root_cause_service,
            fault_type=answer.fault_type if answer.fault_type in FAULT_TYPES else "unknown",
            confidence=answer.confidence,
            evidence=[
                EvidenceItem(event_id=e.event_id, modality=e.modality, service=e.service, ts=e.ts,
                             excerpt=e.content[:excerpt_chars])
                for e in cited
            ],  # fmt: skip
            propagation_path=answer.propagation_path,
            suggested_actions=answer.suggested_actions,
            generated_at=generated_at or datetime.now(UTC),
            llm_backend=llm_backend,
        )
    except ValidationError as exc:
        return None, f"schema: {str(exc)[:200]}", False, invalid
    return report, None, suspicious, invalid


class Summarizer:
    def __init__(
        self,
        backend: SummaryBackend,
        graph: ServiceGraph,
        require_evidence: bool = True,
        max_evidence: int = 12,
        excerpt_chars: int = 240,
    ) -> None:
        self.backend = backend
        self.graph = graph
        self.require_evidence = require_evidence
        self.max_evidence = max_evidence
        self.excerpt_chars = excerpt_chars

    def summarize(
        self,
        incident: Incident,
        alerts: Sequence[JudgedAlert],
        ranked: Sequence[RankedService],
        path: Sequence[str],
        evidence: Sequence[ContextEvent],
    ) -> SummaryResult:
        """`evidence`: the events the incident's alerts cited, root-cause service first."""
        if not ranked:
            return SummaryResult(incident.incident_id, None, "no_root_cause_candidate", "", llm_called=False)
        if self.require_evidence and not evidence:
            # nothing to cite -> no diagnosis is published, and no LLM call is spent on it
            return SummaryResult(incident.incident_id, None, "no_evidence: incident has no evidence event", "",
                                 llm_called=False)  # fmt: skip
        shown = list(evidence[: self.max_evidence])
        services = set(incident.services) | {r.service for r in ranked[:3]}
        edges = sorted((a, b) for a, b in self.graph.directed.edges if a in services and b in services)
        prompt = compose_prompt(incident, alerts, ranked, path, shown, edges, self.excerpt_chars)
        response = self.backend.complete(prompt)
        debug = {
            "cache_hit": response.cache_hit,
            "cache_key": response.cache_key,
            "actual_api_call": response.actual_api_call,
            "retry_count": response.retry_count,
            "model_version": response.model_version,
            "prompt_chars": len(prompt),
            "prompt_tokens": int(response.usage.get("promptTokenCount") or 0),
            "completion_tokens": int(response.usage.get("candidatesTokenCount") or 0),
            "evidence_shown": len(shown),
        }
        if response.error:
            return SummaryResult(incident.incident_id, None, f"llm_error: {response.error[:200]}", response.raw,
                                 llm_called=True, debug=debug)  # fmt: skip
        report, reason, suspicious, invalid = validate_answer(
            response.raw, incident, ranked[0].service, shown, self.graph, self.backend.name,
            self.require_evidence, excerpt_chars=self.excerpt_chars,
        )  # fmt: skip
        return SummaryResult(incident.incident_id, report, reason, response.raw, True, suspicious, invalid, debug)
