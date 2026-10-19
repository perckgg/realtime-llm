# packages/schemas

`models.py` — Pydantic v2 models shared by every service, copied verbatim from
`docs/Final_Thesis_Phase2/03-schemas-and-contracts.md` §1. Implemented through M1: `MetricPoint`,
`LogEvent`, `TraceSpan`, `WindowLabel`, `TelemetryWindow`, `AlertCandidate`, `ContextEvent`,
`RetrievalBudget`, `RetrievalResult`, `JudgedAlert` (with the CTAV fields). `Incident` and
`DiagnosticReport` come with `services/rca_agent`. No service may define its own copy of a schema
(R-B2) — import from here.

`protocols.py` — the four interfaces of `01` §5 (`SourceAdapter`, `Detector`,
`RetrievalStrategy`, `Judge`), `runtime_checkable`. Signatures frozen from M1.

`evidence.py` — Nezha logs/traces as `EvidenceDoc` in GD1's document format (same doc ids and
text, so the ported BM25/prompt hit GD1's cache). `NezhaEvidenceStore` reads the whole
`rca_data` lazily per minute file; `InMemoryEvidenceStore` / `load_gd1_corpus()` hold a fixed
corpus (GD1's label-filtered one, for the parity gates only — QĐ-016).

`loaders.py` — `iter_telemetry_windows` wraps the Week 1 labelling logic in
`scripts/nezha_windows.py` and emits `TelemetryWindow` objects for `services/replayer`. Drops
non-finite metric values (the Nezha `"NaN"`-literal percentile bug, see `docs/experiment-log.md`
QĐ-009) instead of parsing them as 0.0/inf. `logs`/`spans` are intentionally left empty — no Week 2
service consumes them yet.

Tests: `tests/test_loaders.py`, `tests/test_protocols.py`, `tests/test_evidence.py`.
