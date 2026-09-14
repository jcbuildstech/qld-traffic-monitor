from flask import Flask, jsonify

from storage.postgres_storage import connect_database


app = Flask(__name__)


@app.get("/")
def latest_crash():
    connection = connect_database()

    try:
        with connection.cursor() as cursor:
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

            row = cursor.fetchone()

        if row is None:
            return jsonify({"message": "No crash events found"}), 404

        return jsonify(row)

    finally:
        connection.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
