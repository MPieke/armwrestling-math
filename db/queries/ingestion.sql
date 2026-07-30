-- name: CreateIngestionRun :one
insert into ingestion_runs (batch_key)
values ($1)
returning id;

-- name: CompleteIngestionRun :exec
update ingestion_runs
set status = 'completed', finished_at = now(), summary = $2
where id = $1;

-- name: FailIngestionRun :exec
update ingestion_runs
set status = 'failed', finished_at = now(), error_message = $2
where id = $1;

-- name: UpsertAthlete :one
insert into athletes (canonical_name)
values ($1)
on conflict (canonical_name) do update set canonical_name = excluded.canonical_name
returning id;

-- name: UpsertMatch :one
insert into matches (natural_key, label, arm, scheduled_at)
values ($1, $2, $3, $4)
on conflict (natural_key) do update
set label = excluded.label, arm = excluded.arm, scheduled_at = excluded.scheduled_at
returning id;

-- name: LinkMatchCompetitor :exec
insert into match_competitors (match_id, athlete_id)
values ($1, $2)
on conflict do nothing;

-- name: UpsertSource :one
insert into sources (source_type, external_id, url, title, published_at, raw_payload)
values ($1, $2, $3, $4, $5, $6)
on conflict (source_type, external_id) do update
set url = excluded.url,
    title = excluded.title,
    published_at = excluded.published_at,
    raw_payload = excluded.raw_payload
returning id;

-- name: UpsertClaim :one
insert into claims (
    source_id, match_id, claim_text, timestamp_seconds, speaker, confidence,
    relevance, observed_at, extracted_at, extraction_model, raw_payload
)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
on conflict (source_id, coalesce(timestamp_seconds, -1), claim_text) do update
set match_id = excluded.match_id,
    speaker = excluded.speaker,
    confidence = excluded.confidence,
    relevance = excluded.relevance,
    observed_at = excluded.observed_at,
    extracted_at = excluded.extracted_at,
    extraction_model = excluded.extraction_model,
    raw_payload = excluded.raw_payload
returning id;

-- name: LinkClaimSubject :exec
insert into claim_subjects (claim_id, athlete_id)
values ($1, $2)
on conflict do nothing;

-- name: GetCompletedSourceExtraction :one
select id
from source_extractions
where source_id = $1
  and match_id = $2
  and provider = $3
  and model = $4
  and prompt_version = $5
  and status = 'completed';

-- name: CreateSourceExtraction :one
insert into source_extractions (
    source_id, match_id, provider, model, prompt_version, status, extracted_at,
    raw_response, usage, error_message
)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
returning id;
