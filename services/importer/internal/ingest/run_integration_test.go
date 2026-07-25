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

func TestRunIsIdempotentAndRecordsTransactionalFailure(t *testing.T) {
	databaseURL := integrationDatabaseURL(t)
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	defer pool.Close()
	if _, err := pool.Exec(ctx, "truncate claim_subjects, claims, sources, match_competitors, matches, athletes, ingestion_runs restart identity cascade"); err != nil {
		t.Fatalf("reset database: %v", err)
	}
	t.Log("reset dedicated integration schema to a known empty state")

	batch := fixtureBatch(json.RawMessage(`{"source":true}`))
	t.Log("run valid fixture once to prove canonical rows and a completed run are persisted")
	if _, err := Run(ctx, pool, batch); err != nil {
		t.Fatalf("first Run() error = %v", err)
	}
	t.Log("run the identical fixture again to prove database upserts are idempotent")
	if _, err := Run(ctx, pool, batch); err != nil {
		t.Fatalf("second Run() error = %v", err)
	}
	assertCount(t, ctx, pool, "sources", 1)
	assertCount(t, ctx, pool, "claims", 1)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed'", 2)

	t.Log("inject invalid JSON to prove transaction rollback and compensating failed-run recording")
	failed := fixtureBatch(json.RawMessage(`not-json`))
	if _, err := Run(ctx, pool, failed); err == nil {
		t.Fatal("Run() error = nil, want invalid JSON failure")
	}
	assertCount(t, ctx, pool, "sources", 1)
	assertCount(t, ctx, pool, "claims", 1)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'failed' and error_message is not null", 1)
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
	now := time.Date(2026, time.June, 1, 0, 0, 0, 0, time.UTC)
	return IngestBatch{
		BatchKey: "integration-fixture",
		Athletes: []AthleteInput{{Key: "ermes", CanonicalName: "Ermes Gasparini"}, {Key: "morozov", CanonicalName: "Artyom Morozov"}},
		Match:    MatchInput{Key: "match", NaturalKey: "2026-06:artyom-morozov:ermes-gasparini:right", Label: "Ermes Gasparini vs Artyom Morozov", Arm: "right", Competitors: []string{"ermes", "morozov"}},
		Sources:  []SourceInput{{Key: "youtube:fixture", SourceType: "youtube", ExternalID: "fixture", URL: "https://www.youtube.com/watch?v=fixture", RawPayload: raw}},
		Claims:   []ClaimInput{{SourceKey: "youtube:fixture", MatchKey: "match", SubjectKeys: []string{"ermes"}, Text: "Ermes claim", ExtractedAt: now, RawPayload: json.RawMessage(`{"claim":true}`)}},
	}
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
