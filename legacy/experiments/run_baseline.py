from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.main import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiment.yaml")
    parser.add_argument("--mode", choices=["detector_only", "llm_without_rag"], required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    _, message = run_pipeline(config, args.mode)
    print(message)


if __name__ == "__main__":
    main()
