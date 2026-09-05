//go:build integration

package ingest

import (
	"testing"
	"time"
)

func resultFixture() ResultSubmission {
	score := func(value int) *int { return &value }
	return ResultSubmission{
		SchemaVersion: ResultSubmissionSchemaVersion,
		BatchKey:      "result-fixture",
		Event: EventInput{
			Slug: "east-vs-west-25", Promoter: "East vs West", Name: "East vs West 25",
			HeldOn: time.Date(2026, time.August, 1, 0, 0, 0, 0, time.UTC),
		},
		Arm:         "right",
		ScheduledAt: time.Date(2026, time.August, 1, 18, 0, 0, 0, time.UTC),
		Status:      "completed",
		Competitors: []CompetitorResultInput{
			{AthleteName: "Adam Wawrzynski", Score: score(3), Result: "win"},
			{AthleteName: "Nurdaulet Aidarkhan", Score: score(2), Result: "loss"},
		},
	}
}

func TestSubmitResultCreatesEventMatchAndCompetitorOutcomes(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	submission := resultFixture()
	if _, err := SubmitResult(ctx, pool, submission); err != nil {
		t.Fatalf("SubmitResult() error = %v", err)
	}

	var status, eventSlug string
	if err := pool.QueryRow(ctx, `
		select m.status, e.slug from matches m join events e on e.id = m.event_id
	`).Scan(&status, &eventSlug); err != nil {
		t.Fatalf("read match/event: %v", err)
	}
	if status != "completed" || eventSlug != submission.Event.Slug {
		t.Errorf("status=%q eventSlug=%q, want completed/%q", status, eventSlug, submission.Event.Slug)
	}

	rows, err := pool.Query(ctx, `
		select a.canonical_name, mc.score, mc.result
		from match_competitors mc join athletes a on a.id = mc.athlete_id
		order by a.canonical_name`)
	if err != nil {
		t.Fatalf("read competitor outcomes: %v", err)
	}
	defer rows.Close()
	type outcome struct {
		name   string
		score  int
		result string
	}
	var got []outcome
	for rows.Next() {
		var o outcome
		if err := rows.Scan(&o.name, &o.score, &o.result); err != nil {
			t.Fatalf("scan competitor outcome: %v", err)
		}
		got = append(got, o)
	}
	want := []outcome{{"Adam Wawrzynski", 3, "win"}, {"Nurdaulet Aidarkhan", 2, "loss"}}
	if len(got) != len(want) {
		t.Fatalf("competitor outcomes = %+v, want %+v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("competitor outcome[%d] = %+v, want %+v", i, got[i], want[i])
		}
	}
}

func TestSubmitResultDistinguishesNoContestFromCompletedWin(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	completed := resultFixture()
	if _, err := SubmitResult(ctx, pool, completed); err != nil {
		t.Fatalf("SubmitResult() completed error = %v", err)
	}

	noContest := resultFixture()
	noContest.Event.Slug = "east-vs-west-26"
	noContest.Event.Name = "East vs West 26"
	noContest.Status = "no_contest"
	noContest.Competitors[0].Result, noContest.Competitors[0].Score = "no_contest", nil
	noContest.Competitors[1].Result, noContest.Competitors[1].Score = "no_contest", nil
	if _, err := SubmitResult(ctx, pool, noContest); err != nil {
		t.Fatalf("SubmitResult() no_contest error = %v", err)
	}

	assertCount(t, ctx, pool, "matches where status = 'completed'", 1)
	assertCount(t, ctx, pool, "matches where status = 'no_contest'", 1)
}

func TestSubmitResultMatchesAreSelectableByEvent(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	if _, err := SubmitResult(ctx, pool, resultFixture()); err != nil {
		t.Fatalf("SubmitResult() error = %v", err)
	}
	assertCount(t, ctx, pool, "matches m join events e on e.id = m.event_id where e.slug = 'east-vs-west-25'", 1)
}

func TestSubmitResultNaturalKeyIsOrderIndependent(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	forward := resultFixture()
	if _, err := SubmitResult(ctx, pool, forward); err != nil {
		t.Fatalf("SubmitResult() forward error = %v", err)
	}

	backward := resultFixture()
	backward.Competitors[0], backward.Competitors[1] = backward.Competitors[1], backward.Competitors[0]
	if _, err := SubmitResult(ctx, pool, backward); err != nil {
		t.Fatalf("SubmitResult() backward error = %v", err)
	}

	// Same match resubmitted with competitors listed in the opposite order
	// must resolve to the same natural key -- one match row, not two.
	assertCount(t, ctx, pool, "matches", 1)
}

