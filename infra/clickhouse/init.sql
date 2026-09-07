-- ClickHouse schema for the AIOps RCA Platform.
-- Transcribed verbatim from docs/Final_Thesis_Phase2/03-schemas-and-contracts.md §3.
-- Changing a column here after data exists must go through a migration script
-- in infra/clickhouse/migrations/, not an edit of this file in place
-- (docs/Final_Thesis_Phase2/03-schemas-and-contracts.md §7).

CREATE DATABASE IF NOT EXISTS aiops;

USE aiops;

-- 3.1 fact_alert_evaluation: one row per window per run.
CREATE TABLE IF NOT EXISTS fact_alert_evaluation
(
    run_id                LowCardinality(String),
    window_id             String,
    service               LowCardinality(String),
    window_ts             DateTime64(3, 'UTC'),

    anomaly_score         Float32,
    candidate_source      LowCardinality(String),   -- metric | rescue | none
    rescue_score          Nullable(Float32),
    rescue_lambda_log     Nullable(Float32),
    rescue_phi_topo       Nullable(Float32),
    rescue_delta_time     Nullable(Float32),

    retrieval_strategy    LowCardinality(String),
    retrieval_latency_ms  Float32,
    context_event_count   UInt16,
    context_tokens        UInt32,
    retrieval_truncated   UInt8,

    verdict               LowCardinality(String),   -- TRUE_ALERT | FALSE_POSITIVE | UNCERTAIN | NONE
    confidence            Nullable(Float32),
    judge_backend         LowCardinality(String),
    llm_latency_ms        Nullable(Float32),
    cache_hit             UInt8,
    downgraded            UInt8,

    label_is_fault        UInt8,
    label_fault_type      LowCardinality(String),
    label_root_cause      LowCardinality(String),

    created_at            DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (run_id, window_ts, window_id)
PARTITION BY run_id;

-- 3.2 fact_retrieval_trace: one row per retrieved context event, used to score
-- context precision.
CREATE TABLE IF NOT EXISTS fact_retrieval_trace
(
    run_id      LowCardinality(String),
    window_id   String,
    event_id    String,
    modality    LowCardinality(String),
    service     LowCardinality(String),
    event_ts    DateTime64(3, 'UTC'),
    score       Float32,
    rank        UInt16,
    debug_json  String,
    created_at  DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (run_id, window_id, rank)
PARTITION BY run_id
TTL created_at + INTERVAL 180 DAY;
