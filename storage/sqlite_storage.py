#sqlite_storage.py

import sqlite3
from pathlib import Path
import json
import hashlib


DATABASE_PATH = Path(
    "/home/vscode/.local/share/accident_notification/traffic.db"
)


def connect_database(database_path=DATABASE_PATH):
    # Make sure the folder exists before SQLite tries to create the file.
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)

    # Let returned rows behave a little like dictionaries:
    # row["status"] instead of only row[0]
    connection.row_factory = sqlite3.Row

    # SQLite requires foreign-key enforcement to be enabled per connection.
    connection.execute("PRAGMA foreign_keys = ON")

   

    return connection


def initialize_database(connection):
    version = connection.execute(
        "PRAGMA user_version"
    ).fetchone()[0]

    if version == 0:
        migrate_0_to_1(connection)

    elif version > 1:
        raise RuntimeError(
            f"Database schema version {version} is newer than this program supports."
        )


def migrate_0_to_1(connection):
    with connection:

        connection.execute(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,

                UNIQUE(source, external_id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                observed_at TEXT NOT NULL,

                event_subtype TEXT,
                status TEXT,
                priority TEXT,
                description TEXT,

                road_name TEXT,
                locality TEXT,
                postcode TEXT,
                local_government_area TEXT,

                started_at TEXT,
                ended_at TEXT,
                source_updated_at TEXT,

                geometry_json TEXT,
                raw_payload_json TEXT,
                state_hash TEXT NOT NULL,

                FOREIGN KEY (event_id)
                    REFERENCES events(id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX idx_observations_event_time
            ON observations(event_id, observed_at)
            """
        )

        connection.execute("PRAGMA user_version = 1")

def upsert_event(connection, event, observed_at):
    cursor = connection.execute(
        """
        INSERT INTO events (
            source,
            external_id,
            event_type,
            first_seen_at,
            last_seen_at
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(source, external_id)
        DO UPDATE SET
            last_seen_at = excluded.last_seen_at

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
    row = connection.execute(
        """
        SELECT id
        FROM observations
        WHERE event_id = ?
        LIMIT 1
        """,
        (event_id,),
    ).fetchone()

    return row is not None



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

    row = connection.execute(
        """
        SELECT state_hash
        FROM observations
        WHERE event_id = ?
        ORDER BY observed_at DESC
        LIMIT 1
        """,
        (event_id,),
    ).fetchone()

    if row is None:
        return None

    return row["state_hash"]

def insert_observation(connection, event_id, event, observed_at):

    state_hash = calculate_state_hash(event)

    connection.execute(
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(event["geometry"]),
            json.dumps(event["raw_payload"]),
            state_hash,
        ),
    )