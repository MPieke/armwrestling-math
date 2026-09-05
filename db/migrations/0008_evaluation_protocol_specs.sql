alter table eval_protocols
add column spec jsonb not null default '{}';
