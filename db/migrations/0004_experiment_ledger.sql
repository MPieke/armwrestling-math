create table eval_protocols (
    id         bigserial primary key,
    name       text not null,
    kind       text not null
        constraint eval_protocols_kind_check
        check (kind in ('rolling_origin', 'lockbox_retrospective', 'lockbox_prospective')),
    created_at timestamptz not null default now(),
    constraint eval_protocols_name_key unique (name)
);

-- Fold membership is materialized here at creation time, never re-derived
-- from a rule (e.g. "matches after date X"): a rule-based definition would
-- silently change as new matches are ingested, breaking comparability
-- between runs scored against "the same" protocol months apart. A lockbox
-- protocol is represented the same way, distinguished only by
-- eval_protocols.kind, typically with a single fold (fold_index = 0).
create table eval_folds (
    protocol_id     bigint not null references eval_protocols(id) on delete cascade,
    fold_index      integer not null,
    train_match_ids bigint[] not null,
    test_match_ids  bigint[] not null,
    primary key (protocol_id, fold_index)
);

create table experiment_runs (
    id            bigserial primary key,
    git_sha       text not null,
    git_dirty     boolean not null,
    protocol_id   bigint not null references eval_protocols(id),
    feature_spec  jsonb not null default '{}',
    model_family  text not null,
    hyperparams   jsonb not null default '{}',
    seed          integer not null,
    parent_run_id bigint references experiment_runs(id),
    hypothesis    text,
    status        text not null
        constraint experiment_runs_status_check
        check (status in ('running', 'completed', 'failed')),
    metrics       jsonb,
    error_message text,
    started_at    timestamptz not null default now(),
    finished_at   timestamptz
);

create table run_predictions (
    run_id     bigint not null references experiment_runs(id) on delete cascade,
    match_id   bigint not null references matches(id),
    athlete_id bigint not null references athletes(id),
    p_win      double precision not null
        constraint run_predictions_p_win_check
        check (p_win >= 0 and p_win <= 1),
    primary key (run_id, match_id, athlete_id)
);

create table run_models (
    run_id bigint primary key references experiment_runs(id) on delete cascade,
    params jsonb not null default '{}'
);
