from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.llm.judge_client import JudgeClient, JudgeResult
from src.llm.local_first_judge import LocalFirstJudgeClient
from src.llm.schema import validate_judge_json
from src.models import AlertCandidate


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _StaticClient:
    def __init__(self, result: JudgeResult) -> None:
        self.result = result
        self.calls = 0
        self.provider = result.provider
        self.model = result.model

    def judge(self, *_: object, **__: object) -> JudgeResult:
        self.calls += 1
        return self.result


class OllamaJudgeTests(unittest.TestCase):
    def test_ollama_provider_parses_json_response_and_usage(self) -> None:
        payload = {
            "response": json.dumps(
                {
                    "label": "true_alert",
                    "severity": "P2",
                    "confidence": 0.91,
                    "evidence": ["trace-1"],
                    "reason": "trace confirms latency",
                    "recommended_action": "inspect dependency",
                }
            ),
            "prompt_eval_count": 42,
            "eval_count": 18,
        }
        with patch("src.llm.judge_client.request.urlopen", return_value=_FakeResponse(payload)):
            result = JudgeClient(provider="ollama", model="qwen2.5:1.5b").judge("prompt", [])
        self.assertTrue(result.valid_json)
        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.model, "qwen2.5:1.5b")
        self.assertEqual(result.prompt_tokens, 42)
        self.assertEqual(result.completion_tokens, 18)
        self.assertEqual(result.token_source, "ollama_usage_metadata")

    def test_schema_accepts_markdown_wrapped_json_from_local_model(self) -> None:
        decision = validate_judge_json(
            '```json\n{"label":"false_positive","severity":"none","confidence":0.88,"evidence":[],"reason":"benign","recommended_action":"suppress"}\n```'
        )
        self.assertEqual(decision.label, "false_positive")

    def test_local_first_uses_local_when_confident(self) -> None:
        local = _StaticClient(
            JudgeResult(
                decision=validate_judge_json(
                    '{"label":"true_alert","severity":"P2","confidence":0.92,"evidence":[],"reason":"x","recommended_action":"x"}'
                ),
                raw_response="{}",
                prompt_tokens=1,
                completion_tokens=1,
                latency_ms=1.0,
                valid_json=True,
                provider="ollama",
                model="qwen2.5:1.5b",
            )
        )
        fallback = _StaticClient(_fallback_result())
        result = LocalFirstJudgeClient(local, fallback, confidence_threshold=0.8).judge("prompt", [], alert=_alert(0.8))
        self.assertFalse(result.api_fallback_used)
        self.assertEqual(local.calls, 1)
        self.assertEqual(fallback.calls, 0)

    def test_local_first_falls_back_on_uncertain(self) -> None:
        local = _StaticClient(
            JudgeResult(
                decision=validate_judge_json(
                    '{"label":"uncertain","severity":"P3","confidence":0.7,"evidence":[],"reason":"weak","recommended_action":"review"}'
                ),
                raw_response="{}",
                prompt_tokens=1,
                completion_tokens=1,
                latency_ms=1.0,
                valid_json=True,
                provider="ollama",
                model="qwen2.5:1.5b",
            )
        )
        fallback = _StaticClient(_fallback_result())
        result = LocalFirstJudgeClient(local, fallback, confidence_threshold=0.8).judge("prompt", [], alert=_alert(0.8))
        self.assertTrue(result.api_fallback_used)
        self.assertEqual(result.api_fallback_reason, "local_uncertain")
        self.assertTrue(result.model_fallback_used)
        self.assertEqual(result.model_fallback_reason, "local_uncertain")
        self.assertEqual(fallback.calls, 1)

    def test_local_first_falls_back_on_high_anomaly_score(self) -> None:
        local = _StaticClient(
            JudgeResult(
                decision=validate_judge_json(
                    '{"label":"true_alert","severity":"P2","confidence":0.95,"evidence":[],"reason":"x","recommended_action":"x"}'
                ),
                raw_response="{}",
                prompt_tokens=1,
                completion_tokens=1,
                latency_ms=1.0,
                valid_json=True,
                provider="ollama",
                model="qwen2.5:1.5b",
            )
        )
        fallback = _StaticClient(_fallback_result())
        result = LocalFirstJudgeClient(local, fallback, high_anomaly_fallback_threshold=0.98).judge(
            "prompt",
            [],
            alert=_alert(0.99),
        )
        self.assertTrue(result.api_fallback_used)
        self.assertEqual(result.api_fallback_reason, "high_anomaly_score")
        self.assertTrue(result.model_fallback_used)
        self.assertEqual(result.primary_local_model, "ollama:qwen2.5:1.5b")
        self.assertEqual(result.fallback_model, "gemini:gemini-2.5-flash")

    def test_local_first_can_block_api_fallback_for_scheduler(self) -> None:
        local = _StaticClient(
            JudgeResult(
                decision=validate_judge_json(
                    '{"label":"uncertain","severity":"P3","confidence":0.4,"evidence":[],"reason":"weak","recommended_action":"review"}'
                ),
                raw_response="{}",
                prompt_tokens=1,
                completion_tokens=1,
                latency_ms=1.0,
                valid_json=True,
                provider="ollama",
                model="qwen2.5:1.5b",
            )
        )
        fallback = _StaticClient(_fallback_result())
        result = LocalFirstJudgeClient(local, fallback, confidence_threshold=0.8).judge(
            "prompt",
            [],
            alert=_alert(0.8),
            allow_api_fallback=False,
        )

        self.assertFalse(result.api_fallback_used)
        self.assertEqual(result.api_fallback_reason, "api_fallback_blocked:local_uncertain")
        self.assertFalse(result.model_fallback_used)
        self.assertEqual(result.model_fallback_reason, "fallback_blocked:local_uncertain")
        self.assertEqual(local.calls, 1)
        self.assertEqual(fallback.calls, 0)


def _fallback_result() -> JudgeResult:
    return JudgeResult(
        decision=validate_judge_json(
            '{"label":"true_alert","severity":"P2","confidence":0.9,"evidence":[],"reason":"api","recommended_action":"route"}'
        ),
        raw_response="{}",
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=1.0,
        valid_json=True,
        provider="gemini",
        model="gemini-2.5-flash",
    )


def _alert(score: float) -> AlertCandidate:
    return AlertCandidate(
        alert_id="a1",
        window_id="w1",
        time_window={"start": "2026-05-14T00:00:00Z", "end": "2026-05-14T00:01:00Z"},
        node_id="n1",
        service_id="svc",
        anomaly_score=score,
        metric_snapshot={},
        detector_label="anomaly",
        top_features=[],
    )


if __name__ == "__main__":
    unittest.main()
