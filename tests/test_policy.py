from __future__ import annotations

import unittest

from src.decision.policy import build_alert_candidate, decide_llm_budget_exhausted
from src.models import DetectorResult, MetricWindow
from src.time_utils import parse_timestamp


class PolicyTests(unittest.TestCase):
    def test_alert_id_is_stable_for_same_window_and_score(self) -> None:
        window = MetricWindow(
            window_id="node-a-service-a-2022-01-01T00:00:00Z-2022-01-01T00:02:00Z",
            start_time=parse_timestamp("2022-01-01T00:00:00Z"),
            end_time=parse_timestamp("2022-01-01T00:02:00Z"),
            node_id="node-a",
            service_id="service-a",
            features=[[0.0], [1.0]],
            feature_names=["latency"],
        )
        result = DetectorResult(
            window_id=window.window_id,
            is_candidate=True,
            anomaly_score=0.999,
            detector_label="isolation_forest",
            top_features=["latency"],
        )

        first = build_alert_candidate(window, result)
        second = build_alert_candidate(window, result)

        self.assertEqual(first.alert_id, second.alert_id)
        self.assertTrue(first.alert_id.startswith("alert-"))

    def test_llm_budget_exhausted_defaults_to_manual_review(self) -> None:
        self.assertEqual(
            decide_llm_budget_exhausted({}),
            ("manual_review", "llm_budget_exhausted"),
        )

    def test_llm_budget_exhausted_action_can_be_configured(self) -> None:
        self.assertEqual(
            decide_llm_budget_exhausted({"llm_budget_exhausted_action": "route_alert"}),
            ("route_alert", "llm_budget_exhausted"),
        )


if __name__ == "__main__":
    unittest.main()
