CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS fault_events (
    fault_id TEXT PRIMARY KEY,
    fault_type TEXT NOT NULL,
    service_id TEXT NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'online-boutique',
    target_kind TEXT NOT NULL DEFAULT 'service',
    pod_id TEXT,
    severity TEXT NOT NULL DEFAULT 'ERROR',
    expected_symptom TEXT,
    status TEXT NOT NULL,
    planned_start_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    cooldown_seconds INTEGER,
    selector JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metric_samples (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    service_id TEXT NOT NULL,
    pod_id TEXT,
    node_id TEXT,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    source TEXT NOT NULL DEFAULT 'kubernetes',
    fault_id TEXT,
    labels JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS log_events (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    service_id TEXT NOT NULL,
    pod_id TEXT,
    node_id TEXT,
    severity TEXT NOT NULL DEFAULT 'INFO',
    event_type TEXT NOT NULL DEFAULT 'log',
    message TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'kubernetes_event',
    fault_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS trace_spans (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    trace_id TEXT,
    span_id TEXT,
    parent_span_id TEXT,
    service_id TEXT NOT NULL,
    pod_id TEXT,
    node_id TEXT,
    operation_name TEXT,
    duration_ms DOUBLE PRECISION,
    status_code TEXT,
    source TEXT NOT NULL DEFAULT 'otel',
    fault_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS context_documents (
    doc_id TEXT PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    service_id TEXT NOT NULL,
    pod_id TEXT,
    node_id TEXT,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    fault_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(512)
);

CREATE TABLE IF NOT EXISTS metric_windows (
    window_id TEXT PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    watermark_time TIMESTAMPTZ NOT NULL,
    service_id TEXT NOT NULL,
    pod_id TEXT,
    node_id TEXT,
    features JSONB NOT NULL,
    label TEXT NOT NULL DEFAULT 'normal',
    fault_type TEXT NOT NULL DEFAULT 'none',
    fault_id TEXT,
    source_stream TEXT NOT NULL DEFAULT 'ob:metrics',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    window_id TEXT NOT NULL,
    event_time TIMESTAMPTZ,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    service_id TEXT NOT NULL,
    pod_id TEXT,
    node_id TEXT,
    fault_type TEXT NOT NULL DEFAULT 'none',
    fault_id TEXT,
    ground_truth TEXT NOT NULL,
    is_candidate BOOLEAN NOT NULL,
    context_rescue_checked BOOLEAN NOT NULL DEFAULT false,
    context_rescue_promoted BOOLEAN NOT NULL DEFAULT false,
    final_decision TEXT NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_fault_events_status ON fault_events (status);
CREATE INDEX IF NOT EXISTS idx_fault_events_time ON fault_events (started_at, ended_at);
CREATE INDEX IF NOT EXISTS idx_metric_samples_time ON metric_samples (event_time);
CREATE INDEX IF NOT EXISTS idx_metric_samples_service_time ON metric_samples (service_id, event_time);
CREATE INDEX IF NOT EXISTS idx_log_events_time ON log_events (event_time);
CREATE INDEX IF NOT EXISTS idx_log_events_service_time ON log_events (service_id, event_time);
CREATE INDEX IF NOT EXISTS idx_trace_spans_time ON trace_spans (event_time);
CREATE INDEX IF NOT EXISTS idx_context_documents_time ON context_documents (event_time);
CREATE INDEX IF NOT EXISTS idx_context_documents_service_time ON context_documents (service_id, event_time);
CREATE INDEX IF NOT EXISTS idx_metric_windows_service_time ON metric_windows (service_id, window_start, window_end);
