from __future__ import annotations

import unittest

from src.retrieval.context_signal import evaluate_context_signal, trace_duration_ms


class ContextSignalTests(unittest.TestCase):
    def test_trace_duration_parser(self) -> None:
        self.assertEqual(trace_duration_ms("Trace span op duration_ms=101.25"), 101.25)
        self.assertEqual(trace_duration_ms("no duration"), 0.0)

    def test_context_signal_promotes_slow_trace(self) -> None:
        signal = evaluate_context_signal(
            [
                {
                    "doc_id": "trace-1",
                    "score": 0.81,
                    "event_type": "trace_span",
                    "severity": "INFO",
                    "message": "Trace span service/op duration_ms=2.5",
                }
            ],
            min_context_score=0.7,
            min_trace_duration_ms=1.0,
        )
        self.assertTrue(signal.should_promote)
        self.assertIn("trace-1", signal.matched_context_ids)

    def test_context_signal_ignores_weak_context(self) -> None:
        signal = evaluate_context_signal(
            [
                {
                    "doc_id": "trace-weak",
                    "score": 0.2,
                    "event_type": "trace_span",
                    "severity": "INFO",
                    "message": "Trace span service/op duration_ms=100.0",
                }
            ],
            min_context_score=0.7,
            min_trace_duration_ms=1.0,
        )
        self.assertFalse(signal.should_promote)


if __name__ == "__main__":
    unittest.main()
