"""M1: every GD2 implementation satisfies its 01 SS5 Protocol, and the new
models carry the CTAV fields of 03 SS1.3-1.4 with their defaults."""

from __future__ import annotations

from datetime import UTC, datetime

from packages.schemas.evidence import InMemoryEvidenceStore
from packages.schemas.models import JudgedAlert, RetrievalBudget
from packages.schemas.protocols import Detector, Judge, RetrievalStrategy, SourceAdapter
from services.detector.isolation_forest import IsolationForestDetector
from services.judge.backends import MockBackend
from services.judge.llm_judge import LLMJudge
from services.replayer.nezha_source import NezhaReplaySource
from services.retrieval.bm25_hybrid import Bm25HybridRetriever


def test_implementations_satisfy_protocols():
    assert isinstance(NezhaReplaySource(window_ids=set()), SourceAdapter)
    assert isinstance(IsolationForestDetector(), Detector)
    assert isinstance(Bm25HybridRetriever(InMemoryEvidenceStore([])), RetrievalStrategy)
    assert isinstance(LLMJudge(MockBackend()), Judge)


def test_retrieval_budget_defaults():
    assert RetrievalBudget() == RetrievalBudget(top_k=6, max_tokens=4000, timeout_ms=500)


def test_judged_alert_ctav_defaults():
    alert = JudgedAlert(
        alert_id="a",
        candidate_id="c",
        window_id="w",
        service="s",
        ts=datetime(2022, 8, 22, tzinfo=UTC),
        verdict="UNCERTAIN",
        raw_verdict="TRUE_ALERT",
        confidence=0.5,
        reasoning="",
        evidence_event_ids=[],
        judge_backend="mock",
        llm_latency_ms=0.0,
        cache_hit=False,
    )
    assert alert.routing_tier == 1
    assert alert.evidence_origin == "none"
    assert alert.threshold_applied is None
    assert not (alert.downgraded_by_gating or alert.downgraded_by_anchoring or alert.downgraded_by_evidence_rule)
