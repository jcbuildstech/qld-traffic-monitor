#ntfy.py

import requests


def send_notification(event, event_id):

    my_topic = "qld_traffic_juan2026"

    message = (
        f"Event ID: {event_id}\n"
        f"{event['event_type'].title()} - {event['road_name']}\n"
        f"{event['locality']}\n"
        f"Priority: {event['priority']}"
    )

    try:
        response = requests.post(
            f"https://ntfy.sh/{my_topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": "New QLD Traffic Event"
            },
            timeout=10
        )

        response.raise_for_status()

        print(
            "NOTIFICATION SENT:",
            event_id,
            "-",
            event["event_type"],
            "-",
            event["road_name"],
            "-",
            event["locality"]
        )

    except requests.RequestException as error:
        print("ntfy notification error:", error)