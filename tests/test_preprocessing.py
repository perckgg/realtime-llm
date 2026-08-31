from __future__ import annotations

import unittest

from src.ingestion.metric_loader import load_metrics
from src.preprocessing.metric_preprocessing import create_metric_windows, normalize


class PreprocessingTests(unittest.TestCase):
    def test_normalization_zscore_centers_columns(self) -> None:
        matrix = normalize([[1, 2], [2, 4], [3, 6]], "zscore")
        self.assertEqual(round(sum(row[0] for row in matrix), 6), 0)

    def test_sliding_window_creation(self) -> None:
        records = load_metrics("data/sample/metrics.csv")
        windows = create_metric_windows(records, 60, 30, "zscore")
        self.assertTrue(windows)
        self.assertTrue({"cpu", "memory", "latency"}.issubset(set(windows[0].feature_names)))


if __name__ == "__main__":
    unittest.main()
