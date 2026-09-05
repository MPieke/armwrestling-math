//go:build integration

package ingest

import (
	"testing"
)

func TestSourceExtractionSchema(t *testing.T) {
	ctx, pool := integrationPool(t)

	var exists bool
	if err := pool.QueryRow(ctx, "select to_regclass('public.source_extractions') is not null").Scan(&exists); err != nil {
		t.Fatalf("check source_extractions relation: %v", err)
	}
	if !exists {
		t.Fatal("source_extractions table does not exist")
	}

	expectedColumns := map[string]string{
		"id":             "NO",
		"source_id":      "NO",
		"match_id":       "NO",
		"provider":       "NO",
		"model":          "NO",
		"prompt_version": "NO",
		"status":         "NO",
		"extracted_at":   "NO",
		"raw_response":   "YES",
		"usage":          "YES",
		"error_message":  "YES",
	}
	for column, nullable := range expectedColumns {
		var actual string
		err := pool.QueryRow(ctx, `
			select is_nullable
			from information_schema.columns
			where table_schema = 'public' and table_name = 'source_extractions' and column_name = $1
		`, column).Scan(&actual)
		if err != nil {
			t.Fatalf("read source_extractions.%s: %v", column, err)
		}
		if actual != nullable {
			t.Errorf("source_extractions.%s is_nullable = %q, want %q", column, actual, nullable)
		}
	}

	var nullable string
	if err := pool.QueryRow(ctx, `
		select is_nullable
		from information_schema.columns
		where table_schema = 'public' and table_name = 'claims' and column_name = 'source_extraction_id'
	`).Scan(&nullable); err != nil {
		t.Fatalf("read claims.source_extraction_id: %v", err)
	}
	if nullable != "YES" {
		t.Errorf("claims.source_extraction_id is_nullable = %q, want YES for legacy claims", nullable)
	}
}

func TestSourceExtractionMigrationPreservesLegacyClaims(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	if _, err := Submit(ctx, pool, evidenceFixture()); err != nil {
		t.Fatalf("persist legacy-shaped claim: %v", err)
	}

	var extractionID *int64
	if err := pool.QueryRow(ctx, "select source_extraction_id from claims").Scan(&extractionID); err != nil {
		t.Fatalf("read legacy claim extraction link: %v", err)
	}
	if extractionID != nil {
		t.Errorf("legacy claim source_extraction_id = %d, want NULL", *extractionID)
	}
}

func TestSourceExtractionStatusConstraint(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	if _, err := Submit(ctx, pool, evidenceFixture()); err != nil {
		t.Fatalf("seed source and match: %v", err)
	}

	assertCheckConstraintViolation(t, ctx, pool, `
		insert into source_extractions (source_id, match_id, provider, model, prompt_version, status, extracted_at)
		select sources.id, matches.id, 'fixture-provider', 'test-model', 'v1', 'not-a-status', now()
		from sources cross join matches
	`)
}
