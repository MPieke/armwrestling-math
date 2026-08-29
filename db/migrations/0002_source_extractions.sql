create table source_extractions (
    id             bigserial primary key,
    source_id      bigint not null references sources(id) on delete restrict,
    match_id       bigint not null references matches(id) on delete restrict,
    provider       text not null,
    model          text not null,
    prompt_version text not null,
    status         text not null
                   constraint source_extractions_status_check
                   check (status in ('completed', 'failed')),
    extracted_at   timestamptz not null,
    raw_response   jsonb,
    usage          jsonb,
    error_message  text,
    created_at     timestamptz not null default now()
);

create unique index source_extractions_completed_dedupe_key
    on source_extractions (source_id, match_id, provider, model, prompt_version)
    where status = 'completed';

alter table claims
    add column source_extraction_id bigint
    references source_extractions(id) on delete restrict;
