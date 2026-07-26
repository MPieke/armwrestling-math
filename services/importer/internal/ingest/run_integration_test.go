//go:build integration

package ingest

import (
	"context"
	"encoding/json"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

const integrationDatabaseName = "armwrestling_math_test"

func TestRunPersistsCompleteGraphAndIsIdempotent(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	batch := fixtureBatch(json.RawMessage(`{"source":true}`))
	t.Log("run valid fixture once to persist its complete canonical graph")
	result, err := Run(ctx, pool, batch)
	if err != nil {
		t.Fatalf("first Run() error = %v", err)
	}
	if result.Athletes != 2 || result.Sources != 1 || result.Claims != 1 {
		t.Fatalf("first Run() result = %+v, want 2 athletes, 1 source, and 1 claim", result)
	}
	assertFixturePersisted(t, ctx, pool)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed'", 1)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed' and summary @> '{\"athletes\": 2, \"sources\": 1, \"claims\": 1}'", 1)

	t.Log("run the identical fixture again to prove canonical rows and links stay idempotent")
	if _, err := Run(ctx, pool, batch); err != nil {
		t.Fatalf("second Run() error = %v", err)
	}
	assertFixturePersisted(t, ctx, pool)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed'", 2)
}

func TestRunRollsBackCanonicalWritesAndRecordsFailure(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	t.Log("inject invalid source JSON after transaction work begins")
	if _, err := Run(ctx, pool, fixtureBatch(json.RawMessage(`not-json`))); err == nil {
		t.Fatal("Run() error = nil, want invalid JSON failure")
	}
	assertCanonicalCounts(t, ctx, pool, 0, 0, 0, 0, 0, 0)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed'", 0)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'failed' and error_message is not null", 1)
}

func integrationPool(t *testing.T) (context.Context, *pgxpool.Pool) {
	t.Helper()
	databaseURL := integrationDatabaseURL(t)
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	t.Cleanup(pool.Close)
	return ctx, pool
}

func resetIntegrationSchema(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	if _, err := pool.Exec(ctx, "truncate claim_subjects, claims, sources, match_competitors, matches, athletes, ingestion_runs restart identity cascade"); err != nil {
		t.Fatalf("reset database: %v", err)
	}
	t.Log("reset dedicated integration schema to a known empty state")
}

func integrationDatabaseURL(t *testing.T) string {
	t.Helper()
	databaseURL := os.Getenv("INGEST_TEST_DATABASE_URL")
	if databaseURL == "" {
		t.Fatal("INGEST_TEST_DATABASE_URL is required for integration tests")
	}
	config, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		t.Fatalf("parse INGEST_TEST_DATABASE_URL: %v", err)
	}
	// This test truncates its schema, so a primary or developer database must
	// never be accepted merely because it was supplied in an environment variable.
	if config.ConnConfig.Database != integrationDatabaseName {
		t.Fatalf("INGEST_TEST_DATABASE_URL must target %q, got %q", integrationDatabaseName, config.ConnConfig.Database)
	}
	t.Logf("accepted dedicated integration database %q", integrationDatabaseName)
	return databaseURL
}

func fixtureBatch(raw json.RawMessage) IngestBatch {
	batch := validBatch()
	batch.BatchKey = "integration-fixture"
	batch.Match.Label = "Ermes Gasparini vs Artyom Morozov"
	scheduledAt := time.Date(2026, time.June, 15, 18, 30, 0, 0, time.UTC)
	batch.Match.ScheduledAt = &scheduledAt
	batch.Sources[0].Title = stringPointer("Fixture source")
	publishedAt := time.Date(2026, time.May, 31, 12, 0, 0, 0, time.UTC)
	batch.Sources[0].PublishedAt = &publishedAt
	batch.Sources[0].RawPayload = raw
	batch.Claims[0].TimestampSeconds = intPointerValue(42)
	batch.Claims[0].Speaker = stringPointer("Ermes Gasparini")
	batch.Claims[0].Confidence = stringPointer("high")
	batch.Claims[0].Relevance = stringPointer("high")
	observedAt := time.Date(2026, time.June, 1, 1, 2, 3, 0, time.UTC)
	batch.Claims[0].ObservedAt = &observedAt
	batch.Claims[0].ExtractionModel = stringPointer("fixture-model")
	batch.Claims[0].RawPayload = json.RawMessage(`{"claim":true}`)
	return batch
}

