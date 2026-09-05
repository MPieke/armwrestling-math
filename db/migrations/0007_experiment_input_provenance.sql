create table feature_specs (
    id                  bigserial primary key,
    name                text not null,
    version             integer not null check (version > 0),
    representation_kind text not null check (representation_kind in ('rating', 'tabular', 'sequence', 'graph', 'prompt')),
    definition          jsonb not null,
    definition_sha256   text not null check (definition_sha256 ~ '^[0-9a-f]{64}$'),
    created_at          timestamptz not null default now(),
    unique (name, version),
    unique (definition_sha256)
);

insert into feature_specs (name, version, representation_kind, definition, definition_sha256)
values ('outcomes_elo', 1, 'rating', '{"inputs":["v_completed_matches"],"missingness":"not_applicable","version":1}',
        '563411b8b192ab973286251471af59301feab4d23b388985e9e5f8b7b0b85f95');

alter table experiment_runs add column feature_spec_id bigint references feature_specs(id);
update experiment_runs set feature_spec_id = (select id from feature_specs where name = 'outcomes_elo' and version = 1);
alter table experiment_runs alter column feature_spec_id set not null;

create table run_input_manifests (
    run_id          bigint primary key references experiment_runs(id) on delete cascade,
    cutoff_policy   jsonb not null,
    data_summary    jsonb not null,
    manifest_sha256 text not null check (manifest_sha256 ~ '^[0-9a-f]{64}$')
);

create table run_feature_rows (
    run_id         bigint not null references experiment_runs(id) on delete cascade,
    fold_index     integer not null,
    match_id       bigint not null references matches(id),
    role           text not null check (role in ('train', 'test')),
    payload        jsonb not null,
    payload_sha256 text not null check (payload_sha256 ~ '^[0-9a-f]{64}$'),
    primary key (run_id, fold_index, match_id, role)
);

create function reject_completed_run_input_mutation() returns trigger language plpgsql as $$
declare input_run_id bigint := coalesce(new.run_id, old.run_id);
begin
    if exists (select 1 from experiment_runs where id = input_run_id and status = 'completed') then
        raise exception 'completed run inputs are immutable';
    end if;
    return coalesce(new, old);
end;
$$;

create trigger run_input_manifests_immutable
before insert or update or delete on run_input_manifests
for each row execute function reject_completed_run_input_mutation();

create trigger run_feature_rows_immutable
before insert or update or delete on run_feature_rows
for each row execute function reject_completed_run_input_mutation();
