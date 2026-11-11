# services/detector

Implements `Detector` (`docs/Final_Thesis_Phase2/01-architecture-design.md` §5.2) as
`IsolationForestDetector` (`isolation_forest.py`, threshold 0.85), ported from
`legacy/src/detectors/isolation_forest_detector.py` per "bọc, đừng viết lại"
(`07-setup-guide.md` §8.1). `candidates.py::build_alert_candidate` turns a scored window into an
`AlertCandidate(source="metric")` (or `source="rescue"`, below), or `None` if it isn't a candidate.

**Rolling buffer adaptation (`docs/experiment-log.md` QĐ-009).** GĐ1's feature formulas
(mean/std/min/max/last/delta per metric) were computed over several raw samples per window;
GĐ2's `TelemetryWindow` (QĐ-003) is exactly one 60s sample. To keep the formulas meaningful without
rewriting them, each service keeps a small rolling buffer (`_ServiceBuffer`, default
`buffer_size=2`) of its most recent snapshots, and the formulas run over that buffer. Consequence:
a service's very first scored window has a degenerate one-point history, so `is_candidate()` never
promotes during that cold start regardless of score — see the cold-start tests in
`tests/test_isolation_forest_detector.py`.

**Rescue Score gate, C5** (`01` §6.2's "else" branch; M7, QĐ-033): pure functions in `rescue.py`
(`lambda_log`, `phi_topo`, `delta_time`, `active_alerts`, `RescueParams`, `rescue_score`, `is_rescued`,
`eta_grid`). The components are precomputed offline for every window by
`scripts/build_rescue_features.py` (error logs from the evidence store, alert set A = the pipeline's own
CTAV alerts), not inside the streaming detector. `build_alert_candidate(..., source="rescue",
rescue_score=..., rescue_components=...)` emits the rescued candidate; the runner judges a listed set of
rescued windows via `rescue: {windows: <csv>}`. On `val` C5 adds at most 2 TP (QĐ-033).

Tests: `tests/test_isolation_forest_detector.py` (pure synthetic `TelemetryWindow`s, no dataset
needed), `tests/test_rescue.py`.
