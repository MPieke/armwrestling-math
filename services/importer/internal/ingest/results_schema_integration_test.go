//go:build integration

package ingest

import (
	"testing"
)

func TestEventAndOutcomeSchema(t *testing.T) {
	ctx, pool := integrationPool(t)

	var eventsExists bool
	if err := pool.QueryRow(ctx, "select to_regclass('public.events') is not null").Scan(&eventsExists); err != nil {
		t.Fatalf("check events relation: %v", err)
	}
	if !eventsExists {
		t.Fatal("events table does not exist")
	}

	expectedMatchColumns := map[string]string{
		"event_id": "NO",
		"status":   "NO",
	}
	for column, nullable := range expectedMatchColumns {
		assertColumnNullable(t, ctx, pool, "matches", column, nullable)
	}
	assertColumnNullable(t, ctx, pool, "matches", "scheduled_at", "NO")

	expectedCompetitorColumns := map[string]string{
		"score":  "YES",
		"result": "YES",
	}
	for column, nullable := range expectedCompetitorColumns {
		assertColumnNullable(t, ctx, pool, "match_competitors", column, nullable)
	}
}

func TestMatchStatusConstraintRejectsUnrecognizedValue(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, `
		with e as (insert into events (slug, promoter, name, held_on) values ('e', 'p', 'n', '2026-01-01') returning id)
		insert into matches (natural_key, arm, scheduled_at, event_id, status)
		select 'k', 'right', now(), e.id, 'not-a-status' from e
	`)
}

func TestMatchCompetitorResultConstraintRejectsUnrecognizedValue(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, `
		update match_competitors set result = 'not-a-result'
		where match_id = (select id from matches limit 1)
	`)
}

func TestMatchCompetitorScoreConstraintRejectsNegativeValue(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, `
		update match_competitors set score = -1
		where match_id = (select id from matches limit 1)
	`)
}
