-- 001: CTAV columns (QD-011, milestone M1) -- 03-schemas-and-contracts.md SS1.6.
-- Idempotent; applied by scripts/apply_clickhouse_migrations.py, in file-name
-- order, after init.sql. Existing rows (M0/M1 smoke runs) get the defaults.

ALTER TABLE aiops.fact_alert_evaluation
    ADD COLUMN IF NOT EXISTS raw_verdict LowCardinality(String) DEFAULT '' AFTER verdict,
    ADD COLUMN IF NOT EXISTS routing_tier UInt8 DEFAULT 0 AFTER raw_verdict,                  -- 0 = not judged, 1 = BM25, 2 = topology
    ADD COLUMN IF NOT EXISTS evidence_origin LowCardinality(String) DEFAULT 'none' AFTER routing_tier,
    ADD COLUMN IF NOT EXISTS threshold_applied Nullable(Float32) AFTER evidence_origin,
    ADD COLUMN IF NOT EXISTS downgraded_gating UInt8 DEFAULT 0 AFTER downgraded,
    ADD COLUMN IF NOT EXISTS downgraded_anchoring UInt8 DEFAULT 0 AFTER downgraded_gating;

ALTER TABLE aiops.fact_retrieval_trace
    ADD COLUMN IF NOT EXISTS origin LowCardinality(String) DEFAULT 'local' AFTER rank,
    ADD COLUMN IF NOT EXISTS graph_distance Nullable(UInt8) AFTER origin;