func TestSubmitResultRematchGetsSequenceSuffix(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	first := resultFixture()
	if _, err := SubmitResult(ctx, pool, first); err != nil {
		t.Fatalf("SubmitResult() first meeting error = %v", err)
	}

	rematch := resultFixture()
	rematch.ScheduledAt = rematch.ScheduledAt.Add(24 * time.Hour)
	rematch.Competitors[0].Score, rematch.Competitors[1].Score = intPtr(3), intPtr(1)
	if _, err := SubmitResult(ctx, pool, rematch); err != nil {
		t.Fatalf("SubmitResult() rematch error = %v", err)
	}

	assertCount(t, ctx, pool, "matches", 2)
	var suffixedKeyExists bool
	if err := pool.QueryRow(ctx, `
		select exists (select 1 from matches where natural_key like '%:2')
	`).Scan(&suffixedKeyExists); err != nil {
		t.Fatalf("check rematch natural key: %v", err)
	}
	if !suffixedKeyExists {
		t.Error("rematch did not receive a sequence-suffixed natural key")
	}
}

func TestSubmitResultRejectsInvalidSubmissionBeforeDatabaseWork(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	invalid := resultFixture()
	invalid.SchemaVersion = "future-version"
	if _, err := SubmitResult(ctx, pool, invalid); err == nil {
		t.Fatal("SubmitResult() accepted an invalid submission")
	}
	assertCount(t, ctx, pool, "events", 0)
	assertCount(t, ctx, pool, "matches", 0)
}

func TestSubmitResultRollsBackAndRecordsFailedRunOnConstraintViolation(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	// A negative score passes Go validation (score sign is a PostgreSQL-level
	// concern per the contract's layer split) but must fail, and roll back,
	// at the database boundary.
	submission := resultFixture()
	*submission.Competitors[0].Score = -1
	if _, err := SubmitResult(ctx, pool, submission); err == nil {
		t.Fatal("SubmitResult() accepted a negative score")
	}
	assertCount(t, ctx, pool, "matches", 0)
	assertCount(t, ctx, pool, "events", 0)
	assertCount(t, ctx, pool, "ingestion_runs where status = 'failed' and error_message is not null", 1)
}

func TestSubmitResultReplayIsIdempotent(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	submission := resultFixture()
	if _, err := SubmitResult(ctx, pool, submission); err != nil {
		t.Fatalf("SubmitResult() first submit error = %v", err)
	}
	if _, err := SubmitResult(ctx, pool, submission); err != nil {
		t.Fatalf("SubmitResult() replay error = %v", err)
	}

	assertCount(t, ctx, pool, "events", 1)
	assertCount(t, ctx, pool, "matches", 1)
	assertCount(t, ctx, pool, "match_competitors", 2)
	assertCount(t, ctx, pool, "athletes", 2)
}

func TestEvidenceSubmissionResolvesResultCreatedMatchUnchanged(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	result := resultFixture()
	if _, err := SubmitResult(ctx, pool, result); err != nil {
		t.Fatalf("SubmitResult() error = %v", err)
	}
	naturalKey := buildBaseNaturalKey(result.Event.Slug, result.Competitors, result.Arm)

	evidence := evidenceFixture()
	evidence.MatchNaturalKey = naturalKey
	evidence.Claims[0].SubjectNames = []string{result.Competitors[0].AthleteName}
	if _, err := Submit(ctx, pool, evidence); err != nil {
		t.Fatalf("Submit() (evidence) error = %v", err)
	}

	var status string
	if err := pool.QueryRow(ctx, "select status from matches where natural_key = $1", naturalKey).Scan(&status); err != nil {
		t.Fatalf("read match status: %v", err)
	}
	if status != result.Status {
		t.Errorf("evidence submission changed match status: got %q, want %q", status, result.Status)
	}
	assertCount(t, ctx, pool, "match_competitors where score is not null", 2)
}

func intPtr(value int) *int { return &value }
