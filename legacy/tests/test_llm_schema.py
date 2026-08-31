from __future__ import annotations

import json
import unittest

from src.decision.policy import decide
from src.llm.judge_client import JudgeResult
from src.llm.schema import validate_judge_json
from src.models import AlertCandidate


class LLMSchemaTests(unittest.TestCase):
    def test_llm_json_validation_accepts_schema(self) -> None:
        decision = validate_judge_json(
            json.dumps(
                {
                    "label": "true_alert",
                    "severity": "P2",
                    "confidence": 0.9,
                    "evidence": ["log-1"],
                    "reason": "matched error",
                    "recommended_action": "investigate",
                }
            )
        )
        self.assertEqual(decision.label, "true_alert")

    def test_llm_json_validation_rejects_bad_label(self) -> None:
        with self.assertRaises(Exception):
            validate_judge_json(
                json.dumps(
                    {
                        "label": "bad",
                        "severity": "P2",
                        "confidence": 0.9,
                        "evidence": [],
                        "reason": "x",
                        "recommended_action": "x",
                    }
                )
            )

    def test_fallback_behavior_on_invalid_json(self) -> None:
        alert = AlertCandidate(
            alert_id="a1",
            window_id="w1",
            time_window={"start": "2026-05-14T00:00:00Z", "end": "2026-05-14T00:01:00Z"},
            node_id="n1",
            service_id="svc",
            anomaly_score=0.8,
            metric_snapshot={},
            detector_label="anomaly",
            top_features=[],
        )
        judge = JudgeResult(None, "bad", 1, 1, 1.0, False, "parse error")
        final_decision, fallback = decide(alert, judge, 0.8)
        self.assertEqual(final_decision, "route_alert")
        self.assertEqual(fallback, "fallback")

    def test_true_alert_without_evidence_can_be_sent_to_manual_review(self) -> None:
        alert = AlertCandidate(
            alert_id="a1",
            window_id="w1",
            time_window={"start": "2026-05-14T00:00:00Z", "end": "2026-05-14T00:01:00Z"},
            node_id="n1",
            service_id="svc",
            anomaly_score=0.99,
            metric_snapshot={},
            detector_label="anomaly",
            top_features=[],
        )
        judge = JudgeResult(
            validate_judge_json(
                '{"label":"true_alert","severity":"P1","confidence":0.99,"evidence":[],"reason":"x","recommended_action":"x"}'
            ),
            "{}",
            1,
            1,
            1.0,
            True,
        )
        final_decision, fallback = decide(alert, judge, 0.8, require_evidence_for_true_alert=True)
        self.assertEqual(final_decision, "manual_review")
        self.assertEqual(fallback, "llm_valid_missing_evidence")

    def test_failed_api_fallback_does_not_suppress_high_anomaly_local_false_positive(self) -> None:
        alert = AlertCandidate(
            alert_id="a1",
            window_id="w1",
            time_window={"start": "2026-05-14T00:00:00Z", "end": "2026-05-14T00:01:00Z"},
            node_id="n1",
            service_id="svc",
            anomaly_score=0.99,
            metric_snapshot={},
            detector_label="anomaly",
            top_features=[],
        )
        judge = JudgeResult(
            validate_judge_json(
                '{"label":"false_positive","severity":"none","confidence":0.0,"evidence":[],"reason":"x","recommended_action":"x"}'
            ),
            "{}",
            1,
            1,
            1.0,
            True,
            api_fallback_used=True,
            api_fallback_reason="high_anomaly_score",
            api_fallback_error="HTTP Error 429: Too Many Requests",
        )
        final_decision, fallback = decide(alert, judge, 0.8)
        self.assertEqual(final_decision, "manual_review")
        self.assertEqual(fallback, "api_fallback_failed_manual_review")


if __name__ == "__main__":
    unittest.main()
