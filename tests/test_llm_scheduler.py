from __future__ import annotations

import unittest

from src.llm.scheduler import LLMRequestScheduler
from src.models import AlertCandidate


class LLMRequestSchedulerTests(unittest.TestCase):
    def test_high_priority_alert_is_allowed_to_call_api(self) -> None:
        scheduler = LLMRequestScheduler({"enabled": True, "high_priority_threshold": 0.95})
        decision = scheduler.plan(_alert(0.99), provider="local_first")

        self.assertEqual(decision.action, "call")
        self.assertEqual(decision.reason, "high_priority")
        self.assertFalse(decision.api_deferred)

    def test_low_priority_local_first_uses_local_only(self) -> None:
        scheduler = LLMRequestScheduler(
            {
                "enabled": True,
                "defer_below_priority": 0.8,
                "low_priority_action": "local_only",
            }
        )
        decision = scheduler.plan(_alert(0.4), provider="local_first")

        self.assertEqual(decision.action, "local_only")
        self.assertEqual(decision.reason, "below_defer_priority")
        self.assertTrue(decision.api_deferred)

    def test_cooldown_defers_non_local_first_provider(self) -> None:
        scheduler = LLMRequestScheduler({"enabled": True, "cooldown_on_429_seconds": 60})
        scheduler.record_result("HTTP Error 429: Too Many Requests", actual_api_call=True)

        decision = scheduler.plan(_alert(0.7), provider="gemini")

        self.assertEqual(decision.action, "defer")
        self.assertEqual(decision.reason, "api_cooldown_active")
        self.assertGreater(decision.delay_seconds, 0)


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
