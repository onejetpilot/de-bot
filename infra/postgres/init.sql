CREATE TABLE IF NOT EXISTS analytics_raw_events (
    id BIGSERIAL PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id UUID NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    event_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_analytics_raw_events_event_id
    ON analytics_raw_events(event_id);

CREATE INDEX IF NOT EXISTS ix_analytics_raw_events_event_time
    ON analytics_raw_events(event_time DESC);

CREATE INDEX IF NOT EXISTS ix_analytics_raw_events_event_name
    ON analytics_raw_events(event_name);
