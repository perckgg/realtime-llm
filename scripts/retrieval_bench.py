"""Benchmark / equivalence check for retrieval strategies (V17, QD-022).

    # 1. collect the candidates of a run config once (replay + detector, no retrieval)
    py scripts/retrieval_bench.py collect --config eval/configs/m3_c1_window_smoke.yaml
    # 2. run a retrieval block over them -> data/bench/<name>.jsonl (top-k ids, scores, latency)
    py scripts/retrieval_bench.py run --config eval/configs/m3_c1_window_smoke.yaml --name c1_new [--limit 50]
    # 3. compare two outputs (same ids in the same order, score differences)
    py scripts/retrieval_bench.py compare --a data/bench/c1_ref.jsonl --b data/bench/c1_new.jsonl

`--set key=value` overrides `retrieval.params` (YAML values), e.g. `--set k_graph=3`.
Candidates are exactly the ones the harness would retrieve for (no gate in the
smoke configs). Outputs live under data/ (not committed).
"""

from __future__ import annotations

import argparse
import json
import pickle
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.runner import _detector, _evaluated, _train_ids, load_config  # noqa: E402
from packages.schemas.evidence import NezhaEvidenceStore  # noqa: E402
from packages.schemas.models import AlertCandidate  # noqa: E402
from services.detector.candidates import build_alert_candidate  # noqa: E402
from services.replayer.nezha_source import NezhaReplaySource  # noqa: E402
from services.retrieval.registry import build_budget, build_strategy  # noqa: E402

BENCH = REPO / "data" / "bench"


def _candidates_path(config: dict[str, Any]) -> Path:
    return BENCH / f"candidates_{config.get('split', 'set')}_{config.get('n_windows', 'all')}.pkl"


def collect(config: dict[str, Any]) -> list[AlertCandidate]:
    path = _candidates_path(config)
    if path.exists():
        with path.open("rb") as handle:
            return pickle.load(handle)  # noqa: S301 -- our own file
    time_source = config.get("time_source", "wall")
    evaluated, _ = _evaluated(config)
    detector, fit = _detector(config)
    train_ids = _train_ids(fit)
    detector.fit(
        NezhaReplaySource(window_ids=train_ids, include_history=True, time_source=time_source).stream(),
        train_ids=train_ids,
    )
    replay = NezhaReplaySource(
        window_ids=evaluated, include_history=True, time_source=time_source, limit=config.get("n_windows")
    )
    candidates: list[AlertCandidate] = []
    for window in replay.stream():
        if not replay.is_evaluated(window):
            detector.observe(window)
            continue
        score = detector.score(window)
        candidate = build_alert_candidate(
            window, score, detector.is_candidate(window, score), detector.top_features(window)
        )
        if candidate is not None:
            candidates.append(candidate)
    BENCH.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(candidates, handle)
    return candidates


def run(config: dict[str, Any], name: str, limit: int | None, overrides: list[str]) -> Path:
    candidates = collect(config)[:limit]
    retrieval = dict(config["retrieval"])
    params = dict(retrieval.get("params") or {})
    for item in overrides:
        key, value = item.split("=", 1)
        params[key] = yaml.safe_load(value)
    retrieval["params"] = params
    strategy = build_strategy(retrieval, NezhaEvidenceStore())
    budget = build_budget(retrieval)
    out = BENCH / f"{name}.jsonl"
    latencies = []
    started = time.perf_counter()
    with out.open("w", encoding="utf-8") as handle:
        for candidate in candidates:
            result = strategy.retrieve(candidate, budget)
            latencies.append(result.latency_ms)
            handle.write(
                json.dumps(
                    {
                        "candidate_id": candidate.candidate_id,
                        "ids": [e.event_id for e in result.events],
                        "scores": [e.score for e in result.events],
                        "origins": [e.origin for e in result.events],
                        "distances": [e.graph_distance for e in result.events],
                        "latency_ms": result.latency_ms,
                    }
                )
                + "\n"
            )
    wall = time.perf_counter() - started
    latencies.sort()
    print(
        json.dumps(
            {
                "name": name,
                "n": len(latencies),
                "wall_s": round(wall, 1),
                "mean_ms": round(statistics.fmean(latencies), 1) if latencies else 0,
                "median_ms": round(statistics.median(latencies), 1) if latencies else 0,
                "p95_ms": round(latencies[int(0.95 * (len(latencies) - 1))], 1) if latencies else 0,
                "params": params,
            }
        )
    )
    return out


def compare(a: Path, b: Path) -> None:
    left = [json.loads(line) for line in a.open(encoding="utf-8")]
    right = [json.loads(line) for line in b.open(encoding="utf-8")]
    n = min(len(left), len(right))
    same = 0
    max_diff = 0.0
    mismatches = []
    for x, y in zip(left[:n], right[:n], strict=True):
        if x["candidate_id"] != y["candidate_id"]:
            raise SystemExit("candidate order differs")
        if x["ids"] == y["ids"]:
            same += 1
            for s, t in zip(x["scores"], y["scores"], strict=True):
                max_diff = max(max_diff, abs(s - t))
        else:
            mismatches.append(x["candidate_id"])
    print(json.dumps({"compared": n, "identical_topk": same, "max_score_diff": max_diff, "mismatch": mismatches[:10]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--config", type=Path, required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--config", type=Path, required=True)
    p_run.add_argument("--name", required=True)
    p_run.add_argument("--limit", type=int)
    p_run.add_argument("--set", action="append", default=[])
    p_cmp = sub.add_parser("compare")
    p_cmp.add_argument("--a", type=Path, required=True)
    p_cmp.add_argument("--b", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "collect":
        print(len(collect(load_config(args.config))), "candidates")
    elif args.cmd == "run":
        run(load_config(args.config), args.name, args.limit, args.set)
    else:
        compare(args.a, args.b)


if __name__ == "__main__":
    main()
