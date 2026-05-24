CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.bot_events_raw
(
    ingest_time      DateTime DEFAULT now(),
    idempotency_key  String,
    event_id         UUID,
    event_time       DateTime,
    event_name       LowCardinality(String),
    user_id          String,
    session_id       String,
    source           LowCardinality(String),
    status           LowCardinality(String),
    payload          String
)
ENGINE = ReplacingMergeTree(ingest_time)
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_time, event_id);

CREATE TABLE IF NOT EXISTS analytics.bot_events_enriched
(
    event_date         Date,
    event_hour         DateTime,
    event_id           UUID,
    event_time         DateTime,
    event_name         LowCardinality(String),
    user_id            String,
    session_id         String,
    source             LowCardinality(String),
    status             LowCardinality(String),

    topic              String,
    is_correct         UInt8,
    response_time_sec  Float64,

    payload            String
)
ENGINE = ReplacingMergeTree(event_time)
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_date, event_name, user_id, event_id);
