from __future__ import annotations

import unittest

from scripts.phase2.run_step9_quality_gate import close, score_values


class Phase2QualityGateTest(unittest.TestCase):
    def test_score_values_extracts_scalar_and_list_scores(self) -> None:
        record = {
            "score_final": [0.1, 0.9],
            "contexts": [
                {"score_final": 0.5},
                {"nested": {"score_final": 1.0}},
            ],
            "unrelated": [10, 20],
        }
        self.assertEqual(list(score_values(record)), [0.1, 0.9, 0.5, 1.0])

    def test_close_compares_numeric_csv_values(self) -> None:
        self.assertTrue(close("0.703", "0.7030"))
        self.assertFalse(close("0.703", "0.704"))


if __name__ == "__main__":
    unittest.main()
