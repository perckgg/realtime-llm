from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.main import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 2 topology-aware fusion integration experiment.")
    parser.add_argument("--config", default="nezha_setup\\config\\experiment_phase2_topology_fusion_300w.yaml")
    parser.add_argument("--output-mode", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    output_mode = args.output_mode or str(config.get("experiment", {}).get("name") or "topology_fusion")
    _, message = run_pipeline(config, "hybrid", output_mode=output_mode)
    print(message)


if __name__ == "__main__":
    main()
