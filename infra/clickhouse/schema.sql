-- ClickHouse schema for time-series latency and cost metrics
-- Run: clickhouse-client < infra/clickhouse/schema.sql

CREATE DATABASE IF NOT EXISTS lucenteval;

USE lucenteval;

-- Per-prompt latency/cost time-series
CREATE TABLE IF NOT EXISTS prompt_metrics (
    run_id        UUID,
    prompt_id     UUID,
    account_id    UUID,
    corpus_version String,
    captured_at   DateTime,
    latency_ms    UInt32,
    input_tokens  UInt32,
    output_tokens UInt32,
    cost_usd      Float64,
    model         String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(captured_at)
ORDER BY (account_id, run_id, captured_at)
TTL captured_at + INTERVAL 2 YEAR;

-- Run-level aggregate metrics
CREATE TABLE IF NOT EXISTS run_metrics (
    run_id           UUID,
    account_id       UUID,
    corpus_version   String,
    completed_at     DateTime,
    composite_score  Float32,
    score_adversarial Float32,
    score_tool_misuse Float32,
    score_hallucination Float32,
    score_recovery   Float32,
    score_latency    Float32,
    score_cost       Float32,
    latency_p50      Float32,
    latency_p95      Float32,
    latency_p99      Float32,
    prompt_count     UInt32,
    weights_version  String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(completed_at)
ORDER BY (account_id, completed_at)
TTL completed_at + INTERVAL 2 YEAR;

-- Materialized view: p95 latency per account per day
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_latency_p95
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (account_id, day)
AS SELECT
    account_id,
    toDate(captured_at) AS day,
    quantileState(0.95)(latency_ms) AS latency_p95_state
FROM prompt_metrics
GROUP BY account_id, day;
