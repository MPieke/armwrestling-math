//go:build integration

package ingest

import (
	"testing"
)

func TestCompletedMatchesViewExcludesNonCompletedMatches(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	completed := resultFixture()
	if _, err := SubmitResult(ctx, pool, completed); err != nil {
		t.Fatalf("SubmitResult() completed error = %v", err)
	}

	scheduled := resultFixture()
	scheduled.Event.Slug, scheduled.Event.Name = "east-vs-west-26", "East vs West 26"
	scheduled.Status = "scheduled"
	scheduled.Competitors[0].Score, scheduled.Competitors[0].Result = nil, ""
	scheduled.Competitors[1].Score, scheduled.Competitors[1].Result = nil, ""
	if _, err := SubmitResult(ctx, pool, scheduled); err != nil {
		t.Fatalf("SubmitResult() scheduled error = %v", err)
	}

	assertCount(t, ctx, pool, "matches", 2)
	assertCount(t, ctx, pool, "v_completed_matches", 1)

	var eventID, arm string
	var athleteAID, athleteBID int64
	if err := pool.QueryRow(ctx, `
		select event_id::text, arm, athlete_a_id, athlete_b_id from v_completed_matches
	`).Scan(&eventID, &arm, &athleteAID, &athleteBID); err != nil {
		t.Fatalf("read v_completed_matches row: %v", err)
	}
	if arm != "right" {
		t.Errorf("arm = %q, want right", arm)
	}
	if athleteAID >= athleteBID {
		t.Errorf("athlete_a_id (%d) >= athlete_b_id (%d), want a strict ordering", athleteAID, athleteBID)
	}
}
