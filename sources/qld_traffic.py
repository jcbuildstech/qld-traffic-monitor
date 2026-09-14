#qld_traffic.py

# Sourcing is the first step this script calls the public QLD government public API
# and retrieves information about current and recent traffic events



import requests, json

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("QLD_TRAFFIC_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "QLD_TRAFFIC_API_KEY environment variable is not set."
    )

params = {
    "apikey": API_KEY
}


# Queries for all active events
def get_events():
    events_url = "https://api.qldtraffic.qld.gov.au/v2/events"

    response = requests.get(
        events_url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "features" not in data:
        raise ValueError(
            f"Unexpected QLDTraffic response: {data}"
        )

    return data

# Queries for the last hour events
def get_last_hour_events():
    last_hour_events_url = (
        "https://api.qldtraffic.qld.gov.au/v2/events/past-one-hour"
    )

    response = requests.get(
        last_hour_events_url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "features" not in data:
        raise ValueError(
            f"Unexpected QLDTraffic response: {data}"
        )

    return data

def list_events(data):
    list_of_events = []

    for raw_event in data['features']:
        event = normalize_event(raw_event)
        list_of_events.append(event)

    return list_of_events

# structure events according to my reporting preferences
def normalize_event(raw_event):

    properties = raw_event["properties"]
    road = properties["road_summary"]
    duration = properties["duration"]

    event = {
        "source": "qldtraffic",
        "external_id": properties["id"],
        "event_type": properties["event_type"].lower(),
        "event_subtype": properties["event_subtype"],
        "status": properties["status"].lower(),
        "priority": properties["event_priority"].lower(),
        "description": properties["description"],
        "road_name": road["road_name"],
        "locality": road["locality"],
        "postcode": road["postcode"],
        "local_government_area": road["local_government_area"],
        "started_at": duration["start"],
        "ended_at": duration["end"],
        "source_updated_at": properties["last_updated"],
        "geometry": raw_event["geometry"],
        "raw_payload": raw_event
    }

    return event