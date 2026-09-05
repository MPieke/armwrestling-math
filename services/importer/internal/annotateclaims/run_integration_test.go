//go:build integration

package annotateclaims

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/annotate"
)

// Shared with internal/ingest and internal/youtubeingest: all three
// packages' integration tests touch the same physical test database
// (claims, sources, matches, ...), so they share one advisory lock ID to
// serialize against each other under `go test ./...`'s package-level
// parallelism -- a different ID here would only prevent self-collision,
// not collision with those other packages.
const integrationDatabaseLockID int64 = 742016

func TestRunAnnotatesEachClaimOnceAndSkipsAlreadyAnnotatedOnRetry(t *testing.T) {
	ctx := context.Background()
	pool := integrationPool(t, ctx)
	resetAndSeed(t, ctx, pool)

	annotator := &fakeAnnotator{model: "fixture-model"}
	first, err := Run(ctx, pool, annotator, Options{PromptVersion: "v1"})
	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if first.Selected != 2 || first.Completed != 2 || first.Failed != 0 {
		t.Fatalf("first result = %+v", first)
	}
	assertCount(t, ctx, pool, "claim_annotations", 2)

	second, err := Run(ctx, pool, annotator, Options{PromptVersion: "v1"})
	if err != nil {
		t.Fatalf("second Run() error = %v", err)
	}
	if second.Selected != 0 {
		t.Fatalf("second result = %+v, want nothing left to annotate", second)
	}
	assertCount(t, ctx, pool, "claim_annotations", 2)
}

func TestRunResolvesSubjectAthleteNameToAnID(t *testing.T) {
	ctx := context.Background()
	pool := integrationPool(t, ctx)
	claimID, subjectAthleteID := resetAndSeedSingleClaim(t, ctx, pool, "Ermes Gasparini")

	annotator := &fakeAnnotator{model: "fixture-model", subjectAthleteName: "Ermes Gasparini"}
	if _, err := Run(ctx, pool, annotator, Options{PromptVersion: "v1"}); err != nil {
		t.Fatalf("Run() error = %v", err)
	}

	var storedSubjectID int64
	if err := pool.QueryRow(ctx, "select subject_athlete_id from claim_annotations where claim_id = $1", claimID).Scan(&storedSubjectID); err != nil {
		t.Fatalf("read stored subject_athlete_id: %v", err)
	}
	if storedSubjectID != subjectAthleteID {
		t.Fatalf("subject_athlete_id = %d, want %d", storedSubjectID, subjectAthleteID)
	}
}

func TestRunContinuesPastAValidationFailureAndCountsIt(t *testing.T) {
	ctx := context.Background()
	pool := integrationPool(t, ctx)
	resetAndSeed(t, ctx, pool)

	annotator := &fakeAnnotator{model: "fixture-model", forceInvalidClaimType: true}
	result, err := Run(ctx, pool, annotator, Options{PromptVersion: "v1"})
	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if result.Selected != 2 || result.Completed != 0 || result.Failed != 2 {
		t.Fatalf("result = %+v", result)
	}
	assertCount(t, ctx, pool, "claim_annotations", 0)
}

type fakeAnnotator struct {
	model                 string
	subjectAthleteName    string
	forceInvalidClaimType bool
	calls                 int
}

func (a *fakeAnnotator) ModelName() string { return a.model }

func (a *fakeAnnotator) Annotate(_ context.Context, claim annotate.ClaimContext) (annotate.ClaimAnnotation, json.RawMessage, json.RawMessage, error) {
	a.calls++
	claimType := "tactic"
	if a.forceInvalidClaimType {
		claimType = "not-a-real-type"
	}
	return annotate.ClaimAnnotation{
		ClaimType:          claimType,
		Concepts:           []string{"top_roll"},
		SubjectAthleteName: a.subjectAthleteName,
		Arm:                "right",
		Temporality:        "current_form",
		Certainty:          "observed",
	}, nil, json.RawMessage(`{"total_tokens":1}`), nil
}

func integrationPool(t *testing.T, ctx context.Context) *pgxpool.Pool {
	t.Helper()
	databaseURL := os.Getenv("INGEST_TEST_DATABASE_URL")
	configuration, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	if configuration.ConnConfig.Database != "armwrestling_math_test" {
		t.Fatalf("integration database must be armwrestling_math_test, got %q", configuration.ConnConfig.Database)
	}
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	connection, err := pool.Acquire(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := connection.Exec(ctx, "select pg_advisory_lock($1)", integrationDatabaseLockID); err != nil {
		connection.Release()
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_, _ = connection.Exec(ctx, "select pg_advisory_unlock($1)", integrationDatabaseLockID)
		connection.Release()
	})
	return pool
}

