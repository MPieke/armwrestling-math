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

func TestRunIsIdempotentAndRecordsTransactionalFailure(t *testing.T) {
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		t.Fatal("DATABASE_URL is required for integration tests")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	defer pool.Close()
	if _, err := pool.Exec(ctx, "truncate claim_subjects, claims, sources, match_competitors, matches, athletes, ingestion_runs restart identity cascade"); err != nil {
		t.Fatalf("reset database: %v", err)
	}

	batch := fixtureBatch(json.RawMessage(`{"source":true}`))
	if _, err := Run(ctx, pool, batch); err != nil {
		t.Fatalf("first Run() error = %v", err)
	}
	if _, err := Run(ctx, pool, batch); err != nil {
		t.Fatalf("second Run() error = %v", err)
	}
	assertCount(t, ctx, pool, "sources", 1)
	assertCount(t, ctx, pool, "claims", 1)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed'", 2)

	failed := fixtureBatch(json.RawMessage(`not-json`))
	if _, err := Run(ctx, pool, failed); err == nil {
		t.Fatal("Run() error = nil, want invalid JSON failure")
	}
	assertCount(t, ctx, pool, "sources", 1)
	assertCount(t, ctx, pool, "claims", 1)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'failed' and error_message is not null", 1)
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
	}
}
