from __future__ import annotations

import json
import os
from typing import Any

import psycopg


POSTGRES_DSN = os.getenv("EVENTS_POSTGRES_DSN", "").strip()


def write_raw_event(event: dict[str, Any]) -> None:
    if not POSTGRES_DSN:
        raise RuntimeError("EVENTS_POSTGRES_DSN is empty")

    sql = """
    INSERT INTO analytics_raw_events
    (event_id, event_time, event_name, user_id, session_id, source, status, payload)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """

    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    str(event["event_id"]),
                    event["event_time"],
                    event["event_name"],
                    event["user_id"],
                    event["session_id"],
                    event["source"],
                    event["status"],
                    json.dumps(event["payload"], ensure_ascii=False),
                ),
            )
        conn.commit()