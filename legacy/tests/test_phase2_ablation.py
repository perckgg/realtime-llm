from __future__ import annotations

import unittest

from scripts.phase2.run_alpha_beta_gamma_ablation import ABLATION_SETTINGS, select_confirmation_settings


class Phase2AblationTest(unittest.TestCase):
    def test_ablation_settings_match_contract(self) -> None:
        settings = {setting.setting: setting for setting in ABLATION_SETTINGS}
        self.assertEqual(set(settings), {
            "A0_bm25_only",
            "A1_bm25_time",
            "A2_bm25_graph",
            "A3_balanced",
            "A4_topology_heavy",
        })
        self.assertEqual((settings["A0_bm25_only"].weights.alpha, settings["A0_bm25_only"].weights.beta, settings["A0_bm25_only"].weights.gamma), (1.0, 0.0, 0.0))
        self.assertEqual((settings["A1_bm25_time"].weights.alpha, settings["A1_bm25_time"].weights.beta, settings["A1_bm25_time"].weights.gamma), (0.5, 0.5, 0.0))
        self.assertEqual((settings["A2_bm25_graph"].weights.alpha, settings["A2_bm25_graph"].weights.beta, settings["A2_bm25_graph"].weights.gamma), (0.5, 0.0, 0.5))
        self.assertEqual((settings["A3_balanced"].weights.alpha, settings["A3_balanced"].weights.beta, settings["A3_balanced"].weights.gamma), (0.4, 0.3, 0.3))
        self.assertEqual((settings["A4_topology_heavy"].weights.alpha, settings["A4_topology_heavy"].weights.beta, settings["A4_topology_heavy"].weights.gamma), (0.35, 0.25, 0.4))

    def test_selection_uses_tuning_graph_enabled_rows_only(self) -> None:
        rows = [
            {
                "phase": "tuning",
                "setting": "A0_bm25_only",
                "gamma": 0.0,
                "positive_service_context_coverage": 1.0,
                "network_delay_service_context_coverage": 1.0,
                "topology_expanded_context_ratio": 0.0,
                "avg_retrieval_latency_ms": 1.0,
            },
            {
                "phase": "confirmation",
                "setting": "A2_bm25_graph",
                "gamma": 0.5,
                "positive_service_context_coverage": 9.0,
                "network_delay_service_context_coverage": 9.0,
                "topology_expanded_context_ratio": 9.0,
                "avg_retrieval_latency_ms": 0.1,
            },
            {
                "phase": "tuning",
                "setting": "A3_balanced",
                "gamma": 0.3,
                "positive_service_context_coverage": 1.0,
                "network_delay_service_context_coverage": 1.0,
                "topology_expanded_context_ratio": 0.5,
                "avg_retrieval_latency_ms": 10.0,
            },
            {
                "phase": "tuning",
                "setting": "A4_topology_heavy",
                "gamma": 0.4,
                "positive_service_context_coverage": 1.0,
                "network_delay_service_context_coverage": 1.0,
                "topology_expanded_context_ratio": 0.6,
                "avg_retrieval_latency_ms": 20.0,
            },
        ]

        self.assertEqual(select_confirmation_settings(rows, 2), ["A4_topology_heavy", "A3_balanced"])


if __name__ == "__main__":
    unittest.main()