func resetAndSeed(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	reset(t, ctx, pool)
	matchID, _ := seedMatch(t, ctx, pool, "Artyom Morozov", "Ermes Gasparini")
	sourceID := seedSource(t, ctx, pool)
	seedClaim(t, ctx, pool, sourceID, matchID, "first claim")
	seedClaim(t, ctx, pool, sourceID, matchID, "second claim")
}

func resetAndSeedSingleClaim(t *testing.T, ctx context.Context, pool *pgxpool.Pool, subjectName string) (claimID, subjectAthleteID int64) {
	t.Helper()
	reset(t, ctx, pool)
	matchID, athleteIDByName := seedMatch(t, ctx, pool, "Artyom Morozov", subjectName)
	sourceID := seedSource(t, ctx, pool)
	claimID = seedClaim(t, ctx, pool, sourceID, matchID, "claim about "+subjectName)
	return claimID, athleteIDByName[subjectName]
}

func reset(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	if _, err := pool.Exec(ctx, "truncate claim_subjects, claims, source_extractions, sources, match_videos, match_competitors, matches, events, athletes, ingestion_runs restart identity cascade"); err != nil {
		t.Fatalf("reset schema: %v", err)
	}
}

func seedMatch(t *testing.T, ctx context.Context, pool *pgxpool.Pool, athleteA, athleteB string) (matchID int64, athleteIDByName map[string]int64) {
	t.Helper()
	athleteIDByName = make(map[string]int64, 2)
	var eventID int64
	if err := pool.QueryRow(ctx, "insert into events (slug, promoter, name, held_on) values ('fixture-event', 'Fixture', 'Fixture Event', '2026-06-15') returning id").Scan(&eventID); err != nil {
		t.Fatalf("seed event: %v", err)
	}
	if err := pool.QueryRow(ctx,
		"insert into matches (natural_key, weight_class, arm, scheduled_at, event_id, status) values ($1, '105 kg', 'right', '2026-06-15', $2, 'completed') returning id",
		strings.ToLower(athleteA)+":"+strings.ToLower(athleteB), eventID,
	).Scan(&matchID); err != nil {
		t.Fatalf("seed match: %v", err)
	}
	for _, name := range []string{athleteA, athleteB} {
		var athleteID int64
		if err := pool.QueryRow(ctx, "insert into athletes (canonical_name) values ($1) returning id", name).Scan(&athleteID); err != nil {
			t.Fatalf("seed athlete %q: %v", name, err)
		}
		if _, err := pool.Exec(ctx, "insert into match_competitors (match_id, athlete_id) values ($1, $2)", matchID, athleteID); err != nil {
			t.Fatalf("link competitor %q: %v", name, err)
		}
		athleteIDByName[name] = athleteID
	}
	return matchID, athleteIDByName
}

func seedSource(t *testing.T, ctx context.Context, pool *pgxpool.Pool) int64 {
	t.Helper()
	var sourceID int64
	if err := pool.QueryRow(ctx,
		"insert into sources (source_type, external_id, url, published_at) values ('youtube', 'fixture-video', 'https://example.com', now()) returning id",
	).Scan(&sourceID); err != nil {
		t.Fatalf("seed source: %v", err)
	}
	return sourceID
}

func seedClaim(t *testing.T, ctx context.Context, pool *pgxpool.Pool, sourceID, matchID int64, text string) int64 {
	t.Helper()
	var claimID int64
	if err := pool.QueryRow(ctx,
		"insert into claims (source_id, match_id, claim_text, extracted_at) values ($1, $2, $3, now()) returning id",
		sourceID, matchID, text,
	).Scan(&claimID); err != nil {
		t.Fatalf("seed claim: %v", err)
	}
	return claimID
}

func assertCount(t *testing.T, ctx context.Context, pool *pgxpool.Pool, relation string, want int) {
	t.Helper()
	var got int
	if err := pool.QueryRow(ctx, "select count(*) from "+relation).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("%s count = %d, want %d", relation, got, want)
	}
}
