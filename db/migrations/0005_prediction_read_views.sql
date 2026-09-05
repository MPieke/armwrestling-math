-- Read-only boundary for services/prediction (Python). It queries this view
-- only, never the base tables, so what counts as a usable completed match
-- has exactly one definition and the base tables can change underneath
-- without breaking the prediction service.
create view v_completed_matches as
select
    m.id as match_id,
    m.event_id,
    m.scheduled_at,
    m.arm,
    mc_a.athlete_id as athlete_a_id,
    mc_b.athlete_id as athlete_b_id,
    mc_a.result as result_a
from matches m
join match_competitors mc_a on mc_a.match_id = m.id
join match_competitors mc_b on mc_b.match_id = m.id and mc_b.athlete_id > mc_a.athlete_id
where m.status = 'completed';
