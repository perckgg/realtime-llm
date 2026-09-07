# services/replayer

Implements `SourceAdapter` (`docs/Final_Thesis_Phase2/01-architecture-design.md` §5.1) as
`NezhaReplaySource` (`nezha_source.py`).

Wraps `packages.schemas.loaders.iter_telemetry_windows` and yields `TelemetryWindow` objects in
deterministic time order (`start_ts`, then `window_id` as a tiebreak). Construct with either
`split="dev"` (reads `data/splits/dev.json`) or an explicit `window_ids` set — the two are
mutually exclusive. `speed_multiplier<=0` disables the inter-window sleep, which experiments need
to replay a split without wall-clock delay; a positive multiplier sleeps proportionally to the gap
between consecutive `start_ts` values, for anything that wants to observe real-time pacing.

Tests: `tests/test_replayer.py` (pure ordering/config logic, loader monkeypatched — no dataset
needed).

See also `scripts/replay_smoke.py`, which drives this source end-to-end into
`packages.storage.clickhouse` for the Week 2 DoD.
