from __future__ import annotations

import json
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from src.llm.judge_client import JudgeClient
from src.llm.response_cache import ResponseCache, reset_global_cache_for_tests


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class LlmCacheAndProviderTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("LLM_RESPONSE_CACHE", None)
        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("GROQ_MODEL", None)
        reset_global_cache_for_tests()

    def test_response_cache_round_trip_reports_hit(self) -> None:
        path = Path(f"outputs/test_results/unit_cache_{uuid.uuid4().hex}.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        cache = ResponseCache(path)
        key = cache.make_key("groq", "model", "prompt")

        self.assertFalse(cache.get(key).hit)
        cache.put(key, "groq", "model", '{"label":"uncertain"}', {"prompt_tokens": 3})

        lookup = ResponseCache(path).get(key)
        self.assertTrue(lookup.hit)
        self.assertEqual(lookup.entry["usage"]["prompt_tokens"], 3)

    def test_groq_provider_parses_openai_compatible_response(self) -> None:
        os.environ["GROQ_API_KEY"] = "test-key"
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "label": "true_alert",
                                "severity": "P2",
                                "confidence": 0.91,
                                "evidence": ["trace-1"],
                                "reason": "trace confirms latency",
                                "recommended_action": "inspect dependency",
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 17},
        }

        with patch("src.llm.judge_client.request.urlopen", return_value=_FakeResponse(payload)):
            result = JudgeClient(provider="groq", model="llama-3.1-8b-instant").judge("prompt", [])

        self.assertTrue(result.valid_json)
        self.assertEqual(result.provider, "groq")
        self.assertEqual(result.prompt_tokens, 11)
        self.assertEqual(result.completion_tokens, 17)
        self.assertTrue(result.actual_api_call)
        self.assertFalse(result.cache_hit)

    def test_provider_cache_hit_avoids_network_call(self) -> None:
        os.environ["GROQ_API_KEY"] = "test-key"
        os.environ["LLM_RESPONSE_CACHE"] = f"outputs/test_results/provider_cache_{uuid.uuid4().hex}.jsonl"
        reset_global_cache_for_tests()
        path = Path(os.environ["LLM_RESPONSE_CACHE"])
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "label": "false_positive",
                                "severity": "none",
                                "confidence": 0.88,
                                "evidence": [],
                                "reason": "benign",
                                "recommended_action": "suppress",
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7},
        }
        with patch("src.llm.judge_client.request.urlopen", return_value=_FakeResponse(payload)) as mocked:
            first = JudgeClient(provider="groq", model="llama-3.1-8b-instant").judge("prompt", [])
            second = JudgeClient(provider="groq", model="llama-3.1-8b-instant").judge("prompt", [])

        self.assertEqual(mocked.call_count, 1)
        self.assertTrue(first.actual_api_call)
        self.assertFalse(first.cache_hit)
        self.assertFalse(second.actual_api_call)
        self.assertTrue(second.cache_hit)
        self.assertEqual(second.prompt_tokens, 5)


if __name__ == "__main__":
    unittest.main()
