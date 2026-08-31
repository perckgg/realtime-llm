"""Stratified real-LLM evaluation runner.

Reduces real-LLM API calls by selecting a balanced slice of windows:
  - all positive windows (label == true_alert), capped at max_positives
  - a random sample of negative windows (label != true_alert)

Designed to mitigate Gemini free-tier 429 issues:
  - works together with the LLM response cache (LLM_RESPONSE_CACHE env var)
  - respects llm_gate.max_total_calls so the API budget is bounded
  - prints the selected slice so re-runs are reproducible
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _load_dotenv(path: Path) -> None:
    env_path = path
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from src.config import load_config
from src.ingestion.metric_loader import load_metrics
from src.main import run_pipeline
from src.preprocessing.metric_preprocessing import create_metric_windows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", default="hybrid")
    parser.add_argument("--max-positives", type=int, default=40,
                        help="Cap on positive windows included in the slice.")
    parser.add_argument("--max-negatives", type=int, default=80,
                        help="Cap on negative windows included in the slice.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cache-path", default=None,
                        help="If set, exports LLM_RESPONSE_CACHE for this run.")
    parser.add_argument("--output-mode", default=None)
    parser.add_argument("--env-file", action="append", default=[],
                        help="Optional extra .env file. Values do not override existing environment variables.")
    args = parser.parse_args()

    for env_file in args.env_file:
        _load_dotenv(Path(env_file))

    if args.cache_path:
        os.environ["LLM_RESPONSE_CACHE"] = args.cache_path
        # Force re-init in case cache module was already imported.
        from src.llm import response_cache
        response_cache.reset_global_cache_for_tests()

    config = load_config(args.config)
    metrics = load_metrics(config["data"]["metric_path"])
    windows = create_metric_windows(
        metrics,
        int(config["preprocessing"]["window_size"]),
        int(config["preprocessing"]["stride"]),
        str(config["preprocessing"]["normalization"]),
    )

    positive_indices = [i for i, w in enumerate(windows) if w.label == "true_alert"]
    negative_indices = [i for i, w in enumerate(windows) if w.label != "true_alert"]

    rng = random.Random(args.seed)
    rng.shuffle(positive_indices)
    chosen_positives = positive_indices[: args.max_positives]
    rng.shuffle(negative_indices)
    chosen_negatives = negative_indices[: args.max_negatives]

    selected = sorted(set(chosen_positives + chosen_negatives))
    if not selected:
        raise RuntimeError("No windows selected. Check label distribution and caps.")

    print(
        f"[stratified] total_windows={len(windows)} "
        f"positives_available={len(positive_indices)} "
        f"negatives_available={len(negative_indices)} "
        f"selected={len(selected)} "
        f"selected_positives={len(chosen_positives)} "
        f"selected_negatives={len(chosen_negatives)} "
        f"seed={args.seed}"
    )
    cache_path = os.environ.get("LLM_RESPONSE_CACHE", "")
    if cache_path and cache_path.lower() not in {"off", "false", "0", "no"}:
        print(f"[stratified] response cache enabled -> {cache_path}")

    output_mode = args.output_mode or f"{args.mode}_stratified"
    output_dir = Path(str(config.get("evaluation", {}).get("output_dir", "outputs/results")))
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_path = output_dir / f"{output_mode}_selected_indices.json"
    selected_path.write_text(
        json.dumps(
            {
                "seed": args.seed,
                "selected": selected,
                "selected_positives": chosen_positives,
                "selected_negatives": chosen_negatives,
                "positive_count": len(chosen_positives),
                "negative_count": len(chosen_negatives),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[stratified] selected indices -> {selected_path}")
    _, message = run_pipeline(
        config,
        args.mode,
        output_mode=output_mode,
        window_indices=selected,
    )
    print(message)


if __name__ == "__main__":
    main()
