"""services.judge: GD1-verbatim prompt and mock, GD1-compatible cache key with
`repeat`, decision rules (require_evidence, threshold, failures)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from packages.schemas.models import AlertCandidate, ContextEvent, RetrievalResult
from services.judge.backends import (
    JUDGE_MODEL,
    PAPER_MODEL,
    BackendResponse,
    GeminiBackend,
    MockBackend,
)
from services.judge.cache import ResponseCache, cache_extra, make_key
from services.judge.llm_judge import LLMJudge
from services.judge.prompt import compose_prompt
from services.judge.registry import build_judge
from tests.gd1 import LEGACY, gd1

FIXTURE = Path(__file__).parent / "fixtures" / "gd1_prompt_cases.json"
GD1_CACHE = LEGACY / "outputs/phase2/step7_rerun/quality_full_budget/cache/paper_500/hybrid_bm25_top6.jsonl"
T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)


def _candidate() -> AlertCandidate:
    return AlertCandidate(
        candidate_id="cand-1",
        window_id="w1",
        service="cartservice",
        pod="cartservice-x",
        ts=T0,
        end_ts=T0 + timedelta(seconds=60),
        anomaly_score=0.91234567,
        source="metric",
        metric_snapshot={"CpuUsage(m)": 1.23456789},
    )


def _event(event_id: str, origin: str = "local", severity: str = "INFO", message: str = "ok") -> ContextEvent:
    return ContextEvent(
        event_id=event_id,
        modality="log",
        ts=T0,
        service="cartservice",
        content=message,
        score=0.5,
        origin=origin,  # type: ignore[arg-type]
        debug={"source": "nezha_log", "severity": severity, "event_type": "application_log"},
    )


def _context(*events: ContextEvent) -> RetrievalResult:
    return RetrievalResult(strategy="bm25_hybrid", events=list(events), latency_ms=1.0, token_estimate=1)


class _Fixed:
    """Backend that returns a canned answer."""

    name = "fixed"

    def __init__(self, answer: dict[str, Any] | str | None, error: str | None = None) -> None:
        self.answer = answer
        self.error = error

    def complete(self, prompt: str, contexts: list[dict[str, Any]], repeat: int = 0) -> BackendResponse:
        if isinstance(self.answer, str):
            raw = self.answer
        else:
            raw = json.dumps(self.answer) if self.answer else ""
        return BackendResponse(raw=raw, error=self.error)


def _answer(label: str, confidence: float = 0.9, evidence: list[str] | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "severity": "P2",
        "confidence": confidence,
        "evidence": evidence or [],
        "reason": "r",
        "recommended_action": "a",
    }


# --- prompt and cache key: byte-identical to GD1 ------------------------------------------


def test_prompt_and_key_reproduce_gd1_cache_entries():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    gd1_keys = {json.loads(line)["key"] for line in GD1_CACHE.open(encoding="utf-8")}
    backend = GeminiBackend(ResponseCache(None), model=PAPER_MODEL)
    for case in cases:
        prompt = compose_prompt(case["alert"], case["contexts"])
        assert backend.cache_key(prompt) == case["cache_key"]
        assert case["cache_key"] in gd1_keys


def test_prompt_is_gd1_compose_prompt():
    models = gd1("src.models")
    composer = gd1("src.llm.prompt_composer")
    case = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][0]
    alert = models.AlertCandidate(**case["alert"])
    assert compose_prompt(case["alert"], case["contexts"]) == composer.compose_prompt(alert, case["contexts"])


def test_cache_key_is_gd1_key_for_repeat_0_and_new_for_repeat_n():
    gd1_cache = gd1("src.llm.response_cache").ResponseCache
    prompt = "p"
    gd1_key = gd1_cache.make_key("gemini", "gemini-2.5-flash-lite", prompt, extra="max=1024|t=0")
    assert make_key("gemini", "gemini-2.5-flash-lite", prompt, cache_extra(1024, 0)) == gd1_key
    keys = {make_key("gemini", "gemini-2.5-flash-lite", prompt, cache_extra(1024, r)) for r in (0, 1, 2)}
    assert len(keys) == 3
    assert make_key("gemini", "gemini-2.5-flash-lite", prompt, cache_extra(512, 0)) != gd1_key
    assert make_key("gemini", "gemini-2.5-flash", prompt, cache_extra(1024, 0)) != gd1_key


def test_gd1_cache_hit_needs_no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    case = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][0]
    backend = GeminiBackend(ResponseCache(None, [GD1_CACHE]), model=PAPER_MODEL)
    response = backend.complete(compose_prompt(case["alert"], case["contexts"]), case["contexts"])
    assert response.cache_hit and response.error is None and json.loads(response.raw)["label"]


def test_cache_miss_without_key_is_manual_review(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    judge = LLMJudge(GeminiBackend(ResponseCache(tmp_path / "c.jsonl"), model=JUDGE_MODEL))
    judged = judge.evaluate(_candidate(), _context(_event("e1")))
    assert judged.verdict == "UNCERTAIN" and judged.debug["status"] == "manual_review"
    assert "GEMINI_API_KEY" in judged.debug["error"] and not judged.cache_hit


def test_cache_round_trip_and_repeat(tmp_path):
    path = tmp_path / "c.jsonl"
    cache = ResponseCache(path)
    cache.put("k", {"provider": "gemini", "model": "m", "raw": "{}", "usage": {}, "repeat": 1})
    entry = ResponseCache(path).get("k")
    assert entry is not None and entry["repeat"] == 1
    assert build_judge({"backend": "api", "cache_path": str(path), "repeat": 2}).repeat == 2


def test_registry_rejects_non_gemini_and_nonzero_temperature():
    with pytest.raises(ValueError):
        build_judge({"backend": "api", "model": "qwen2.5:1.5b"})
    with pytest.raises(ValueError):
        build_judge({"backend": "api", "temperature": 0.7})


# --- mock: GD1 verbatim -------------------------------------------------------------------


def test_mock_matches_gd1_mock():
    client = gd1("src.llm.judge_client").JudgeClient(provider="mock")
    for contexts in (
        [{"doc_id": "a", "severity": "ERROR", "message": "boom"}],
        [{"doc_id": "b", "severity": "INFO", "message": "Trace span x duration_ms=12.0"}],
        [{"doc_id": "c", "severity": "INFO", "event_type": "deployment", "message": "deployed"}],
        [{"doc_id": "d", "severity": "INFO", "message": "ok"}],
        [],
    ):
        assert MockBackend().complete("", contexts).raw == client._mock_response(contexts)


# --- decision rules -----------------------------------------------------------------------


def test_true_alert_with_evidence_is_kept():
    judged = LLMJudge(_Fixed(_answer("true_alert", 0.9, ["e1"]))).evaluate(_candidate(), _context(_event("e1")))
    assert (judged.verdict, judged.raw_verdict) == ("TRUE_ALERT", "TRUE_ALERT")
    assert judged.evidence_event_ids == ["e1"] and judged.evidence_origin == "local"
    assert judged.threshold_applied == 0.80 and judged.routing_tier == 1


def test_require_evidence_downgrades_true_alert_without_evidence():
    judged = LLMJudge(_Fixed(_answer("true_alert", 0.99, []))).evaluate(_candidate(), _context(_event("e1")))
    assert judged.verdict == "UNCERTAIN" and judged.raw_verdict == "TRUE_ALERT"
    assert judged.downgraded_by_evidence_rule
    lenient = LLMJudge(_Fixed(_answer("true_alert", 0.99, [])), require_evidence=False)
    assert lenient.evaluate(_candidate(), _context(_event("e1"))).verdict == "TRUE_ALERT"


def test_invented_evidence_ids_do_not_count():
    judge = LLMJudge(_Fixed(_answer("true_alert", 0.99, ["made-up"])))
    judged = judge.evaluate(_candidate(), _context(_event("e1")))
    assert judged.verdict == "UNCERTAIN" and judged.downgraded_by_evidence_rule
    assert judged.evidence_event_ids == [] and judged.debug["invalid_evidence_ids"] == ["made-up"]


def test_confidence_threshold_downgrades_only_true_alert():
    low_true = LLMJudge(_Fixed(_answer("true_alert", 0.79, ["e1"]))).evaluate(_candidate(), _context(_event("e1")))
    assert low_true.verdict == "UNCERTAIN" and low_true.debug["downgraded_by_threshold"]
    assert not low_true.downgraded_by_evidence_rule
    low_fp = LLMJudge(_Fixed(_answer("false_positive", 0.3))).evaluate(_candidate(), _context(_event("e1")))
    assert low_fp.verdict == "FALSE_POSITIVE"


def test_evidence_origin_mixed_and_graph():
    ctx = _context(_event("e1"), _event("g1", origin="graph"))
    mixed = LLMJudge(_Fixed(_answer("true_alert", 0.9, ["e1", "g1"]))).evaluate(_candidate(), ctx)
    graph = LLMJudge(_Fixed(_answer("true_alert", 0.9, ["g1"]))).evaluate(_candidate(), ctx)
    assert (mixed.evidence_origin, graph.evidence_origin) == ("mixed", "graph")


@pytest.mark.parametrize(
    ("answer", "error"),
    [("not json", None), ({"label": "maybe"}, None), (None, "HTTP 503: Service Unavailable")],
)
def test_unusable_answer_is_manual_review_never_true_alert(answer, error):
    judged = LLMJudge(_Fixed(answer, error)).evaluate(_candidate(), _context(_event("e1")))
    assert judged.verdict == judged.raw_verdict == "UNCERTAIN"
    assert judged.debug["status"] == "manual_review" and judged.debug["error"]
    assert not judged.debug["json_valid"]


def test_debug_records_prompt_inputs_and_backend():
    judged = LLMJudge(MockBackend()).evaluate(_candidate(), _context(_event("e1", severity="ERROR")))
    assert judged.judge_backend == "mock" and judged.verdict == "TRUE_ALERT"
    for key in ("retrieval_strategy", "repeat", "cache_key", "model_version", "json_valid", "raw_response"):
        assert key in judged.debug


def test_model_version_mismatch_stops_and_is_not_cached(monkeypatch, tmp_path):
    from services.judge import backends

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    body = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(_answer("uncertain"))}]}}],
        "usageMetadata": {},
        "modelVersion": "gemini-3.8-flash",
    }
    monkeypatch.setattr(backends, "_post_json_with_retry", lambda *args, **kwargs: (body, 0))
    cache = ResponseCache(tmp_path / "c.jsonl")
    backend = GeminiBackend(cache, model="gemini-3.7-flash")
    with pytest.raises(backends.ModelVersionMismatch):
        backend.complete("p", [])
    assert len(cache) == 0
    body["modelVersion"] = "gemini-3.7-flash"
    assert backend.complete("p", []).error is None and len(cache) == 1
