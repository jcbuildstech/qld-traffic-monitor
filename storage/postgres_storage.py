import hashlib
import json
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")


def connect_database():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        autocommit=True,
    )


def initialize_database(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id BIGSERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                first_seen_at TIMESTAMPTZ NOT NULL,
                last_seen_at TIMESTAMPTZ NOT NULL,

                UNIQUE(source, external_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id BIGSERIAL PRIMARY KEY,
                event_id BIGINT NOT NULL
                    REFERENCES events(id),

                observed_at TIMESTAMPTZ NOT NULL,

                event_subtype TEXT,
                status TEXT,
                priority TEXT,
                description TEXT,

                road_name TEXT,
                locality TEXT,
                postcode TEXT,
                local_government_area TEXT,

                started_at TIMESTAMPTZ,
                ended_at TIMESTAMPTZ,
                source_updated_at TIMESTAMPTZ,

                geometry_json JSONB,
                raw_payload_json JSONB,
                state_hash TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_observations_event_time
            ON observations(event_id, observed_at)
            """
        )

    connection.commit()



def has_any_events(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT EXISTS (
                SELECT 1
                FROM events
            ) AS has_events
            '''
        )

        return cursor.fetchone()["has_events"]

def upsert_event(connection, event, observed_at):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO events (
                source,
                external_id,
                event_type,
                first_seen_at,
                last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s)

            ON CONFLICT(source, external_id)
            DO UPDATE SET
                last_seen_at = EXCLUDED.last_seen_at

            RETURNING id
            """,
            (
                event["source"],
                event["external_id"],
                event["event_type"],
                observed_at,
                observed_at,
            ),
        )

        return cursor.fetchone()["id"]


def has_observation(connection, event_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM observations
            WHERE event_id = %s
            LIMIT 1
            """,
            (event_id,),
        )

        return cursor.fetchone() is not None


def calculate_state_hash(event):
    raw_payload_json = json.dumps(
        event["raw_payload"],
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        raw_payload_json.encode("utf-8")
    ).hexdigest()


def get_last_observation_hash(connection, event_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT state_hash
            FROM observations
            WHERE event_id = %s
            ORDER BY observed_at DESC
            LIMIT 1
            """,
            (event_id,),
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return row["state_hash"]


def insert_observation(connection, event_id, event, observed_at):
    state_hash = calculate_state_hash(event)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO observations (
                event_id,
                observed_at,
                event_subtype,
                status,
                priority,
                description,
                road_name,
                locality,
                postcode,
                local_government_area,
                started_at,
                ended_at,
                source_updated_at,
                geometry_json,
                raw_payload_json,
                state_hash
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                event_id,
                observed_at,
                event["event_subtype"],
                event["status"],
                event["priority"],
                event["description"],
                event["road_name"],
                event["locality"],
                event["postcode"],
                event["local_government_area"],
                event["started_at"],
                event["ended_at"],
                event["source_updated_at"],
                Jsonb(event["geometry"]),
                Jsonb(event["raw_payload"]),
                state_hash,
            ),
        )
