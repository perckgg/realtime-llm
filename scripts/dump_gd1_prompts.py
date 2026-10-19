"""Re-run GD1's Step 7 View A pipeline offline and dump every judge input.

For each LLM call the GD1 pipeline makes on a frozen split (default
`paper_500`, variant `hybrid_bm25_top6`, full budget), this writes one JSONL
row with the GD1 alert candidate, the top-k contexts handed to the judge, the
exact prompt and the Gemini cache key GD1 would have used. The judge is
forced to `mock`, so no API is called; the cache key is recomputed with the
settings recorded in the GD1 run's config snapshot (gemini-2.5-flash-lite,
max_output_tokens=1024, temperature 0).

Why: M3's gate G-paper requires a 100% hit on GD1's Gemini cache, which only
happens if GD2's ported retrieval + prompt composer reproduce GD1's prompt
byte for byte. This dump is the reference those ports are tested against
(tests/test_gd1_prompt_parity.py, docs/experiment-log.md QD-016) and is also
the "GD1 candidates" input M2's G-port compares retrieval against.

    py scripts/dump_gd1_prompts.py                     # -> data/gd1_parity/paper_500_hybrid_bm25_top6.jsonl
    py scripts/dump_gd1_prompts.py --split paper_300
    py scripts/dump_gd1_prompts.py --split phase4 --max-total-calls 40

`--split phase4` replays GD1 Phase 4 (legacy/nezha_setup/config/
experiment_phase4_benchmark.yaml: first 300 windows, its own retrieval
weights, search_k 500, budget 30) -- the input of M2's gate G-port. Raise
`--max-total-calls` to 40 there so all 40 Phase 4 candidates are retrieved;
compare verdicts only on the 30 GD1 actually judged.

Runs from legacy/ (GD1 resolves its data paths relative to it). Takes a few
minutes: GD1 fits its detector and scores every window of the split.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
LEGACY = REPO / "legacy"

GD1_RUN = "outputs/phase2/step7_rerun/quality_full_budget"
CONFIGS = {
    "paper_300": "nezha_setup/config/experiment_phase2_topology_fusion_300w.yaml",
    "paper_500": "nezha_setup/config/experiment_phase2_topology_fusion_500w.yaml",
    "phase4": "nezha_setup/config/experiment_phase4_benchmark.yaml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--split", default="paper_500", choices=sorted(CONFIGS))
    parser.add_argument("--variant", default="hybrid_bm25_top6", choices=["hybrid_bm25_top6"])
    parser.add_argument("--max-total-calls", type=int, default=500, help="GD1 quality_full_budget = 500")
    parser.add_argument("--model", default="gemini-2.5-flash-lite")
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument(
        "--cache",
        default=f"{GD1_RUN}/cache/paper_500/hybrid_bm25_top6.jsonl",
        help="GD1 Gemini cache (relative to legacy/) used to report hit rate",
    )
    parser.add_argument("--out", default=None, help="default data/gd1_parity/<split>_<variant>.jsonl")
    return parser.parse_args()


def _cache_key(model: str, prompt: str, max_output_tokens: int) -> str:
    # legacy/src/llm/response_cache.py ResponseCache.make_key, extra from
    # legacy/src/llm/judge_client.py _gemini_response.
    raw = "|".join(["gemini", model, prompt, f"max={max_output_tokens}|t=0"])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    args = parse_args()
    os.chdir(LEGACY)
    sys.path.insert(0, str(LEGACY))
    os.environ["LLM_RESPONSE_CACHE"] = "off"

    import src.main as gd1_main
    from src.config import load_config
    from src.ingestion.metric_loader import load_metrics
    from src.preprocessing.metric_preprocessing import create_metric_windows

    config = copy.deepcopy(load_config(CONFIGS[args.split]))
    indices: list[int] | None = None
    if args.split != "phase4":
        freeze = json.loads(Path("outputs/phase2/input_freeze.json").read_text(encoding="utf-8"))
        with Path("outputs/phase2/window_index.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        selected = list(
            dict.fromkeys(r["window_id"] for r in rows if r.get("split") == args.split and r["window_id"])
        )
        meta = freeze["window_sets"][args.split]
        digest = hashlib.sha256("".join(f"{w}\n" for w in selected).encode("utf-8")).hexdigest()
        if len(selected) != int(meta["rows"]) or digest != meta["window_id_sha256"]:
            raise SystemExit(f"{args.split}: window set does not match input_freeze.json")
        windows = create_metric_windows(
            load_metrics(config["data"]["metric_path"]),
            int(config["preprocessing"]["window_size"]),
            int(config["preprocessing"]["stride"]),
            str(config["preprocessing"]["normalization"]),
        )
        index = {w.window_id: i for i, w in enumerate(windows)}
        indices = [index[w] for w in selected]

    # legacy/scripts/phase2/run_step7_view_a.py _step7_config, judge forced to mock.
    config["evaluation"]["max_llm_calls"] = args.max_total_calls
    config["evaluation"]["output_dir"] = str(REPO / "data" / "gd1_parity" / "legacy_results")
    config["evaluation"]["audit_dir"] = str(REPO / "data" / "gd1_parity" / "legacy_audit")
    config["llm_gate"]["max_total_calls"] = args.max_total_calls
    config["llm"].update({"provider": "mock", "model": "mock-judge"})
    if args.split != "phase4":
        config["retrieval"].update({"backend": "hybrid_bm25", "vector_db": "hybrid_bm25", "top_k": 6})

    captured: list[dict[str, Any]] = []
    original = gd1_main.compose_prompt

    def capture(alert: Any, contexts: list[dict[str, Any]]) -> str:
        prompt = original(alert, contexts)
        captured.append(
            {
                "alert": asdict(alert),
                "contexts": copy.deepcopy(contexts),
                "prompt": prompt,
                "cache_key": _cache_key(args.model, prompt, args.max_output_tokens),
            }
        )
        return prompt

    gd1_main.compose_prompt = capture
    gd1_main.run_pipeline(config, "hybrid", output_mode=f"gd1_parity_{args.split}_{args.variant}", window_indices=indices)

    cached: set[str] = set()
    cache_path = Path(args.cache)
    if cache_path.exists():
        cached = {json.loads(line)["key"] for line in cache_path.open(encoding="utf-8") if line.strip()}
    out = Path(args.out) if args.out else REPO / "data" / "gd1_parity" / f"{args.split}_{args.variant}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in captured:
            row["in_gd1_cache"] = row["cache_key"] in cached
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    hits = sum(row["in_gd1_cache"] for row in captured)
    print(json.dumps({"out": str(out), "llm_calls": len(captured), "gd1_cache_entries": len(cached), "cache_hits": hits}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
