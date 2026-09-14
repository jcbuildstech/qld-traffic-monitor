from flask import Flask, render_template

from storage.postgres_storage import connect_database


app = Flask(__name__)


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

            # Total crashes since monitoring began
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM events
                WHERE event_type = 'crash'
                """
            )
            total_crashes = cursor.fetchone()["total"]

            # Crashes detected during the last 24 hours
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM events
                WHERE event_type = 'crash'
                  AND first_seen_at >= NOW() - INTERVAL '24 hours'
                """
            )
            crashes_24h = cursor.fetchone()["total"]

            # Average time between crash detections
            cursor.execute(
                """
                WITH crash_times AS (
                    SELECT
                        first_seen_at,
                        LAG(first_seen_at) OVER (
                            ORDER BY first_seen_at
                        ) AS previous_seen_at
                    FROM events
                    WHERE event_type = 'crash'
                )
                SELECT
                    AVG(
                        EXTRACT(
                            EPOCH FROM (
                                first_seen_at - previous_seen_at
                            )
                        ) / 60
                    ) AS average_minutes
                FROM crash_times
                WHERE previous_seen_at IS NOT NULL
                """
            )

            average = cursor.fetchone()["average_minutes"]

    finally:
        connection.close()

    geometry = crash["geometry_json"]
    coordinates = geometry["coordinates"][0]

    longitude = coordinates[0]
    latitude = coordinates[1]

    average_minutes = (
        round(float(average), 1)
        if average is not None
        else "N/A"
    )

    return render_template(
        "index.html",
        crash=crash,
        latitude=latitude,
        longitude=longitude,
        crashes_24h=crashes_24h,
        average_minutes=average_minutes,
        total_crashes=total_crashes,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
