"""NezhaReplaySource — the GD2 `SourceAdapter` (01-architecture-design.md
SS5.1, SS6.1). Wraps packages.schemas.loaders.iter_telemetry_windows so the
rest of the pipeline never parses the Nezha CSVs itself.

Ported from legacy/experiments/run_streaming_replay.py's watermark wait
(`_replay_wait`): sleep between windows scaled by `speed_multiplier`, capped
so a demo doesn't stall on a multi-hour gap between two windows. Experiments
must use `speed_multiplier=0` (SS6.1: "Thuc nghiem luon chay speed_multiplier:
0"), which streams as fast as possible with no sleeping at all.

`include_history=True` (QD-015, D2): the committed splits group windows by
fault injection and drop normal windows within 600 s of an injection
(QD-004), so a split on its own is not a continuous time series -- a fault
onset's preceding sample is never in the same split. In history mode the
source streams every window in time order and the split only marks which
ones are *evaluated* (`is_evaluated`); callers push the others into the
detector with `observe()` so rolling features see the real preceding sample.
No label of a non-evaluated window is used.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from packages.schemas.loaders import iter_telemetry_windows, load_split_window_ids
from packages.schemas.models import TelemetryWindow
from packages.schemas.nezha import DEFAULT_TIME_SOURCE, TimeSource


class NezhaReplaySource:
    """Replays Nezha windows in time order, oldest first.

    Deterministic: the same (split, time_source, include_history) always
    yields the same window sequence, because ordering is a stable sort on
    (start_ts, window_id) and window_id is itself deterministic
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
        include_history: bool = False,
    ) -> None:
        """
        Args:
            split: "dev" | "val" | "test" -- restricts evaluation to that
                committed split's window_ids. Mutually exclusive with
                `window_ids`.
            window_ids: explicit set of window_ids to evaluate, for callers
                that already have a subset (e.g. a smoke test). Mutually
                exclusive with `split`.
            speed_multiplier: 1.0 = wall-clock real time between windows,
                0 = as fast as possible (required for experiments). >1 speeds
                up a demo.
            limit: stop after this many *evaluated* windows.
            max_sleep_seconds: cap on any single inter-window sleep, so a
                multi-hour gap in the data doesn't stall a demo.
            include_history: also stream the non-evaluated windows (see the
                module docstring). Off by default so a plain split replay
                behaves exactly as before.
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
        self.include_history = include_history
        self._evaluated_ids: set[str] | None = None

    @property
    def evaluated_ids(self) -> set[str] | None:
        """The window_ids being evaluated (None = every streamed window)."""
        if self._evaluated_ids is None:
            if self.split is not None:
                self._evaluated_ids = load_split_window_ids(self.split)
            else:
                self._evaluated_ids = self._explicit_window_ids
        return self._evaluated_ids

    def is_evaluated(self, window: TelemetryWindow) -> bool:
        ids = self.evaluated_ids
        return ids is None or window.window_id in ids

    def stream(self) -> Iterator[TelemetryWindow]:
        selected = self.evaluated_ids
        loader_filter = None if self.include_history else selected
        windows = sorted(
            iter_telemetry_windows(root=self.root, time_source=self.time_source, window_ids=loader_filter),
            key=lambda window: (window.start_ts, window.window_id),
        )

        previous_start: datetime | None = None
        evaluated = 0
        for window in windows:
            if self.limit is not None and evaluated >= self.limit:
                return
            _wait(previous_start, window.start_ts, self.speed_multiplier, self.max_sleep_seconds)
            previous_start = window.start_ts
            yield window
            if selected is None or window.window_id in selected:
                evaluated += 1


def _wait(
    previous_start: datetime | None,
    current_start: datetime,
    speed_multiplier: float,
    max_sleep_seconds: float,
) -> None:
    if speed_multiplier <= 0 or previous_start is None:
        return
    delta_seconds = max(0.0, (current_start - previous_start).total_seconds())
    sleep_seconds = min(delta_seconds / speed_multiplier, max_sleep_seconds)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
