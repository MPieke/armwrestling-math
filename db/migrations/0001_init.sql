create table athletes (
    id             bigserial primary key,
    canonical_name text not null,
    created_at     timestamptz not null default now(),
    constraint athletes_canonical_name_key unique (canonical_name)
);

create table ingestion_runs (
    id            bigserial primary key,
    batch_key     text not null,
    status        text not null default 'running'
                    constraint ingestion_runs_status_check
                    check (status in ('running', 'completed', 'failed')),
    started_at    timestamptz not null default now(),
    finished_at   timestamptz,
    error_message text,
    summary       jsonb
);

create table matches (
    id           bigserial primary key,
    natural_key  text not null,
    label        text,
    arm          text not null,
    scheduled_at timestamptz,
    created_at   timestamptz not null default now(),
    constraint matches_natural_key_key unique (natural_key)
);

create table match_competitors (
    match_id   bigint not null references matches(id) on delete cascade,
    athlete_id bigint not null references athletes(id) on delete restrict,
    primary key (match_id, athlete_id)
);

create table sources (
    id            bigserial primary key,
    source_type   text not null,
    external_id   text not null,
    url           text not null,
    title         text,
    published_at  timestamptz,
    raw_payload   jsonb not null default '{}',
    created_at    timestamptz not null default now(),
    constraint sources_source_type_external_id_key unique (source_type, external_id)
);

create table claims (
    id                bigserial primary key,
    source_id         bigint not null references sources(id) on delete restrict,
    match_id          bigint not null references matches(id) on delete restrict,
    claim_text        text not null,
    timestamp_seconds integer,
    speaker           text,
    confidence        text,
    relevance         text,
    observed_at       timestamptz,
    extracted_at      timestamptz not null,
    extraction_model  text,
    raw_payload       jsonb not null default '{}',
    created_at        timestamptz not null default now()
);

create unique index claims_dedupe_key
    on claims (source_id, coalesce(timestamp_seconds, -1), claim_text);

create table claim_subjects (
    claim_id   bigint not null references claims(id) on delete cascade,
    athlete_id bigint not null references athletes(id) on delete restrict,
    primary key (claim_id, athlete_id)
);
