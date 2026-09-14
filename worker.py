#main.py

# This project is original work of Juan Camilo Delgado Vivas
# is a notification system of traffic events



import time
import requests

from datetime import datetime, timezone

from sources import qld_traffic
from notifications import ntfy
from storage.postgres_storage import (
    connect_database,
    initialize_database,
    has_any_events,
    upsert_event,
    has_observation,
    insert_observation,
    get_last_observation_hash,
    calculate_state_hash,
)


def main():

    connection = connect_database()
    initialize_database(connection)

    try:
        while True:

            try:
                current_events_data = qld_traffic.get_events()

            except requests.RequestException as error:
                print("QLDTraffic API error:", error)
                time.sleep(60)
                continue

            list_of_events = qld_traffic.list_events(
                current_events_data
            )

            baseline_mode = not has_any_events(connection)

            observed_at = datetime.now(timezone.utc).isoformat()

            events_to_notify = []

            with connection.transaction():

                for event in list_of_events:

                    event_id = upsert_event(
                        connection,
                        event,
                        observed_at
                    )

                    #print("Stored event ID:", event_id)

                    if not has_observation(connection, event_id):

                        insert_observation(
                            connection,
                            event_id,
                            event,
                            observed_at
                        )

                        print("First observation stored for event:", event_id)
                        if not baseline_mode:
                            events_to_notify.append((event, event_id))

                    else:

                        current_state_hash = calculate_state_hash(event)

                        previous_state_hash = get_last_observation_hash(
                            connection,
                            event_id
                        )

                        if current_state_hash != previous_state_hash:

                            insert_observation(
                                connection,
                                event_id,
                                event,
                                observed_at
                            )

                            #print("New observation stored for changed event:", event_id)

            for event, event_id in events_to_notify:
                ntfy.send_notification(event, event_id)
                            



            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down traffic collector.")


    finally:
        connection.close()


if __name__ == "__main__":
    main()


 