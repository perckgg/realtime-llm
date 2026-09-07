# services/detector

Implements `Detector` (`docs/Final_Thesis_Phase2/01-architecture-design.md` §5.2) as
`IsolationForestDetector` (`isolation_forest.py`, threshold 0.85), ported from
`legacy/src/detectors/isolation_forest_detector.py` per "bọc, đừng viết lại"
(`07-setup-guide.md` §8.1). `candidates.py::build_alert_candidate` turns a scored window into an
`AlertCandidate(source="metric")`, or `None` if it isn't a candidate.

**Rolling buffer adaptation (`docs/experiment-log.md` QĐ-009).** GĐ1's feature formulas
(mean/std/min/max/last/delta per metric) were computed over several raw samples per window;
GĐ2's `TelemetryWindow` (QĐ-003) is exactly one 60s sample. To keep the formulas meaningful without
rewriting them, each service keeps a small rolling buffer (`_ServiceBuffer`, default
`buffer_size=2`) of its most recent snapshots, and the formulas run over that buffer. Consequence:
a service's very first scored window has a degenerate one-point history, so `is_candidate()` never
promotes during that cold start regardless of score — see the cold-start tests in
`tests/test_isolation_forest_detector.py`.

**Not implemented here: the Rescue Score gate** (`01` §6.2's "else" branch). Deferred per QĐ-009 —
`TelemetryWindow.logs`/`.spans` aren't populated yet, and the roadmap places the Rescue Score
ablation in Week 8 (Month 2), not Week 2. This detector only ever emits
`AlertCandidate(source="metric")`.

Tests: `tests/test_isolation_forest_detector.py` (pure synthetic `TelemetryWindow`s, no dataset
needed).
