"""Retrieval-only ablation of C1's Fusion weights x k_graph (M4 task 3, V22 (a), QD-025).

    py scripts/fusion_ablation.py --config eval/configs/m4_fusion_ablation_val.yaml

Writes eval/results/<run_id>/ (grid.json, per_candidate.csv, runtime.json); never overwrites.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.fusion_ablation import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if config.get("split") == "test":
        raise SystemExit("test split is locked until M8 (G-test)")
    out_dir = run(config)
    runtime = json.loads((out_dir / "runtime.json").read_text(encoding="utf-8"))
    print(json.dumps(runtime, indent=2))
    for entry in json.loads((out_dir / "grid.json").read_text(encoding="utf-8")):
        cr = entry["concurrent_root"]
        print(
            f"{entry['point']:28s} nonfault graph={entry['nonfault']['with_graph_evidence']:5d} "
            f"share={entry['nonfault']['graph_share_mean'] or 0:.3f} | fault graph={entry['fault']['with_graph_evidence']:4d} "
            f"share={entry['fault']['graph_share_mean'] or 0:.3f} | concurrent root {cr['hits']}/{cr['n']}"
        )
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