func assertFixturePersisted(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	assertCanonicalCounts(t, ctx, pool, 2, 1, 2, 1, 1, 1)

	var athleteNames string
	if err := pool.QueryRow(ctx, "select string_agg(canonical_name, ', ' order by canonical_name) from athletes").Scan(&athleteNames); err != nil {
		t.Fatalf("read athletes: %v", err)
	}
	if athleteNames != "Artyom Morozov, Ermes Gasparini" {
		t.Errorf("athlete names = %q, want persisted fixture names", athleteNames)
	}

	var label, arm string
	var scheduledAt time.Time
	if err := pool.QueryRow(ctx, "select label, arm, scheduled_at from matches where natural_key = $1", "2026-06:artyom-morozov:ermes-gasparini:right").Scan(&label, &arm, &scheduledAt); err != nil {
		t.Fatalf("read match: %v", err)
	}
	if label != "Ermes Gasparini vs Artyom Morozov" || arm != "right" || !scheduledAt.Equal(time.Date(2026, time.June, 15, 18, 30, 0, 0, time.UTC)) {
		t.Errorf("match = (%q, %q, %s), want fixture values", label, arm, scheduledAt)
	}

	var sourceType, externalID, url, title, rawPayload string
	var publishedAt time.Time
	if err := pool.QueryRow(ctx, "select source_type, external_id, url, title, published_at, raw_payload::text from sources").Scan(&sourceType, &externalID, &url, &title, &publishedAt, &rawPayload); err != nil {
		t.Fatalf("read source: %v", err)
	}
	if sourceType != "youtube" || externalID != "fixture" || url != "https://www.youtube.com/watch?v=fixture" || title != "Fixture source" || !publishedAt.Equal(time.Date(2026, time.May, 31, 12, 0, 0, 0, time.UTC)) || rawPayload != `{"source": true}` {
		t.Errorf("source does not match fixture: type=%q externalID=%q url=%q title=%q publishedAt=%s payload=%s", sourceType, externalID, url, title, publishedAt, rawPayload)
	}

	var claimText, speaker, confidence, relevance, extractionModel, claimPayload string
	var timestampSeconds int32
	var observedAt, extractedAt time.Time
	if err := pool.QueryRow(ctx, "select claim_text, timestamp_seconds, speaker, confidence, relevance, observed_at, extracted_at, extraction_model, raw_payload::text from claims").Scan(&claimText, &timestampSeconds, &speaker, &confidence, &relevance, &observedAt, &extractedAt, &extractionModel, &claimPayload); err != nil {
		t.Fatalf("read claim: %v", err)
	}
	if claimText != "Ermes claim" || timestampSeconds != 42 || speaker != "Ermes Gasparini" || confidence != "high" || relevance != "high" || !observedAt.Equal(time.Date(2026, time.June, 1, 1, 2, 3, 0, time.UTC)) || !extractedAt.Equal(time.Date(2026, time.June, 1, 0, 0, 0, 0, time.UTC)) || extractionModel != "fixture-model" || claimPayload != `{"claim": true}` {
		t.Errorf("claim does not match fixture: text=%q timestamp=%d speaker=%q confidence=%q relevance=%q observedAt=%s extractedAt=%s model=%q payload=%s", claimText, timestampSeconds, speaker, confidence, relevance, observedAt, extractedAt, extractionModel, claimPayload)
	}
}

func assertCanonicalCounts(t *testing.T, ctx context.Context, pool *pgxpool.Pool, athletes, matches, competitors, sources, claims, subjects int) {
	t.Helper()
	assertCount(t, ctx, pool, "athletes", athletes)
	assertCount(t, ctx, pool, "matches", matches)
	assertCount(t, ctx, pool, "match_competitors", competitors)
	assertCount(t, ctx, pool, "sources", sources)
	assertCount(t, ctx, pool, "claims", claims)
	assertCount(t, ctx, pool, "claim_subjects", subjects)
}

func assertCount(t *testing.T, ctx context.Context, pool *pgxpool.Pool, relation string, want int) {
	t.Helper()
	var got int
	if err := pool.QueryRow(ctx, "select count(*) from "+relation).Scan(&got); err != nil {
		t.Fatalf("count %s: %v", relation, err)
	}
	if got != want {
		t.Errorf("count %s = %d, want %d", relation, got, want)
		return
	}
	t.Logf("verified %s count is %d", relation, got)
}

func stringPointer(value string) *string { return &value }

func intPointerValue(value int) *int { return &value }
