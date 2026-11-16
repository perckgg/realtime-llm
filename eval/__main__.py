"""`py -m eval run --config eval/configs/<name>.yaml` (02 SS3);
`py -m eval compare --runs a=run_a,b=run_b [--detector-only run] --out name` (eval/harness/compare.py);
`py -m eval ctav --config eval/configs/ctav_final.yaml` (eval/harness/ctav.py);
`py -m eval rescue --config eval/configs/m7_rescue_*.yaml` (eval/harness/rescue.py)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from eval.harness.runner import REPO, RESULTS, _git_commit, load_config, run


def _compare(args: argparse.Namespace) -> int:
    from eval.harness.compare import compare, parse_methods, table, write

    report = compare(parse_methods(args.runs, args.detector_only), RESULTS, n_boot=args.n_boot, seed=args.seed)
    report["git_commit"] = _git_commit()
    path = write(report, RESULTS / args.out)
    print(table(report, "telemetry"))
    print(table(report, "all"))
    print(f"wrote {path}")
    return 0


def _ctav(args: argparse.Namespace) -> int:
    from eval.harness import ctav

    config = ctav.load_ctav_config(args.config)
    out_dir = RESULTS / config["run_id"]
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    report, replay, outcome, _ = ctav.evaluate(config, RESULTS)
    report["git_commit"] = _git_commit()
    ctav.write(report, replay, outcome, out_dir, args.config.read_text(encoding="utf-8"))
    print(ctav.table(report))
    print(f"wrote {out_dir}")
    return 0


def _rescue(args: argparse.Namespace) -> int:
    from eval.harness import rescue

    config = rescue.load_rescue_config(args.config)
    out_dir = RESULTS / config["run_id"]
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    base = rescue.load_base(config, RESULTS, REPO)
    frame = rescue.load_features(RESULTS, config["features"], base.replay.ids)
    union = None
    if "judged_run" in config:
        report = rescue.evaluate(config, base, frame, RESULTS)
    else:
        report, union = rescue.plan(config, base, frame)
    report["git_commit"] = _git_commit()
    rescue.write(report, out_dir, args.config.read_text(encoding="utf-8"), union)
    print(rescue.table(report))
    print(f"wrote {out_dir}")
    return 0


def _rca(args: argparse.Namespace) -> int:
    """`py -m eval rca --config eval/configs/rca_final.yaml` (eval/harness/rca.py, M9)."""
    from datetime import UTC, datetime

    from eval.harness import rca

    load_dotenv(REPO / ".env")
    config = rca.load_rca_config(args.config)
    out_dir = RESULTS / config["run_id"]
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists: results are never overwritten, use a new run_id")
    started_at = datetime.now(UTC)
    config_text = args.config.read_text(encoding="utf-8")
    to_postgres = bool((config.get("postgres") or {}).get("write", False))
    if to_postgres:  # fail before any LLM call, not after
        from services.rca_agent import store

        with store.connect() as conn:
            if store.run_exists(conn, config["run_id"]):
                raise SystemExit(f"run_id {config['run_id']} is already in run_registry: use a new run_id")
    report, located, inputs, graph = rca.evaluate(config, RESULTS)
    summaries = None
    if (config.get("summarizer") or {}).get("enabled", False):
        report["summarizer"], summaries = rca.summarize(config, located, inputs, graph, RESULTS)
    report["git_commit"] = _git_commit()
    report["method_fingerprint"] = rca.config_fingerprint(config)
    if to_postgres:
        report["postgres_rows"] = rca.write_postgres(config, config_text, report["git_commit"], started_at, located, summaries)
    rca.write(report, located, summaries, out_dir, config_text)
    print(rca.table(report))
    print(f"method fingerprint {report['method_fingerprint']}")
    print(f"wrote {out_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="py -m eval")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="run one config, write eval/results/<run_id>/")
    run_parser.add_argument("--config", type=Path, required=True)
    compare_parser = sub.add_parser("compare", help="paired comparison of runs, write eval/results/<out>/")
    compare_parser.add_argument("--runs", required=True, help="name=run_id,... (first = reference)")
    compare_parser.add_argument("--detector-only", help="run whose candidates give the detector-only baseline")
    compare_parser.add_argument("--out", required=True, help="new directory name under eval/results/")
    compare_parser.add_argument("--n-boot", type=int, default=1000)
    compare_parser.add_argument("--seed", type=int, default=42)
    ctav_parser = sub.add_parser("ctav", help="CTAV replay on cached tier runs (C2+C3+C4, M6)")
    ctav_parser.add_argument("--config", type=Path, required=True)
    rescue_parser = sub.add_parser("rescue", help="Rescue Score (C5) plan / ablation on top of CTAV (M7)")
    rescue_parser.add_argument("--config", type=Path, required=True)
    rca_parser = sub.add_parser("rca", help="RCA agent on the alerts of a CTAV run: incidents, Hit@k, ARR, reports (M9)")
    rca_parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "compare":
        return _compare(args)
    if args.command == "ctav":
        return _ctav(args)
    if args.command == "rescue":
        return _rescue(args)
    if args.command == "rca":
        return _rca(args)
    load_dotenv(REPO / ".env")
    out_dir = run(load_config(args.config))
    metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    for subset in ("telemetry", "all"):
        p = metrics[subset]["pipeline"]
        print(
            f"{subset:9s} P={p['precision']:.4f} R={p['recall']:.4f} F1={p['f1']:.4f} FPR={p['fpr']:.4f} "
            f"TP={p['tp']} FP={p['fp']} FN={p['fn']} TN={p['tn']}"
        )
    errors = json.loads((out_dir / "runtime.json").read_text(encoding="utf-8")).get("judge_errors", 0)
    if errors:
        print(f"WARNING: {errors} judge call(s) failed and were counted as manual review; "
              "re-run under a new run_id to retry them (successful answers come from the cache)")
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
