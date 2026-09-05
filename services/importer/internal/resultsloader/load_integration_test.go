//go:build integration

package resultsloader

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

func TestSubmitAllPersistsAndReplaysEveryParsedRow(t *testing.T) {
	ctx, pool := loaderIntegrationPool(t)
	resetLoaderSchema(t, ctx, pool)
	submissions, err := Parse(strings.NewReader(csvHeader+
		"evw-25,East vs West 25,Core Sports,2026-08-01,right,105 kg,A,B,3,2,completed,video-1,\n"), "fixture.csv")
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if err := SubmitAll(ctx, pool, submissions); err != nil {
		t.Fatalf("SubmitAll() first run error = %v", err)
	}
	if err := SubmitAll(ctx, pool, submissions); err != nil {
		t.Fatalf("SubmitAll() replay error = %v", err)
	}
	for relation, want := range map[string]int{"events": 1, "matches": 1, "match_competitors": 2, "match_videos": 1} {
		var got int
		if err := pool.QueryRow(ctx, "select count(*) from "+relation).Scan(&got); err != nil {
			t.Fatalf("count %s: %v", relation, err)
		}
		if got != want {
			t.Errorf("count %s = %d, want %d", relation, got, want)
		}
	}
}

func loaderIntegrationPool(t *testing.T) (context.Context, *pgxpool.Pool) {
	t.Helper()
	databaseURL := os.Getenv("INGEST_TEST_DATABASE_URL")
	if databaseURL == "" {
		t.Fatal("INGEST_TEST_DATABASE_URL is required for integration tests")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatalf("connect integration database: %v", err)
	}
	t.Cleanup(pool.Close)
	return ctx, pool
}

func resetLoaderSchema(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	if _, err := pool.Exec(ctx, "truncate claim_subjects, claims, source_extractions, sources, match_videos, match_competitors, matches, events, athletes, ingestion_runs, run_predictions, run_models, experiment_runs, eval_folds, eval_protocols restart identity cascade"); err != nil {
		t.Fatalf("reset integration database: %v", err)
	}
}
