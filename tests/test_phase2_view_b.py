from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from scripts.phase2.run_step7_view_b import activate_cache, view_b_config


class Phase2ViewBTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base_config = {
            "experiment": {},
            "evaluation": {},
            "llm_gate": {},
            "llm": {},
            "decision": {},
            "retrieval": {},
        }
        self.args = argparse.Namespace(
            max_total_calls=120,
            max_llm_calls_per_minute=15,
            provider="gemini",
            model="gemini-2.5-flash-lite",
            max_output_tokens=1024,
            timeout_seconds=60.0,
            max_retries=5,
            input_cost_per_1m_tokens=0.10,
            output_cost_per_1m_tokens=0.40,
            cost_pricing_source="test",
        )

    def test_llm_without_rag_does_not_require_evidence(self) -> None:
        config, mode = view_b_config(
            self.base_config,
            "llm_without_rag",
            Path("results"),
            Path("audit"),
            self.args,
            "fresh",
        )
        self.assertEqual(mode, "llm_without_rag")
        self.assertFalse(config["decision"]["require_evidence_for_true_alert"])
        self.assertFalse(config["candidate_rescue"]["enabled"])

    def test_context_rescue_is_bm25_architecture_variant(self) -> None:
        config, mode = view_b_config(
            self.base_config,
            "context_rescue",
            Path("results"),
            Path("audit"),
            self.args,
            "seeded_from_view_a_bm25",
        )
        self.assertEqual(mode, "hybrid")
        self.assertTrue(config["candidate_rescue"]["enabled"])
        self.assertEqual(config["retrieval"]["backend"], "hybrid_bm25")
        self.assertTrue(config["decision"]["require_evidence_for_true_alert"])
        self.assertEqual(config["llm_gate"]["max_llm_calls_per_minute"], 0)

    def test_context_rescue_cache_is_seeded_from_view_a(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view_a_root = root / "view_a"
            source = view_a_root / "cache" / "paper_500" / "hybrid_bm25_top6.jsonl"
            source.parent.mkdir(parents=True)
            source.write_text('{"key":"cached"}\n', encoding="utf-8")
            args = argparse.Namespace(
                cache_dir=str(root / "view_b_cache"),
                split="paper_500",
                view_a_root=str(view_a_root),
                allow_existing_cache=False,
            )

            cache_path, state = activate_cache(args, "context_rescue")

            self.assertEqual(state, "seeded_from_view_a_bm25")
            self.assertEqual(cache_path.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
