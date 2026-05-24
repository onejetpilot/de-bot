from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import psycopg
from clickhouse_driver import Client
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator


PG_DSN = os.getenv("EVENTS_POSTGRES_DSN", "postgresql://events_user:events_pass@postgres:5432/events")
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CH_DB = os.getenv("CLICKHOUSE_DB", "analytics")
CH_USER = os.getenv("CLICKHOUSE_USER", "analytics_user")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "analytics_pass")

WATERMARK_VAR = "events_pg_last_id"


def load_batch() -> None:
    last_id = int(Variable.get(WATERMARK_VAR, default_var="0"))

    with psycopg.connect(PG_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, event_id, event_time, event_name, user_id, session_id, source, status, payload
                FROM analytics_raw_events
                WHERE id > %s
                ORDER BY id
                LIMIT 5000
                """,
                (last_id,),
            )
            rows = cur.fetchall()

    if not rows:
        return

    ch = Client(
        host=CH_HOST,
        port=CH_PORT,
        database=CH_DB,
        user=CH_USER,
        password=CH_PASSWORD,
    )

    raw_data = []
    enriched_data = []

    max_id = last_id
    for r in rows:
        pg_id, event_id, event_time, event_name, user_id, session_id, source, status, payload = r
        max_id = max(max_id, pg_id)

        payload_str = json.dumps(payload, ensure_ascii=False)
        idempotency_key = f"{pg_id}:{event_id}"

        raw_data.append(
            (
                idempotency_key,
                str(event_id),
                event_time,
                event_name,
                user_id,
                session_id,
                source,
                status,
                payload_str,
            )
        )

        topic = str(payload.get("topic", "")) if isinstance(payload, dict) else ""
        is_correct = 1 if isinstance(payload, dict) and bool(payload.get("is_correct", False)) else 0
        response_time_sec = float(payload.get("response_time_sec", 0.0)) if isinstance(payload, dict) else 0.0

        enriched_data.append(
            (
                event_time.date(),
                event_time.replace(minute=0, second=0, microsecond=0),
                str(event_id),
                event_time,
                event_name,
                user_id,
                session_id,
                source,
                status,
                topic,
                is_correct,
                response_time_sec,
                payload_str,
            )
        )

    ch.execute(
        """
        INSERT INTO analytics.bot_events_raw
        (idempotency_key, event_id, event_time, event_name, user_id, session_id, source, status, payload)
        VALUES
        """,
        raw_data,
    )

    ch.execute(
        """
        INSERT INTO analytics.bot_events_enriched
        (event_date, event_hour, event_id, event_time, event_name, user_id, session_id, source, status,
         topic, is_correct, response_time_sec, payload)
        VALUES
        """,
        enriched_data,
    )

    Variable.set(WATERMARK_VAR, str(max_id))


default_args = {
    "owner": "analytics",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="load_events_to_clickhouse",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="*/2 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["events", "clickhouse", "etl"],
) as dag:
    PythonOperator(
        task_id="load_batch",
        python_callable=load_batch,
    )
