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
		"event_id":     "NO",
		"status":       "NO",
		"weight_class": "NO",
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

func TestMatchVideosSchemaUsesMatchAndVideoAsItsPrimaryKey(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	var exists bool
	if err := pool.QueryRow(ctx, "select to_regclass('public.match_videos') is not null").Scan(&exists); err != nil {
		t.Fatalf("check match_videos relation: %v", err)
	}
	if !exists {
		t.Fatal("match_videos table does not exist")
	}

	seedExistingMatch(t, ctx, pool)
	var matchID int64
	if err := pool.QueryRow(ctx, "select id from matches limit 1").Scan(&matchID); err != nil {
		t.Fatalf("read seeded match id: %v", err)
	}
	if _, err := pool.Exec(ctx, "insert into match_videos (match_id, youtube_video_id) values ($1, 'video-1')", matchID); err != nil {
		t.Fatalf("insert match video: %v", err)
	}
	if _, err := pool.Exec(ctx, "insert into match_videos (match_id, youtube_video_id) values ($1, 'video-1')", matchID); err == nil {
		t.Fatal("duplicate match video succeeded, want primary-key violation")
	}
}

func TestMatchStatusConstraintRejectsUnrecognizedValue(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, `
		with e as (insert into events (slug, promoter, name, held_on) values ('e', 'p', 'n', '2026-01-01') returning id)
		insert into matches (natural_key, arm, weight_class, scheduled_at, event_id, status)
		select 'k', 'right', '105 kg', now(), e.id, 'not-a-status' from e
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
