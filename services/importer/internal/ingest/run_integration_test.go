//go:build integration

package ingest

import (
	"context"
	"os"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

const integrationDatabaseName = "armwrestling_math_test"
const integrationDatabaseLockID int64 = 742016

func integrationPool(t *testing.T) (context.Context, *pgxpool.Pool) {
	t.Helper()
	databaseURL := integrationDatabaseURL(t)
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	t.Cleanup(pool.Close)
	connection, err := pool.Acquire(ctx)
	if err != nil {
		t.Fatalf("acquire integration lock connection: %v", err)
	}
	if _, err := connection.Exec(ctx, "select pg_advisory_lock($1)", integrationDatabaseLockID); err != nil {
		connection.Release()
		t.Fatalf("lock integration database: %v", err)
	}
	t.Cleanup(func() {
		_, _ = connection.Exec(ctx, "select pg_advisory_unlock($1)", integrationDatabaseLockID)
		connection.Release()
	})
	return ctx, pool
}

func resetIntegrationSchema(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	if _, err := pool.Exec(ctx, "truncate claim_subjects, claims, source_extractions, sources, match_competitors, matches, athletes, ingestion_runs restart identity cascade"); err != nil {
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
	if config.ConnConfig.Database != integrationDatabaseName {
		t.Fatalf("INGEST_TEST_DATABASE_URL must target %q, got %q", integrationDatabaseName, config.ConnConfig.Database)
	}
	t.Logf("accepted dedicated integration database %q", integrationDatabaseName)
	return databaseURL
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
