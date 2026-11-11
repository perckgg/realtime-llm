"""C3 anchoring facts for every event a tier run retrieved (M6, QD-031). No LLM call, no label.

    py scripts/build_anchor_features.py --config eval/configs/m6_anchor_features_val.yaml

For each (run, window, event) of the runs' `retrieval.jsonl`: modality, service, severity,
duration and, for trace spans, the rolling baseline (V30) and the `dev` baseline (QD-030)
at every configured percentile. Writes eval/results/<run_id>/events.jsonl.gz + summary.json.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.ctav import load_anchor_config  # noqa: E402
from eval.harness.runner import RESULTS, _git_commit  # noqa: E402
from packages.schemas.evidence import NezhaEvidenceStore  # noqa: E402
from packages.schemas.nezha import dataset_root  # noqa: E402
from services.judge.span_baseline import RollingSpanBaseline, SpanBaseline, span_operation  # noqa: E402


def trace_docs(store: NezhaEvidenceStore):  # type: ignore[no-untyped-def]
    anchor = datetime(2022, 1, 1, tzinfo=UTC)
    for file in store.files_for(anchor, anchor + timedelta(days=7300)):
        if file.kind == "trace":
            yield from store.load_file(file)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = load_anchor_config(args.config)
    out = RESULTS / config["run_id"]
    if out.exists():
        raise SystemExit(f"{out} already exists: results are never overwritten")
    rolling_spec = config["rolling"]
    percentiles = [int(p) for p in config["percentiles"]]
    started = time.perf_counter()
    rolling = RollingSpanBaseline.from_docs(trace_docs(NezhaEvidenceStore(dataset_root(), cache_files=2)))
    index_seconds = time.perf_counter() - started
    dev = SpanBaseline(pd.read_parquet(REPO / config["dev_baseline"]))

    out.mkdir(parents=True)
    summary: dict[str, Any] = {"config": config, "index_seconds": round(index_seconds, 1), "runs": {}}
    with gzip.open(out / "events.jsonl.gz", "wt", encoding="utf-8") as sink:
        for run in config["runs"]:
            with (RESULTS / run / "per_window.csv").open(encoding="utf-8", newline="") as handle:
                starts = {r["window_id"]: datetime.fromisoformat(r["window_ts"]) for r in csv.DictReader(handle)}
            counts: Counter[str] = Counter()
            with (RESULTS / run / "retrieval.jsonl").open(encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    for event in row["events"]:
                        record: dict[str, Any] = {
                            "run": run,
                            "window_id": row["window_id"],
                            "event_id": event["event_id"],
                            "service": event["service"],
                            "modality": event["modality"],
                            "severity": str(event["debug"].get("severity") or "INFO"),
                            "duration_ms": event["debug"].get("duration_ms"),
                        }
                        counts[event["modality"]] += 1
                        if event["modality"] == "trace":
                            operation = span_operation(event["content"])
                            n, points = rolling.thresholds(
                                event["service"],
                                operation,
                                starts[row["window_id"]],
                                float(rolling_spec["lookback_minutes"]),
                                float(rolling_spec["guard_seconds"]),
                                percentiles,
                                int(rolling_spec["min_spans"]),
                            )
                            record["rolling_n"] = n
                            record["rolling"] = {str(p): v for p, v in (points or {}).items()}
                            record["dev"] = {
                                str(p): v
                                for p in percentiles
                                if (v := dev.threshold(event["service"], operation, p) if operation else None)
                                is not None
                            }
                            counts["trace_rolling_covered"] += points is not None
                            counts["trace_dev_covered"] += bool(record["dev"])
                        sink.write(json.dumps(record) + "\n")
            summary["runs"][run] = dict(counts)
    summary["wall_seconds"] = round(time.perf_counter() - started, 1)
    summary["git_commit"] = _git_commit()
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "config.snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(json.dumps(summary["runs"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
