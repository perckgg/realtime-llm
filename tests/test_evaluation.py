from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.evaluation.metrics import summarize
from src.evaluation.report import write_result


class EvaluationTests(unittest.TestCase):
    def test_summary_includes_retrieval_context_metrics(self) -> None:
        records = [
            {
                "ground_truth": "true_alert",
                "final_decision": "route_alert",
                "is_candidate": True,
                "llm_called": True,
                "llm_call_avoided": False,
                "retrieved_context_count": 2,
                "retrieval_attempted": True,
                "context_token_count": 14,
                "prompt_token_count": 100,
                "completion_token_count": 20,
                "context_rescue_checked": True,
                "context_rescue_promoted": True,
                "api_fallback_used": True,
                "local_result_valid_json": False,
                "model_fallback_used": True,
                "primary_local_model": "ollama:llama3.2:3b",
                "fallback_model": "ollama:qwen2.5:3b",
                "llm_provider": "gemini",
                "llm_cache_hit": True,
                "actual_api_call": False,
                "llm_retry_count": 2,
                "llm_backoff_sleep_ms": 1250.5,
                "scheduler_action": "local_only",
                "priority_score": 0.72,
                "api_deferred": True,
            },
            {
                "ground_truth": "normal",
                "final_decision": "suppress",
                "is_candidate": True,
                "llm_called": True,
                "llm_call_avoided": False,
                "retrieved_context_count": 0,
                "retrieval_attempted": True,
                "context_token_count": 0,
                "prompt_token_count": 80,
                "completion_token_count": 10,
                "scheduler_action": "defer",
                "priority_score": 0.4,
                "api_deferred": True,
            },
        ]
        summary = summarize(records)
        self.assertEqual(summary["context_tokens"], 14)
        self.assertEqual(summary["avg_retrieved_context_count"], 1.0)
        self.assertEqual(summary["context_coverage_rate"], 0.5)
        self.assertEqual(summary["retrieval_attempts"], 2)
        self.assertEqual(summary["retrieval_successes"], 1)
        self.assertEqual(summary["retrieval_attempt_coverage_rate"], 0.5)
        self.assertEqual(summary["manual_reviews"], 0)
        self.assertEqual(summary["automation_coverage"], 1.0)
        self.assertEqual(summary["selective_f1"], 1.0)
        self.assertEqual(summary["llm_conditional_f1"], 1.0)
        self.assertEqual(summary["context_rescue_checked"], 1)
        self.assertEqual(summary["context_rescue_promoted"], 1)
        self.assertEqual(summary["api_fallback_calls"], 1)
        self.assertEqual(summary["model_fallback_calls"], 1)
        self.assertEqual(summary["primary_local_models"], ["ollama:llama3.2:3b"])
        self.assertEqual(summary["fallback_models"], ["ollama:qwen2.5:3b"])
        self.assertEqual(summary["llm_providers"], ["gemini"])
        self.assertEqual(summary["llm_cache_hits"], 1)
        self.assertEqual(summary["actual_api_calls"], 0)
        self.assertEqual(summary["llm_retry_count"], 2)
        self.assertEqual(summary["llm_backoff_sleep_ms"], 1250.5)
        self.assertEqual(summary["cache_hit_rate"], 0.5)
        self.assertEqual(summary["scheduler_deferred"], 1)
        self.assertEqual(summary["scheduler_local_only"], 1)
        self.assertEqual(summary["api_deferred"], 2)
        self.assertEqual(summary["avg_priority_score"], 0.56)

    def test_summary_treats_manual_review_as_abstention_for_selective_metrics(self) -> None:
        records = [
            {
                "ground_truth": "true_alert",
                "final_decision": "route_alert",
                "is_candidate": True,
                "llm_called": True,
                "retrieval_attempted": True,
                "retrieved_context_count": 1,
            },
            {
                "ground_truth": "true_alert",
                "final_decision": "manual_review",
                "is_candidate": True,
                "llm_called": False,
                "gate_action": "llm_budget_exhausted",
                "retrieval_attempted": False,
                "retrieved_context_count": 0,
            },
            {
                "ground_truth": "normal",
                "final_decision": "suppress",
                "is_candidate": False,
                "llm_called": False,
                "retrieval_attempted": False,
                "retrieved_context_count": 0,
            },
        ]

        summary = summarize(records)

        self.assertEqual(summary["recall"], 0.5)
        self.assertEqual(summary["manual_reviews"], 1)
        self.assertEqual(summary["manual_review_rate"], 0.3333)
        self.assertEqual(summary["automation_coverage"], 0.6667)
        self.assertEqual(summary["selective_recall"], 1.0)
        self.assertEqual(summary["llm_conditional_recall"], 1.0)

    def test_write_result_adds_configured_llm_cost_estimate(self) -> None:
        records = [
            {
                "ground_truth": "true_alert",
                "final_decision": "route_alert",
                "is_candidate": True,
                "llm_called": True,
                "llm_call_avoided": False,
                "retrieved_context_count": 1,
                "context_token_count": 10,
                "prompt_token_count": 1000,
                "completion_token_count": 500,
            }
        ]
        config = {
            "llm": {
                "input_cost_per_1m_tokens": 1.0,
                "output_cost_per_1m_tokens": 2.0,
                "cost_pricing_source": "unit_test",
            }
        }
        output_dir = Path("outputs/test_results")
        path = write_result("unit_test_eval", records, str(output_dir), config=config)
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["llm_cost_pricing_source"], "unit_test")
        self.assertEqual(payload["summary"]["estimated_llm_cost_usd"], 0.002)


if __name__ == "__main__":
    unittest.main()
