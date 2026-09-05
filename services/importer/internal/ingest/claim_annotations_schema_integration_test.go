//go:build integration

package ingest

import (
	"context"
	"fmt"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

func TestClaimAnnotationsUniquePerClaimModelAndPromptVersion(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	claimID := seedClaimForAnnotation(t, ctx, pool)

	insertAnnotation := `
		insert into claim_annotations (claim_id, model, prompt_version, claim_type, concepts, temporality, certainty)
		values ($1, 'gpt-4.1-mini', 'v1', 'tactic', array['top_roll'], 'current_form', 'observed')`
	if _, err := pool.Exec(ctx, insertAnnotation, claimID); err != nil {
		t.Fatalf("insert first annotation: %v", err)
	}
	if _, err := pool.Exec(ctx, insertAnnotation, claimID); err == nil {
		t.Fatal("duplicate (claim_id, model, prompt_version) inserted successfully")
	}
	assertCount(t, ctx, pool, "claim_annotations", 1)
}

func TestClaimAnnotationsRejectUnrecognizedTemporalityAndCertainty(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	claimID := seedClaimForAnnotation(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, insertAnnotationSQL(claimID, "not-a-temporality", "observed"))
	assertCheckConstraintViolation(t, ctx, pool, insertAnnotationSQL(claimID, "current_form", "not-a-certainty"))
}

func TestClaimAnnotationsCascadeDeleteWithTheirClaim(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	claimID := seedClaimForAnnotation(t, ctx, pool)
	if _, err := pool.Exec(ctx, insertAnnotationSQL(claimID, "current_form", "observed")); err != nil {
		t.Fatalf("insert annotation: %v", err)
	}

	if _, err := pool.Exec(ctx, "delete from claims where id = $1", claimID); err != nil {
		t.Fatalf("delete claim: %v", err)
	}
	assertCount(t, ctx, pool, "claim_annotations", 0)
}

func insertAnnotationSQL(claimID int64, temporality, certainty string) string {
	return fmt.Sprintf(
		"insert into claim_annotations (claim_id, model, prompt_version, claim_type, concepts, temporality, certainty) values (%d, 'gpt-4.1-mini', 'v1', 'tactic', array['top_roll'], '%s', '%s')",
		claimID, temporality, certainty,
	)
}

func seedClaimForAnnotation(t *testing.T, ctx context.Context, pool *pgxpool.Pool) int64 {
	t.Helper()
	seedExistingMatch(t, ctx, pool)
	var sourceID, matchID, claimID int64
	if err := pool.QueryRow(ctx,
		"insert into sources (source_type, external_id, url, published_at) values ('youtube', 'fixture-video', 'https://example.com', now()) returning id",
	).Scan(&sourceID); err != nil {
		t.Fatalf("seed source: %v", err)
	}
	if err := pool.QueryRow(ctx, "select id from matches limit 1").Scan(&matchID); err != nil {
		t.Fatalf("read match id: %v", err)
	}
	if err := pool.QueryRow(ctx,
		"insert into claims (source_id, match_id, claim_text, extracted_at) values ($1, $2, 'fixture claim', now()) returning id",
		sourceID, matchID,
	).Scan(&claimID); err != nil {
		t.Fatalf("seed claim: %v", err)
	}
	return claimID
}
