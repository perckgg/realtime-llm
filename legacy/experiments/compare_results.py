from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.metrics import false_positive_reduction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/results")
    args = parser.parse_args()
    input_dir = Path(args.input)
    summaries = {}
    for path in sorted(input_dir.glob("*_results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        summaries[payload["mode"]] = payload["summary"]
    base = summaries.get("detector_only", {})
    for mode, summary in summaries.items():
        summary["false_positive_reduction_vs_detector"] = false_positive_reduction(base, summary)
    output = input_dir / "comparison_report.json"
    output.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
