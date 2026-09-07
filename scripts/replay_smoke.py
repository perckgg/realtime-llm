"""Week 2 smoke test / reproduction script (docs/CURRENT-WEEK.md DoD):
replay windows from the `dev` split through IsolationForestDetector and
write one fact_alert_evaluation row per window (candidate or not, per
03-schemas-and-contracts.md SS3.1) to ClickHouse.

    docker compose --profile dev up -d
    python scripts/replay_smoke.py --windows 50

Fits the detector on the full dev split -- GD1's unsupervised Isolation
Forest fits and scores the same corpus, see docs/experiment-log.md QD-009 --
then replays the first N dev windows in time order through
services.replayer.NezhaReplaySource.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.schemas.loaders import load_split_window_ids  # noqa: E402
from packages.storage.clickhouse import get_client, insert_alert_evaluations, pending_alert_evaluation_row  # noqa: E402
from services.detector.candidates import build_alert_candidate  # noqa: E402
from services.detector.isolation_forest import IsolationForestDetector  # noqa: E402
from services.replayer.nezha_source import NezhaReplaySource  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=int, default=50)
    parser.add_argument("--run-id", default="week2-smoke")
    args = parser.parse_args()

    dev_ids = load_split_window_ids("dev")

    print(f"Fitting IsolationForestDetector on the dev split ({len(dev_ids)} windows)...")
    detector = IsolationForestDetector()
    detector.fit(NezhaReplaySource(window_ids=dev_ids, speed_multiplier=0).stream())

    print(f"Replaying first {args.windows} dev windows...")
    rows = []
    n_candidates = 0
    replay = NezhaReplaySource(window_ids=dev_ids, speed_multiplier=0, limit=args.windows)
    for window in replay.stream():
        score = detector.score(window)
        is_candidate = detector.is_candidate(window, score)
        candidate = build_alert_candidate(window, score, is_candidate)
        if candidate is not None:
            n_candidates += 1
        label = window.label
        rows.append(
            pending_alert_evaluation_row(
                run_id=args.run_id,
                window_id=window.window_id,
                service=window.service,
                window_ts=window.start_ts,
                anomaly_score=score,
                candidate_source=candidate.source if candidate else "none",
                label_is_fault=bool(label and label.is_fault),
                label_fault_type=(label.fault_type if label else None) or "normal",
                label_root_cause=label.root_cause_service if label else None,
            )
        )

    client = get_client()
    try:
        insert_alert_evaluations(rows, client=client)
    finally:
        client.close()
    print(f"Wrote {len(rows)} rows to fact_alert_evaluation ({n_candidates} alert candidates).")


if __name__ == "__main__":
    main()
