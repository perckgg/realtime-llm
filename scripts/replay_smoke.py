"""Milestone M0 smoke test / reproduction script, updated in M1 (QD-015):
replay windows from the `dev` split through IsolationForestDetector and
write one fact_alert_evaluation row per evaluated window (candidate or not,
per 03-schemas-and-contracts.md SS3.1) to ClickHouse.

    docker compose --profile dev up -d
    py scripts/replay_smoke.py --windows 50 --run-id m1-smoke

The detector is fitted on the dev split's windows -- GD1's unsupervised
Isolation Forest fits and scores the same corpus, see docs/experiment-log.md
QD-009 -- with the continuous history of every pod replayed through its
rolling buffer (QD-015, D2). The replay then streams in time order: windows
outside dev only update the buffers (`observe`), the first N dev windows are
scored and written. Refuses to write under a run_id that already has rows
(AGENTS.md rule 3).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.schemas.loaders import load_split_window_ids
from packages.storage.clickhouse import (
    get_client,
    insert_alert_evaluations,
    pending_alert_evaluation_row,
    run_exists,
)
from services.detector.candidates import build_alert_candidate
from services.detector.isolation_forest import IsolationForestDetector
from services.replayer.nezha_source import NezhaReplaySource


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=int, default=50)
    parser.add_argument("--run-id", required=True, help="new run_id; must not exist in ClickHouse yet")
    args = parser.parse_args()

    client = get_client()
    try:
        if run_exists(args.run_id, client=client):
            raise SystemExit(f"run_id {args.run_id!r} already has rows in fact_alert_evaluation; pick a new run_id.")

        dev_ids = load_split_window_ids("dev")
        print(f"Fitting IsolationForestDetector on the dev split ({len(dev_ids)} windows, continuous history)...")
        detector = IsolationForestDetector()
        detector.fit(NezhaReplaySource(window_ids=dev_ids, include_history=True).stream(), train_ids=dev_ids)

        print(f"Replaying until {args.windows} dev windows have been scored...")
        rows = []
        n_candidates = 0
        replay = NezhaReplaySource(window_ids=dev_ids, include_history=True, limit=args.windows)
        for window in replay.stream():
            if not replay.is_evaluated(window):
                detector.observe(window)
                continue
            score = detector.score(window)
            candidate = build_alert_candidate(window, score, detector.is_candidate(window, score))
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

        insert_alert_evaluations(rows, client=client)
    finally:
        client.close()
    print(f"Wrote {len(rows)} rows to fact_alert_evaluation ({n_candidates} alert candidates).")


if __name__ == "__main__":
    main()
