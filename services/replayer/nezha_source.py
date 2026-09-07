"""NezhaReplaySource — the GD2 `SourceAdapter` (01-architecture-design.md
SS5.1, SS6.1). Wraps packages.schemas.loaders.iter_telemetry_windows so the
rest of the pipeline never parses the Nezha CSVs itself.

Ported from legacy/experiments/run_streaming_replay.py's watermark wait
(`_replay_wait`): sleep between windows scaled by `speed_multiplier`, capped
so a demo doesn't stall on a multi-hour gap between two windows. Experiments
must use `speed_multiplier=0` (SS6.1: "Thuc nghiem luon chay speed_multiplier:
0"), which streams as fast as possible with no sleeping at all.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

from packages.schemas.loaders import iter_telemetry_windows, load_split_window_ids
from packages.schemas.models import TelemetryWindow
from scripts.nezha_windows import DEFAULT_TIME_SOURCE, TimeSource


class NezhaReplaySource:
    """Replays Nezha windows in time order, oldest first.

    Deterministic: the same (split, time_source, seed of the underlying data)
    always yields the same window sequence, because ordering is a stable sort
    on (start_ts, window_id) and window_id is itself deterministic
    (docs/experiment-log.md QD-003).
    """

    name = "nezha_replay"

    def __init__(
        self,
        split: str | None = None,
        window_ids: set[str] | None = None,
        speed_multiplier: float = 0.0,
        limit: int | None = None,
        max_sleep_seconds: float = 5.0,
        root: Path | None = None,
        time_source: TimeSource = DEFAULT_TIME_SOURCE,
    ) -> None:
        """
        Args:
            split: "dev" | "val" | "test" -- restricts the stream to that
                committed split's window_ids. Mutually exclusive with
                `window_ids`.
            window_ids: explicit set of window_ids to replay, for callers that
                already have a subset (e.g. a smoke test). Mutually exclusive
                with `split`.
            speed_multiplier: 1.0 = wall-clock real time between windows,
                0 = as fast as possible (required for experiments). >1 speeds
                up a demo.
            limit: stop after this many windows.
            max_sleep_seconds: cap on any single inter-window sleep, so a
                multi-hour gap in the data doesn't stall a demo.
        """
        if split is not None and window_ids is not None:
            raise ValueError("NezhaReplaySource: pass split or window_ids, not both")
        self.split = split
        self._explicit_window_ids = window_ids
        self.speed_multiplier = speed_multiplier
        self.limit = limit
        self.max_sleep_seconds = max_sleep_seconds
        self.root = root
        self.time_source = time_source

    def stream(self) -> Iterator[TelemetryWindow]:
        selected_ids = self._explicit_window_ids
        if self.split is not None:
            selected_ids = load_split_window_ids(self.split)

        windows = sorted(
            iter_telemetry_windows(root=self.root, time_source=self.time_source, window_ids=selected_ids),
            key=lambda window: (window.start_ts, window.window_id),
        )

        previous_start = None
        yielded = 0
        for window in windows:
            if self.limit is not None and yielded >= self.limit:
                return
            _wait(previous_start, window.start_ts, self.speed_multiplier, self.max_sleep_seconds)
            previous_start = window.start_ts
            yield window
            yielded += 1


def _wait(previous_start, current_start, speed_multiplier: float, max_sleep_seconds: float) -> None:
    if speed_multiplier <= 0 or previous_start is None:
        return
    delta_seconds = max(0.0, (current_start - previous_start).total_seconds())
    sleep_seconds = min(delta_seconds / speed_multiplier, max_sleep_seconds)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
