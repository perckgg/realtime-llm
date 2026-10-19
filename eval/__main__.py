"""`py -m eval run --config eval/configs/<name>.yaml` (02 SS3)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from eval.harness.runner import REPO, load_config, run


def main() -> int:
    parser = argparse.ArgumentParser(prog="py -m eval")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="run one config, write eval/results/<run_id>/")
    run_parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
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
