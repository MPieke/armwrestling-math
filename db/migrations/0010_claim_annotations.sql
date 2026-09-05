create table claim_annotations (
    id                  bigserial primary key,
    claim_id            bigint not null references claims(id) on delete cascade,
    model               text not null,
    prompt_version      text not null,
    -- Reuses transcript.Claim's existing extraction-time claim_type
    -- vocabulary (services/importer/internal/transcript/model.go) rather
    -- than inventing a second, overlapping one.
    claim_type          text not null
        constraint claim_annotations_claim_type_check
        check (claim_type in (
            'form', 'tactic', 'injury', 'endurance', 'setup',
            'opponent_comparison', 'other'
        )),
    concepts            text[] not null default '{}',
    subject_athlete_id  bigint references athletes(id),
    arm                 text
        constraint claim_annotations_arm_check
        check (arm is null or arm in ('left', 'right')),
    temporality         text not null
        constraint claim_annotations_temporality_check
        check (temporality in (
            'current_form', 'recent_context', 'historical_event', 'durable_style',
            'future_prediction', 'general_principle', 'unclear'
        )),
    certainty           text not null
        constraint claim_annotations_certainty_check
        check (certainty in (
            'observed', 'self_reported', 'analyst_interpretation',
            'community_narrative', 'unclear'
        )),
    raw_payload         jsonb not null default '{}',
    created_at          timestamptz not null default now(),
    constraint claim_annotations_claim_model_prompt_key unique (claim_id, model, prompt_version)
);

create index claim_annotations_claim_id_idx on claim_annotations (claim_id);
