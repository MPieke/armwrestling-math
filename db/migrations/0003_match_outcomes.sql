create table events (
    id         bigserial primary key,
    slug       text not null,
    promoter   text not null,
    name       text not null,
    held_on    date not null,
    created_at timestamptz not null default now(),
    constraint events_slug_key unique (slug)
);

alter table matches
    add column event_id bigint not null references events(id),
    add column status text not null
        constraint matches_status_check
        check (status in ('scheduled', 'completed', 'dq', 'no_contest'));

alter table matches
    alter column scheduled_at set not null;

alter table match_competitors
    add column score  integer
        constraint match_competitors_score_check
        check (score >= 0),
    add column result text
        constraint match_competitors_result_check
        check (result in ('win', 'loss', 'no_contest'));
