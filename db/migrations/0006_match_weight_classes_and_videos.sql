alter table matches
    add column weight_class text not null;

create table match_videos (
    match_id         bigint not null references matches(id) on delete cascade,
    youtube_video_id text not null,
    primary key (match_id, youtube_video_id)
);

drop view v_completed_matches;

create view v_completed_matches as
select
    m.id as match_id,
    m.event_id,
    m.scheduled_at,
    m.arm,
    m.weight_class,
    mc_a.athlete_id as athlete_a_id,
    mc_b.athlete_id as athlete_b_id,
    mc_a.result as result_a
from matches m
join match_competitors mc_a on mc_a.match_id = m.id
join match_competitors mc_b on mc_b.match_id = m.id and mc_b.athlete_id > mc_a.athlete_id
where m.status = 'completed';
