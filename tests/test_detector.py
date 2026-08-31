from __future__ import annotations

import unittest

from src.detectors.feature_pressure_detector import FeaturePressureDetector
from src.detectors.factory import build_detector
from src.detectors.isolation_forest_detector import IsolationForestDetector
from src.models import MetricWindow
from src.time_utils import parse_timestamp


class DetectorTests(unittest.TestCase):
    def test_detector_interface_returns_candidate_fields(self) -> None:
        window = MetricWindow(
            window_id="w1",
            start_time=parse_timestamp("2026-05-14T00:00:00Z"),
            end_time=parse_timestamp("2026-05-14T00:01:00Z"),
            node_id="n1",
            service_id="svc",
            features=[[0.0, 0.0], [3.0, 0.5]],
            feature_names=["cpu", "latency"],
            raw_features=[[10.0, 90.0], [95.0, 1300.0]],
        )
        result = FeaturePressureDetector(threshold=0.7).score(window)
        self.assertTrue(result.is_candidate)
        self.assertIn(result.top_features[0], {"cpu", "latency"})

    def test_isolation_forest_scores_unseen_outlier(self) -> None:
        windows = [
            MetricWindow(
                window_id=f"normal-{index}",
                start_time=parse_timestamp(f"2026-05-14T00:{index:02d}:00Z"),
                end_time=parse_timestamp(f"2026-05-14T00:{index:02d}:30Z"),
                node_id="n1",
                service_id="svc",
                features=[[0.0], [0.1]],
                feature_names=["cpu"],
                raw_features=[[10.0 + (index % 3)], [11.0 + (index % 3)]],
            )
            for index in range(20)
        ]
        outlier = MetricWindow(
            window_id="outlier",
            start_time=parse_timestamp("2026-05-14T00:30:00Z"),
            end_time=parse_timestamp("2026-05-14T00:30:30Z"),
            node_id="n1",
            service_id="svc",
            features=[[4.0], [5.0]],
            feature_names=["cpu"],
            raw_features=[[95.0], [99.0]],
        )
        detector = IsolationForestDetector(threshold=0.8, contamination=0.1, n_estimators=50, min_fit_windows=5)
        detector.fit(windows)
        result = detector.score(outlier)
        self.assertTrue(result.is_candidate)
        self.assertEqual(result.detector_label, "anomaly")
        self.assertIn("cpu", result.top_features)

    def test_detector_factory_selects_isolation_forest(self) -> None:
        windows = [
            MetricWindow(
                window_id=f"w-{index}",
                start_time=parse_timestamp(f"2026-05-14T00:{index:02d}:00Z"),
                end_time=parse_timestamp(f"2026-05-14T00:{index:02d}:30Z"),
                node_id="n1",
                service_id="svc",
                features=[[0.0]],
                feature_names=["cpu"],
                raw_features=[[10.0 + index]],
            )
            for index in range(10)
        ]
        detector = build_detector(
            {"name": "isolation_forest", "threshold": 0.95, "min_fit_windows": 5, "n_estimators": 10},
            windows,
        )
        self.assertIsInstance(detector, IsolationForestDetector)


if __name__ == "__main__":
    unittest.main()
