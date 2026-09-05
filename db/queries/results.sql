-- name: UpsertEvent :one
insert into events (slug, promoter, name, held_on)
values ($1, $2, $3, $4)
on conflict (slug) do update
set promoter = excluded.promoter, name = excluded.name, held_on = excluded.held_on
returning id;

-- name: CountMatchesWithNaturalKeyPrefix :one
select count(*)
from matches
where natural_key = $1 or natural_key like $2;

-- name: UpsertResultMatch :one
insert into matches (natural_key, label, arm, scheduled_at, event_id, status)
values ($1, $2, $3, $4, $5, $6)
on conflict (natural_key) do update
set label = excluded.label, arm = excluded.arm, scheduled_at = excluded.scheduled_at,
    event_id = excluded.event_id, status = excluded.status
returning id;

-- name: UpsertMatchCompetitorOutcome :exec
insert into match_competitors (match_id, athlete_id, score, result)
values ($1, $2, $3, $4)
on conflict (match_id, athlete_id) do update
set score = excluded.score, result = excluded.result;
