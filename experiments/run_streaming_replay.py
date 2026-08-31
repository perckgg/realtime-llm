from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.main import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="nezha_setup/config/experiment_nezha_smoke.yaml")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--audit-dir", default=None)
    parser.add_argument("--speedup", type=float, default=0.0)
    parser.add_argument("--max-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--ingest-lag-seconds", type=float, default=0.0)
    parser.add_argument("--max-windows", type=int, default=None)
    args = parser.parse_args()

    config = copy.deepcopy(load_config(args.config))
    if args.output_dir:
        config.setdefault("evaluation", {})["output_dir"] = args.output_dir
    if args.audit_dir:
        config.setdefault("evaluation", {})["audit_dir"] = args.audit_dir
    if args.max_windows is not None:
        config.setdefault("evaluation", {})["max_windows"] = args.max_windows
    config["streaming"] = {
        "speedup": args.speedup,
        "max_sleep_seconds": args.max_sleep_seconds,
        "ingest_lag_seconds": args.ingest_lag_seconds,
    }
    _, message = run_pipeline(config, "hybrid", replay_stream=True, output_mode="streaming_hybrid")
    print(message)


if __name__ == "__main__":
    main()
