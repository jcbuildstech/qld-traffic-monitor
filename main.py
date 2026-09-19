from datetime import datetime, timezone

from flask import Flask, render_template

from storage.postgres_storage import connect_database


app = Flask(__name__)


def format_age(seconds):
    if seconds is None:
        return "No data yet"

    if seconds < 60:
        return f"{seconds} seconds ago"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago"


@app.get("/case-study")
def case_study():
    return render_template("case_study.html")


@app.get("/")
def dashboard():
    connection = connect_database()

    try:
        with connection.cursor() as cursor:

            # Latest crash and its latest observation
            cursor.execute(
                """
                SELECT
                    e.id,
                    e.event_type,
                    e.first_seen_at,
                    o.road_name,
                    o.locality,
                    o.priority,
                    o.status,
                    o.description,
                    o.geometry_json
                FROM events e
                JOIN observations o
                    ON o.id = (
                        SELECT id
                        FROM observations
                        WHERE event_id = e.id
                        ORDER BY observed_at DESC
                        LIMIT 1
                    )
                WHERE e.event_type = 'crash'
                ORDER BY e.first_seen_at DESC
                LIMIT 1
                """
            )

            crash = cursor.fetchone()

            if crash is None:
                return "No crash events have been recorded yet.", 404

            # Latest successful worker ingest.
            # The worker updates last_seen_at every polling cycle.
            cursor.execute(
                """
                SELECT MAX(last_seen_at) AS last_ingest
                FROM events
                """
            )
            last_ingest = cursor.fetchone()["last_ingest"]

            # Number of historical observations stored.
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM observations
                """
            )
            observations_stored = cursor.fetchone()["total"]

    finally:
        connection.close()

    geometry = crash["geometry_json"]
    coordinates = geometry["coordinates"][0]

    longitude = coordinates[0]
    latitude = coordinates[1]

    now = datetime.now(timezone.utc)

    if last_ingest is None:
        seconds_since_ingest = None
        pipeline_status = "NO DATA"
        status_class = "stale"
    else:
        seconds_since_ingest = max(
            0,
            int((now - last_ingest).total_seconds())
        )

        if seconds_since_ingest < 120:
            pipeline_status = "LIVE"
            status_class = "live"
        else:
            pipeline_status = "STALE"
            status_class = "stale"

    last_ingest_text = format_age(seconds_since_ingest)

    return render_template(
        "index.html",
        crash=crash,
        latitude=latitude,
        longitude=longitude,
        pipeline_status=pipeline_status,
        status_class=status_class,
        last_ingest_text=last_ingest_text,
        observations_stored=observations_stored,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
