"""H1 -- mechanism of confirmation bias (M5, QD-027). See eval/harness/h1.py.

    py scripts/h1.py collect --config eval/configs/h1_val.yaml           # sample, no LLM
    py scripts/h1.py judge   --config eval/configs/h1_val.yaml --condition ref [--repeat 1 --subset 200]
    py scripts/h1.py analyze --runs ref=h1_val_ref_r0_v1,... --repeats ref=r0_run+r1_run+r2_run,... --out h1_val_analysis_v1

`collect` writes the sample (`h1.sample` in the config, never overwritten); `judge` writes
eval/results/<run_id>/ (judged.jsonl, runtime.json) per condition; `analyze` reads those runs.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.fusion_ablation import collect as replay_candidates  # noqa: E402
from eval.harness.h1 import (  # noqa: E402
    CONDITIONS,
    Params,
    analyze,
    build_sample,
    cited_near_share,
    feasibility,
    jobs_for,
    read_sample,
    repeat_stability,
    result_row,
    write_sample,
)
from eval.harness.runner import RESULTS, judge_all  # noqa: E402
from services.judge.backends import PRICES_PER_1M  # noqa: E402
from services.judge.registry import build_judge  # noqa: E402


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("split") == "test":
        raise SystemExit("test split is locked until M8 (G-test)")
    return config


def cmd_collect(args: argparse.Namespace) -> int:
    config = _config(args.config)
    sample = REPO / config["h1"]["sample"]
    if sample.exists():
        raise SystemExit(f"{sample} already exists: samples are never overwritten")
    params = Params.from_config(config["h1"])
    started = time.perf_counter()
    _, candidates = replay_candidates(config)
    kept = [(c, info) for c, info in candidates if info.has_telemetry]
    retrieval = dict(config["retrieval"])
    workers = int(retrieval.pop("workers", 1))
    built = build_sample(retrieval, [c for c, _ in kept], params, workers)
    rows = [
        {"candidate": c.model_dump(mode="json"), "window_id": info.window_id, "is_fault": info.is_fault, **row}
        for (c, info), row in zip(kept, built, strict=True)
    ]
    meta = {
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "config": config,
        "params": params.__dict__,
        "candidates_with_telemetry": len(kept),
        "feasibility": feasibility(rows),
        "wall_seconds": round(time.perf_counter() - started, 1),
    }
    write_sample(sample, rows, meta)
    print(json.dumps({k: meta[k] for k in ("candidates_with_telemetry", "feasibility", "wall_seconds")}, indent=2))
    print(f"wrote {sample}")
    return 0


def _subset(rows: list[dict[str, Any]], n_normal: int, seed: int) -> list[dict[str, Any]]:
    """`n_normal` normal rows drawn with `seed` + every fault row (for repeat runs)."""
    normal = sorted(r["candidate"]["candidate_id"] for r in rows if not r["is_fault"])
    keep = set(random.Random(seed).sample(normal, min(n_normal, len(normal))))
    return [r for r in rows if r["is_fault"] or r["candidate"]["candidate_id"] in keep]


def cmd_judge(args: argparse.Namespace) -> int:
    config = _config(args.config)
    load_dotenv(REPO / ".env")
    if config["judge"].get("backend", "api") == "api" and not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set (.env): refusing to write a run of cache misses")
    meta, rows = read_sample(REPO / config["h1"]["sample"])
    if args.subset:
        rows = _subset(rows, args.subset, int(config["h1"].get("seed", 42)))
    judge_config = {**config["judge"], "repeat": args.repeat}
    for condition in args.condition:
        if condition not in CONDITIONS:
            raise SystemExit(f"unknown condition {condition!r}; one of {CONDITIONS}")
        run_id = args.run_id.format(condition=condition, repeat=args.repeat)
        out_dir = RESULTS / run_id
        if out_dir.exists():
            raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
        jobs = jobs_for(rows, condition)
        judge = build_judge(judge_config)
        started = time.perf_counter()
        judged = judge_all(judge, [(c, ctx) for c, ctx, _ in jobs], int(config["judge"].get("workers", 8)))
        out = [result_row(condition, fault, j) for (_, _, fault), j in zip(jobs, judged, strict=True)]
        out_dir.mkdir(parents=True)
        with (out_dir / "judged.jsonl").open("w", encoding="utf-8") as handle:
            for row in out:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        api = [r for r in out if r["actual_api_call"]]
        prompt_tokens = sum(r["prompt_tokens"] or 0 for r in api)
        completion_tokens = sum(r["completion_tokens"] or 0 for r in api)
        price_in, price_out = PRICES_PER_1M[str(config["judge"]["model"])]
        runtime = {
            "run_id": run_id,
            "condition": condition,
            "repeat": args.repeat,
            "subset_normal": args.subset,
            "sample": config["h1"]["sample"],
            "sample_git_commit": meta["git_commit"],
            "git_commit": _git_commit(),
            "finished_at": datetime.now(UTC).isoformat(),
            "wall_seconds": round(time.perf_counter() - started, 1),
            "calls": len(out),
            "api_calls": len(api),
            "cache_hits": sum(1 for r in out if r["cache_hit"]),
            "errors": sum(1 for r in out if r["error"]),
            "prompt_tokens_api": prompt_tokens,
            "completion_tokens_api": completion_tokens,
            "estimated_usd_by_tokens": round(prompt_tokens * price_in / 1e6 + completion_tokens * price_out / 1e6, 4),
        }
        (out_dir / "runtime.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
        (out_dir / "config.snapshot.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
        print(json.dumps(runtime))
    return 0


def _read_run(run_id: str) -> list[dict[str, Any]]:
    with (RESULTS / run_id / "judged.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def cmd_analyze(args: argparse.Namespace) -> int:
    out_dir = RESULTS / args.out
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten")
    results: dict[str, list[dict[str, Any]]] = {}
    runs = dict(item.split("=", 1) for item in args.runs.split(","))
    for condition, run_id in runs.items():
        results[condition] = _read_run(run_id)
    report = {"runs": runs, "git_commit": _git_commit(), **analyze(results)}
    meta, rows = read_sample(REPO / args.sample)
    report["cited_near_share"] = cited_near_share(results, rows, float(meta["params"]["near_s"]))
    if args.repeats:
        repeat_runs = {c: ids.split("+") for c, ids in (item.split("=", 1) for item in args.repeats.split(","))}
        report["repeat_runs"] = repeat_runs
        report["repeat_stability"] = repeat_stability({c: [_read_run(i) for i in ids] for c, ids in repeat_runs.items()})
    out_dir.mkdir(parents=True)
    (out_dir / "h1_analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for cond, entry in report["conditions"].items():
        n, f = entry["normal"], entry["fault"]
        print(
            f"{cond:15s} normal n={n['n']:5d} raw_true={n['raw_true']:.3f} routed={n['routed']:.3f} | "
            f"fault n={f['n']:4d} raw_true={f['raw_true']:.3f} routed={f['routed']:.3f}"
        )
    for p in report["pairs"]:
        ci = p["diff_ci95"] or [float("nan")] * 2
        print(
            f"{p['condition']:15s} - {p['baseline']:11s} [{p['label']:6s}] n={p['n']:5d} "
            f"diff={p['diff']:+.3f} [{ci[0]:+.3f}; {ci[1]:+.3f}] McNemar p={p['mcnemar_p']:.3g}"
        )
    for label, t in report["time_trend"].items():
        ci = t["slope_ci95"] or [float("nan")] * 2
        print(f"time slope [{label}] n={t['n']} slope={t['slope_raw_true_per_share']:+.3f} [{ci[0]:+.3f}; {ci[1]:+.3f}] {t['by_level']}")
    for cond, entry in report["conditions"].items():
        for label in ("normal", "fault"):
            gate = " ".join(f"{k}:{v:.3f}" for k, v in entry[label]["gate"].items())
            print(f"gate {cond:15s} [{label:6s}] {gate}")
    for cond, entry in report["cited_near_share"].items():
        for label, s in entry.items():
            ci = s["near_share_ci95"] or [float("nan")] * 2
            print(f"cited near {cond:8s} [{label:6s}] alerts={s['alerts']:4d} cited={s['cited']:5d} near={s['near_share']:.3f} [{ci[0]:.3f}; {ci[1]:.3f}]")
    for cond, entry in report.get("repeat_stability", {}).items():
        for label, s in entry.items():
            ci = s["flip_rate_ci95"] or [float("nan")] * 2
            rates = " ".join(f"{r:.3f}" for r in s["raw_true_by_repeat"])
            print(f"repeat {cond:11s} [{label:6s}] n={s['n']:4d} raw_true={rates} flip={s['flip_rate']:.3f} [{ci[0]:.3f}; {ci[1]:.3f}]")
    print(f"wrote {out_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("collect")
    p.add_argument("--config", type=Path, required=True)
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("judge")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--condition", nargs="+", required=True)
    p.add_argument("--repeat", type=int, default=0)
    p.add_argument("--subset", type=int, default=0, help="judge only N seeded normal candidates (+ all faults)")
    p.add_argument("--run-id", default="h1_val_{condition}_r{repeat}_v1")
    p.set_defaults(fn=cmd_judge)
    p = sub.add_parser("analyze")
    p.add_argument("--runs", required=True, help="condition=run_id,...")
    p.add_argument("--repeats", default="", help="condition=run_r0+run_r1+run_r2,... (judge variance, QD-013)")
    p.add_argument("--sample", default="eval/samples/h1_val_v1.json.gz")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_analyze)
    args = parser.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
