SELECT *
FROM events
GROUP BY event_type
ORDER BY last_seen_at DESC
LIMIT 10;