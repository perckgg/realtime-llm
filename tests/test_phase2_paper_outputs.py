from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.phase2.generate_paper_outputs import (
    audit_context_coverage_by_fault,
    build_ablation_rows,
)


class Phase2PaperOutputsTest(unittest.TestCase):
    def test_ablation_rows_do_not_invent_decision_metrics(self) -> None:
        rows = build_ablation_rows(
            [
                {
                    "phase": "tuning",
                    "split": "paper_300",
                    "setting": "A3_balanced",
                    "setting_description": "Balanced",
                    "alpha": "0.4",
                    "beta": "0.3",
                    "gamma": "0.3",
                    "service_context_coverage": "0.75",
                    "avg_retrieval_latency_ms": "12.5",
                    "network_delay_service_context_coverage": "1.0",
                    "topology_expanded_context_ratio": "0.2",
                }
            ]
        )

        self.assertEqual(rows[0]["evaluation_level"], "retrieval_only")
        self.assertEqual(rows[0]["precision"], "")
        self.assertEqual(rows[0]["f1"], "")
        self.assertEqual(rows[0]["coverage"], "0.75")
        self.assertEqual(
            rows[0]["network_delay_recall_type"],
            "retrieval service-context recall",
        )

    def test_fault_coverage_uses_retrieval_attempts_as_denominator(self) -> None:
        records = [
            {
                "fault_type": "network_delay",
                "retrieval_attempted": True,
                "context_coverage": True,
            },
            {
                "fault_type": "network_delay",
                "retrieval_attempted": True,
                "context_coverage": False,
            },
            {
                "fault_type": "network_delay",
                "retrieval_attempted": False,
                "context_coverage": False,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            coverage = audit_context_coverage_by_fault(path)

        self.assertEqual(coverage["network_delay"]["attempts"], 2)
        self.assertEqual(coverage["network_delay"]["covered"], 1)
        self.assertEqual(coverage["network_delay"]["coverage"], 0.5)

    def test_legacy_audit_infers_attempts_from_candidate_rows(self) -> None:
        records = [
            {
                "fault_type": "none",
                "is_candidate": True,
                "retrieved_context_count": 1,
                "retrieval_latency_ms": 4.0,
            },
            {
                "fault_type": "none",
                "is_candidate": True,
                "retrieved_context_count": 0,
                "retrieval_latency_ms": 3.0,
            },
            {
                "fault_type": "none",
                "is_candidate": False,
                "retrieved_context_count": 0,
                "retrieval_latency_ms": 0.0,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy_audit.jsonl"
            path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            coverage = audit_context_coverage_by_fault(path)

        self.assertEqual(coverage["none"]["attempts"], 2)
        self.assertEqual(coverage["none"]["coverage"], 0.5)


if __name__ == "__main__":
    unittest.main()
