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

-- name: FindMatchNaturalKeyByBaseAndScheduledAt :one
-- A rematch (same pair, arm, event) is a different real-world match; a
-- replay of the same submission is not. scheduled_at disambiguates them:
-- an identical timestamp under the same base key is treated as the same
-- match being resubmitted, reusing its exact natural key so the later
-- upsert updates in place instead of minting a new sequence-suffixed one.
select natural_key
from matches
where (natural_key = $1 or natural_key like $2) and scheduled_at = $3;

-- name: UpsertResultMatch :one
insert into matches (natural_key, label, arm, weight_class, scheduled_at, event_id, status)
values ($1, $2, $3, $4, $5, $6, $7)
on conflict (natural_key) do update
set label = excluded.label, arm = excluded.arm, weight_class = excluded.weight_class,
    scheduled_at = excluded.scheduled_at, event_id = excluded.event_id, status = excluded.status
returning id;

-- name: UpsertMatchVideo :exec
insert into match_videos (match_id, youtube_video_id)
values ($1, $2)
on conflict (match_id, youtube_video_id) do nothing;

-- name: UpsertMatchCompetitorOutcome :exec
insert into match_competitors (match_id, athlete_id, score, result)
values ($1, $2, $3, $4)
on conflict (match_id, athlete_id) do update
set score = excluded.score, result = excluded.result;
