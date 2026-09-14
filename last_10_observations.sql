SELECT
    id,
    event_id,
    locality,
    postcode,
    source_updated_at,
    observed_at
FROM observations
ORDER BY observed_at DESC
LIMIT 10;