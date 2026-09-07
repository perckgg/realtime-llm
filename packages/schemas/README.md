# packages/schemas

`models.py` — Pydantic v2 models shared by every service, copied verbatim from
`docs/Final_Thesis_Phase2/03-schemas-and-contracts.md` §1. Only the models needed through Week 2
are implemented so far: `MetricPoint`, `LogEvent`, `TraceSpan`, `WindowLabel`, `TelemetryWindow`,
`AlertCandidate`. `RetrievalResult`, `JudgedAlert`, `Incident`, `DiagnosticReport` are added when
the services that need them are ported (see `docs/CURRENT-WEEK.md`). No service may define its own
copy of a schema (R-B2) — import from here.

`loaders.py` — `iter_telemetry_windows` wraps the Week 1 labelling logic in
`scripts/nezha_windows.py` and emits `TelemetryWindow` objects for `services/replayer`. Drops
non-finite metric values (the Nezha `"NaN"`-literal percentile bug, see `docs/experiment-log.md`
QĐ-009) instead of parsing them as 0.0/inf. `logs`/`spans` are intentionally left empty — no Week 2
service consumes them yet.

The four core Protocols (`SourceAdapter`, `Detector`, `RetrievalStrategy`, `Judge`,
`01-architecture-design.md` §5) are Week 3 work, not started here.

Tests: `tests/test_loaders.py`.
