//go:build integration

package ingest

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func TestSubmitPersistsEvidenceForExistingMatchWithoutMutatingCanonicalData(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	submission := evidenceFixture()
	if _, err := Submit(ctx, pool, submission); err != nil {
		t.Fatalf("Submit() error = %v", err)
	}

	assertCanonicalCounts(t, ctx, pool, 2, 1, 2, 1, 1, 1)
	var label, arm string
	if err := pool.QueryRow(ctx, "select label, arm from matches where natural_key = $1", submission.MatchNaturalKey).Scan(&label, &arm); err != nil {
		t.Fatalf("read existing match: %v", err)
	}
	if label != "Ermes Gasparini vs Artyom Morozov" || arm != "right" {
		t.Errorf("match changed to (%q, %q), want seeded canonical data", label, arm)
	}
	if _, err := Submit(ctx, pool, submission); err != nil {
		t.Fatalf("second Submit() error = %v", err)
	}
	assertCanonicalCounts(t, ctx, pool, 2, 1, 2, 1, 1, 1)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'completed'", 2)
}

func TestSubmitRejectsMissingMatchBeforeEvidencePersistence(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	submission := evidenceFixture()
	submission.MatchNaturalKey = "missing-match"
	_, err := Submit(ctx, pool, submission)
	if err == nil || !strings.Contains(err.Error(), "match not found") {
		t.Fatalf("Submit() error = %v, want missing match error", err)
	}
	assertCanonicalCounts(t, ctx, pool, 0, 0, 0, 0, 0, 0)
}

func TestSubmitRejectsSubjectOutsideExistingMatch(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	submission := evidenceFixture()
	submission.Claims[0].SubjectNames = []string{"Unknown athlete"}
	_, err := Submit(ctx, pool, submission)
	if err == nil || !strings.Contains(err.Error(), "subject is not a match competitor") {
		t.Fatalf("Submit() error = %v, want subject validation error", err)
	}
	assertCanonicalCounts(t, ctx, pool, 2, 1, 2, 0, 0, 0)
}

func TestSubmitRollsBackEvidenceAndRecordsFailure(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)
	submission := evidenceFixture()
	submission.Sources[0].RawPayload = json.RawMessage(`not-json`)
	if _, err := Submit(ctx, pool, submission); err == nil {
		t.Fatal("Submit() error = nil, want invalid JSON failure")
	}
	assertCanonicalCounts(t, ctx, pool, 2, 1, 2, 0, 0, 0)
	assertCount(t, ctx, pool, "source_extractions", 0)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'failed' and error_message is not null", 1)
}

func seedExistingMatch(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	_, err := pool.Exec(ctx, `
		with ermes as (
			insert into athletes (canonical_name) values ('Ermes Gasparini') returning id
		), morozov as (
			insert into athletes (canonical_name) values ('Artyom Morozov') returning id
		), event as (
			insert into events (slug, promoter, name, held_on)
			values ('fixture-event', 'Fixture Promoter', 'Fixture Event', '2026-06-15')
			returning id
		), matchup as (
			insert into matches (natural_key, label, arm, weight_class, scheduled_at, event_id, status)
			select
				'2026-06:artyom-morozov:ermes-gasparini:right',
				'Ermes Gasparini vs Artyom Morozov',
				'right',
				'105 kg',
				'2026-06-15T18:30:00Z',
				event.id,
				'scheduled'
			from event
			returning id
		)
		insert into match_competitors (match_id, athlete_id)
		select matchup.id, athlete.id
		from matchup cross join (select id from ermes union all select id from morozov) athlete
	`)
	if err != nil {
		t.Fatalf("seed existing match: %v", err)
	}
}

func evidenceFixture() EvidenceSubmission {
	extractedAt := time.Date(2026, time.June, 1, 0, 0, 0, 0, time.UTC)
	return EvidenceSubmission{
		SchemaVersion:   "evidence-submission-v1",
		BatchKey:        "evidence-fixture",
		MatchNaturalKey: "2026-06:artyom-morozov:ermes-gasparini:right",
		Sources: []SourceInput{{
			Key:        "youtube:fixture",
			SourceType: "youtube",
			ExternalID: "fixture",
			URL:        "https://www.youtube.com/watch?v=fixture",
			RawPayload: json.RawMessage(`{"source":true}`),
		}},
		Claims: []EvidenceClaimInput{{
			SourceKey:       "youtube:fixture",
			SubjectNames:    []string{"Ermes Gasparini"},
			Text:            "Ermes claim",
			ExtractedAt:     extractedAt,
			RawPayload:      json.RawMessage(`{"claim":true}`),
			ExtractionModel: "fixture-model",
		}},
	}
}
