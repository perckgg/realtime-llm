"""Milestone M1 end-to-end smoke: dev candidate -> BM25 -> judge -> JudgedAlert.

Fits IsolationForestDetector on dev exactly like scripts/replay_smoke.py,
replays dev in time order until N candidates appear, retrieves evidence for
each from the full Nezha log/trace store (`bm25_hybrid`, GD2 window pool) and
judges it twice: with the `mock` backend and with the GD2 judge model (QD-021)
through the cache (data/llm_cache/gemini.jsonl; GEMINI_API_KEY from .env is
only needed on a cache miss). Writes, under eval/results/<run_id>/:

- retrieval.jsonl  one RetrievalResult per candidate
- judged.jsonl     one JudgedAlert per (candidate, backend)

    py scripts/judge_smoke.py --run-id m1-judge-smoke [--candidates 3] [--fault-only]

`--fault-only` uses the label only to pick which candidates to show (a fault
window makes a more informative example); it never reaches retrieval or the
judge. Refuses to reuse an existing run_id directory (AGENTS.md rule 3).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

from packages.schemas.evidence import NezhaEvidenceStore
from packages.schemas.loaders import load_split_window_ids
from packages.schemas.models import RetrievalBudget
from services.detector.candidates import build_alert_candidate
from services.detector.isolation_forest import IsolationForestDetector
from services.judge.registry import build_judge
from services.replayer.nezha_source import NezhaReplaySource
from services.retrieval.registry import build_strategy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidates", type=int, default=1)
    parser.add_argument("--fault-only", action="store_true")
    parser.add_argument("--skip-gemini", action="store_true")
    args = parser.parse_args()

    out_dir = REPO / "eval" / "results" / args.run_id
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists; pick a new --run-id")
    load_dotenv(REPO / ".env")

    dev_ids = load_split_window_ids("dev")
    started = time.perf_counter()
    detector = IsolationForestDetector()
    detector.fit(NezhaReplaySource(window_ids=dev_ids, include_history=True).stream(), train_ids=dev_ids)
    print(f"detector fitted on dev in {time.perf_counter() - started:.0f} s")

    store = NezhaEvidenceStore()
    retriever = build_strategy({"type": "bm25_hybrid", "params": {}}, store)
    budget = RetrievalBudget()
    judges = {"mock": build_judge({"backend": "mock"})}
    if not args.skip_gemini:
        judges["gemini"] = build_judge({"backend": "api"})

    out_dir.mkdir(parents=True)
    picked = 0
    replay = NezhaReplaySource(window_ids=dev_ids, include_history=True)
    with (out_dir / "retrieval.jsonl").open("w", encoding="utf-8") as retrieval_out, (
        out_dir / "judged.jsonl"
    ).open("w", encoding="utf-8") as judged_out:
        for window in replay.stream():
            if not replay.is_evaluated(window):
                detector.observe(window)
                continue
            score = detector.score(window)
            candidate = build_alert_candidate(
                window, score, detector.is_candidate(window, score), detector.top_features(window)
            )
            if candidate is None or (args.fault_only and not (window.label and window.label.is_fault)):
                continue
            result = retriever.retrieve(candidate, budget)
            retrieval_out.write(
                json.dumps({"candidate": candidate.model_dump(mode="json"), **result.model_dump(mode="json")}) + "\n"
            )
            label = window.label.model_dump() if window.label else None
            print(
                f"\n{candidate.candidate_id} {candidate.service} {candidate.ts:%Y-%m-%d %H:%M} "
                f"score={score:.3f} label={label}\n  retrieval: {len(result.events)} events, "
                f"pool={result.debug['pool_size']}, {result.latency_ms:.0f} ms"
            )
            for name, judge in judges.items():
                judged = judge.evaluate(candidate, result)
                judged_out.write(json.dumps({"backend_config": name, **judged.model_dump(mode="json")}) + "\n")
                print(
                    f"  {name}: verdict={judged.verdict} raw={judged.raw_verdict} conf={judged.confidence} "
                    f"evidence={len(judged.evidence_event_ids)} cache_hit={judged.cache_hit} "
                    f"model_version={judged.debug.get('model_version')} error={judged.debug.get('error')}"
                )
            picked += 1
            if picked >= args.candidates:
                break
    print(f"\nwrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
