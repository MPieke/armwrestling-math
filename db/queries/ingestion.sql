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
    relevance, observed_at, extracted_at, extraction_model, raw_payload,
    source_extraction_id
)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
on conflict (source_id, coalesce(timestamp_seconds, -1), claim_text) do update
set match_id = excluded.match_id,
    speaker = excluded.speaker,
    confidence = excluded.confidence,
    relevance = excluded.relevance,
    observed_at = excluded.observed_at,
    extracted_at = excluded.extracted_at,
    extraction_model = excluded.extraction_model,
    raw_payload = excluded.raw_payload,
    source_extraction_id = excluded.source_extraction_id
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
on conflict (source_id, match_id, provider, model, prompt_version)
    where status = 'completed'
do update set
    extracted_at = excluded.extracted_at,
    raw_response = excluded.raw_response,
    usage = excluded.usage,
    error_message = excluded.error_message
returning id;

-- name: GetMatchByNaturalKey :one
select id, natural_key, label, arm, scheduled_at
from matches
where natural_key = $1;

-- name: ListMatchCompetitors :many
select athletes.id, athletes.canonical_name
from match_competitors
join athletes on athletes.id = match_competitors.athlete_id
where match_competitors.match_id = $1
order by athletes.canonical_name;

-- name: CompletedExtractionExists :one
select exists (
    select 1
    from source_extractions
    join sources on sources.id = source_extractions.source_id
    join matches on matches.id = source_extractions.match_id
    where matches.natural_key = $1
      and sources.source_type = $2
      and sources.external_id = $3
      and source_extractions.provider = $4
      and source_extractions.model = $5
      and source_extractions.prompt_version = $6
      and source_extractions.status = 'completed'
);
