-- PostgreSQL schema for the AIOps RCA Platform.
-- Transcribed verbatim from docs/Final_Thesis_Phase2/03-schemas-and-contracts.md §4.

CREATE TABLE IF NOT EXISTS run_registry (
    run_id          TEXT PRIMARY KEY,
    config_yaml     TEXT NOT NULL,
    git_commit      TEXT NOT NULL,
    split           TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',  -- running|done|failed
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id     TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES run_registry(run_id),
    alert_ids       JSONB NOT NULL,
    services        JSONB NOT NULL,
    start_ts        TIMESTAMPTZ NOT NULL,
    end_ts          TIMESTAMPTZ NOT NULL,
    grouping_reason JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incidents_run ON incidents(run_id, start_ts);

CREATE TABLE IF NOT EXISTS diagnostic_reports (
    incident_id      TEXT PRIMARY KEY REFERENCES incidents(incident_id),
    run_id           TEXT NOT NULL,
    report           JSONB NOT NULL,        -- full DiagnosticReport
    schema_version   TEXT NOT NULL,
    valid            BOOLEAN NOT NULL,
    validation_error TEXT,
    llm_backend      TEXT,
    e2e_latency_ms   REAL,
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS diagnostic_rejected (
    id              BIGSERIAL PRIMARY KEY,
    incident_id     TEXT,
    run_id          TEXT,
    raw_output      TEXT,
    reject_reason   TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
