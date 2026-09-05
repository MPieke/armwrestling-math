-- name: ListClaimsMissingAnnotation :many
select c.id, c.claim_text, c.match_id
from claims c
where not exists (
    select 1 from claim_annotations ca
    where ca.claim_id = c.id and ca.model = $1 and ca.prompt_version = $2
)
order by c.id;

-- name: UpsertClaimAnnotation :one
insert into claim_annotations (
    claim_id, model, prompt_version, claim_type, concepts, subject_athlete_id,
    arm, temporality, certainty, raw_payload
)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
on conflict (claim_id, model, prompt_version) do update
set claim_type = excluded.claim_type,
    concepts = excluded.concepts,
    subject_athlete_id = excluded.subject_athlete_id,
    arm = excluded.arm,
    temporality = excluded.temporality,
    certainty = excluded.certainty,
    raw_payload = excluded.raw_payload
returning id;

-- name: CountClaimAnnotations :one
select count(*) from claim_annotations where model = $1 and prompt_version = $2;
