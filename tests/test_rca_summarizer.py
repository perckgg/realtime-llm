"""services/rca_agent/summarizer.py: prompt, mock backend, validation rules of 03 SS2.1 (M9)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import networkx as nx
import pytest

from packages.graph.service_graph import ServiceGraph
from packages.schemas.models import ContextEvent, Incident, JudgedAlert
from services.judge.backends import BackendResponse
from services.judge.cache import ResponseCache
from services.rca_agent.propagation import backward_one_hop, propagation_path
from services.rca_agent.summarizer import (
    GeminiSummaryBackend,
    MockSummaryBackend,
    Summarizer,
    compose_prompt,
    looks_executable,
    prompt_fingerprint,
    validate_answer,
)

T0 = datetime(2022, 8, 22, 4, 0, tzinfo=UTC)


def _graph() -> ServiceGraph:
    directed = nx.DiGraph()
    directed.add_edge("frontend", "cart", weight=3)
    return ServiceGraph(directed)


def _alert(alert_id: str, service: str, evidence: list[str]) -> JudgedAlert:
    return JudgedAlert(
        alert_id=alert_id, candidate_id=alert_id, window_id=alert_id, service=service, ts=T0,
        verdict="TRUE_ALERT", raw_verdict="TRUE_ALERT", confidence=0.9, reasoning="slow spans",
        evidence_event_ids=evidence, judge_backend="mock", llm_latency_ms=0.0, cache_hit=True,
    )  # fmt: skip


def _event(event_id: str, service: str) -> ContextEvent:
    return ContextEvent(event_id=event_id, modality="trace", ts=T0 + timedelta(seconds=5), service=service,
                        content=f"Trace span GetCart on {service} duration_ms=900", score=1.0)  # fmt: skip


INCIDENT = Incident(
    incident_id="inc-1", run_id="run", alert_ids=["a", "b"], services=["cart", "frontend"],
    start_ts=T0, end_ts=T0 + timedelta(seconds=60), grouping_reason={"temporal_window_sec": 300},
)  # fmt: skip
ALERTS = [_alert("a", "frontend", ["e1"]), _alert("b", "cart", ["e2"])]
EVENTS = [_event("e2", "cart"), _event("e1", "frontend")]
RANKED = backward_one_hop(["frontend", "cart"], _graph(), {"cart": 0.8, "frontend": 0.6})
PATH = propagation_path(RANKED, _graph())


def _answer(**overrides: object) -> str:
    answer: dict[str, object] = {
        "fault_type": "network_delay",
        "confidence": 0.8,
        "evidence": ["e2"],
        "propagation_path": ["cart", "frontend"],
        "suggested_actions": [{"description": "Check the network latency of the cart pods.", "priority": "high"}],
    }
    answer.update(overrides)
    return json.dumps(answer)


def _validate(raw: str, require_evidence: bool = True, root: str = "cart"):  # type: ignore[no-untyped-def]
    return validate_answer(raw, INCIDENT, root, EVENTS, _graph(), "mock", require_evidence, generated_at=T0)


class _Fixed:
    name = "fixed"

    def __init__(self, raw: str = "", error: str | None = None) -> None:
        self.raw, self.error, self.calls = raw, error, 0

    def complete(self, prompt: str) -> BackendResponse:
        self.calls += 1
        return BackendResponse(raw=self.raw, error=self.error)


def test_prompt_has_no_ground_truth_and_lists_allowed_ids() -> None:
    prompt = json.loads(compose_prompt(INCIDENT, ALERTS, RANKED, PATH, EVENTS, [("frontend", "cart")]))
    assert prompt["incident"]["root_cause_service"] == "cart"
    assert prompt["allowed_evidence_ids"] == ["e2", "e1"]
    assert prompt["incident"]["call_edges"] == ["frontend -> cart"]
    assert "label" not in json.dumps(prompt).lower()
    assert len(prompt_fingerprint()) == 16


def test_mock_backend_gives_a_published_report() -> None:
    result = Summarizer(MockSummaryBackend(), _graph()).summarize(INCIDENT, ALERTS, RANKED, PATH, EVENTS)
    assert result.valid and result.llm_called and result.reject_reason is None
    report = result.report
    assert report is not None
    assert (report.incident_id, report.run_id, report.root_cause_service) == ("inc-1", "run", "cart")
    assert [e.event_id for e in report.evidence] == ["e2", "e1"]
    assert report.evidence[0].excerpt.startswith("Trace span GetCart")
    assert report.llm_backend == "mock" and report.schema_version == "1.0"


def test_valid_answer_fills_evidence_from_the_context() -> None:
    report, reason, suspicious, invalid = _validate(_answer(evidence=["e2", "made-up", "e2"]))
    assert reason is None and report is not None and not suspicious
    assert [e.event_id for e in report.evidence] == ["e2"]  # made-up id dropped, duplicate removed
    assert invalid == ["made-up"]
    assert report.evidence[0].service == "cart" and report.generated_at == T0


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("not json at all", "invalid_json"),
        ("[1, 2]", "invalid_json"),
        (json.dumps({"fault_type": "exception"}), "invalid_json"),  # missing fields
        (_answer(confidence=1.5), "confidence_out_of_range"),
        (_answer(confidence=-0.1), "confidence_out_of_range"),
        (_answer(evidence=[]), "no_evidence"),
        (_answer(evidence=["made-up"]), "no_evidence"),
        (_answer(suggested_actions=[{"description": "kubectl rollout restart deploy/cart", "priority": "high"}]),
         "executable_action"),
        (_answer(suggested_actions=[{"description": "Run `sudo systemctl restart cart` on the node", "priority": "low"}]),
         "executable_action"),
        (_answer(suggested_actions=[{"description": "do it", "priority": "urgent"}]), "invalid_json"),
    ],
)  # fmt: skip
def test_rejections(raw: str, reason: str) -> None:
    report, why, _, _ = _validate(raw)
    assert report is None and why is not None and why.startswith(reason)


def test_require_evidence_off_still_publishes_with_the_first_event() -> None:
    report, reason, _, _ = _validate(_answer(evidence=[]), require_evidence=False)
    assert reason is None and report is not None and [e.event_id for e in report.evidence] == ["e2"]


def test_root_cause_outside_the_graph_is_published_but_suspicious() -> None:
    report, reason, suspicious, _ = _validate(_answer(), root="ghost")
    assert report is not None and reason is None and suspicious


def test_unknown_fault_type_is_mapped_to_unknown_and_fenced_json_is_read() -> None:
    report, reason, _, _ = _validate("```json\n" + _answer(fault_type="disk_full") + "\n```")
    assert reason is None and report is not None and report.fault_type == "unknown"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("kubectl get pods -n prod", True),
        ("$ docker restart cart", True),
        ("sudo rm -rf /tmp/cache", True),
        ("Restart it: `systemctl restart cart`", True),
        ("check logs && restart", True),
        ("Inspect the network latency between frontend and cart.", False),
        ("Make sure the cart service has enough CPU; consider scaling it.", False),
        ("Review docker image versions deployed for cart.", False),
        ("Kill switch for the feature flag should be reviewed.", False),
    ],
)
def test_looks_executable(text: str, expected: bool) -> None:
    assert looks_executable(text) is expected


def test_no_evidence_means_no_llm_call() -> None:
    backend = _Fixed(_answer())
    result = Summarizer(backend, _graph()).summarize(INCIDENT, ALERTS, RANKED, PATH, [])
    assert not result.valid and not result.llm_called and backend.calls == 0
    assert (result.reject_reason or "").startswith("no_evidence")


def test_llm_error_is_rejected_not_swallowed() -> None:
    result = Summarizer(_Fixed(error="HTTP 503"), _graph()).summarize(INCIDENT, ALERTS, RANKED, PATH, EVENTS)
    assert not result.valid and result.llm_called and (result.reject_reason or "").startswith("llm_error")


def test_max_evidence_limits_what_can_be_cited() -> None:
    result = Summarizer(_Fixed(_answer(evidence=["e1"])), _graph(), max_evidence=1).summarize(
        INCIDENT, ALERTS, RANKED, PATH, EVENTS
    )
    assert not result.valid and result.invalid_evidence_ids == ["e1"]  # e1 was not shown


def test_gemini_backend_reads_the_cache_without_a_key(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path / "cache.jsonl")
    backend = GeminiSummaryBackend(cache, "gemini-2.5-flash", 512, api_key=None)
    prompt = compose_prompt(INCIDENT, ALERTS, RANKED, PATH, EVENTS, [])
    cache.put(backend.cache_key(prompt), {"raw": _answer(), "usage": {"promptTokenCount": 10}, "model_version": "gemini-2.5-flash"})
    hit = backend.complete(prompt)
    assert hit.cache_hit and not hit.actual_api_call and json.loads(hit.raw)["fault_type"] == "network_delay"
    assert backend.cache_key(prompt) != GeminiSummaryBackend(cache, "gemini-2.5-flash", 1024).cache_key(prompt)
