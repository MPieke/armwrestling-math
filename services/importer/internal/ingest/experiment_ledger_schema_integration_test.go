//go:build integration

package ingest

import (
	"context"
	"fmt"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

func TestExperimentLedgerSchema(t *testing.T) {
	ctx, pool := integrationPool(t)

	for _, table := range []string{"eval_protocols", "eval_folds", "experiment_runs", "run_predictions", "run_models"} {
		var exists bool
		if err := pool.QueryRow(ctx, "select to_regclass($1) is not null", "public."+table).Scan(&exists); err != nil {
			t.Fatalf("check %s relation: %v", table, err)
		}
		if !exists {
			t.Fatalf("%s table does not exist", table)
		}
	}

	assertColumnNullable(t, ctx, pool, "experiment_runs", "protocol_id", "NO")
	assertColumnNullable(t, ctx, pool, "experiment_runs", "parent_run_id", "YES")
}

func TestEvalProtocolNameIsUnique(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	if _, err := pool.Exec(ctx, "insert into eval_protocols (name, kind) values ('dev', 'rolling_origin')"); err != nil {
		t.Fatalf("insert protocol: %v", err)
	}
	_, err := pool.Exec(ctx, "insert into eval_protocols (name, kind) values ('dev', 'rolling_origin')")
	if err == nil {
		t.Fatal("duplicate protocol name inserted successfully")
	}
}

func TestEvalProtocolKindConstraintRejectsUnrecognizedValue(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, "insert into eval_protocols (name, kind) values ('bad', 'not-a-kind')")
}

func TestEvalFoldsRoundTripsMatchIDArraysIncludingEmpty(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	protocolID := seedProtocol(t, ctx, pool, "dev", "rolling_origin")
	if _, err := pool.Exec(ctx, `
		insert into eval_folds (protocol_id, fold_index, train_match_ids, test_match_ids)
		values ($1, 0, '{}', '{1,2,3}')`, protocolID); err != nil {
		t.Fatalf("insert fold: %v", err)
	}

	var trainCount, testCount int
	if err := pool.QueryRow(ctx, `
		select coalesce(array_length(train_match_ids, 1), 0), array_length(test_match_ids, 1)
		from eval_folds where protocol_id = $1 and fold_index = 0`, protocolID).Scan(&trainCount, &testCount); err != nil {
		t.Fatalf("read fold arrays: %v", err)
	}
	if trainCount != 0 || testCount != 3 {
		t.Errorf("trainCount=%d testCount=%d, want 0/3", trainCount, testCount)
	}
}

func TestExperimentRunsSupportIndependentRunsPerProtocolAndParentLineage(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)

	protocolID := seedProtocol(t, ctx, pool, "dev", "rolling_origin")

	featureSpecID := seedFeatureSpec(t, ctx, pool)

	var firstRunID int64
	if err := pool.QueryRow(ctx, `
		insert into experiment_runs (git_sha, git_dirty, protocol_id, feature_spec_id, model_family, seed, status)
		values ('abc123', false, $1, $2, 'elo', 1, 'completed') returning id`, protocolID, featureSpecID).Scan(&firstRunID); err != nil {
		t.Fatalf("insert first run: %v", err)
	}

	var secondRunID int64
	if err := pool.QueryRow(ctx, `
		insert into experiment_runs (git_sha, git_dirty, protocol_id, feature_spec_id, feature_spec, model_family, hyperparams, seed, parent_run_id, hypothesis, status)
		values ('def456', false, $1, $2, '{"evidence_scope":"dyad"}', 'logistic_regression', '{"k":16}', 2, $3, 'evidence beats elo', 'completed')
		returning id`, protocolID, featureSpecID, firstRunID).Scan(&secondRunID); err != nil {
		t.Fatalf("insert second run: %v", err)
	}

	var parent *int64
	if err := pool.QueryRow(ctx, "select parent_run_id from experiment_runs where id = $1", secondRunID).Scan(&parent); err != nil {
		t.Fatalf("read parent_run_id: %v", err)
	}
	if parent == nil || *parent != firstRunID {
		t.Errorf("parent_run_id = %v, want %d", parent, firstRunID)
	}

	var firstParent *int64
	if err := pool.QueryRow(ctx, "select parent_run_id from experiment_runs where id = $1", firstRunID).Scan(&firstParent); err != nil {
		t.Fatalf("read first run parent_run_id: %v", err)
	}
	if firstParent != nil {
		t.Errorf("first run in a lineage has a parent: %v", firstParent)
	}
}

func TestRunPredictionsRejectsDuplicateAthletePerMatch(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)

	runID, matchID, athleteID := seedCompletedRunAndFixtureIdentity(t, ctx, pool)

	if _, err := pool.Exec(ctx, `
		insert into run_predictions (run_id, match_id, athlete_id, p_win) values ($1, $2, $3, 0.6)`,
		runID, matchID, athleteID); err != nil {
		t.Fatalf("insert prediction: %v", err)
	}
	_, err := pool.Exec(ctx, `
		insert into run_predictions (run_id, match_id, athlete_id, p_win) values ($1, $2, $3, 0.7)`,
		runID, matchID, athleteID)
	if err == nil {
		t.Fatal("duplicate (run_id, match_id, athlete_id) inserted successfully")
	}
}

func TestRunPredictionsRejectsOutOfRangeProbability(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)
	runID, matchID, athleteID := seedCompletedRunAndFixtureIdentity(t, ctx, pool)

	assertCheckConstraintViolation(t, ctx, pool, fmt.Sprintf(
		"insert into run_predictions (run_id, match_id, athlete_id, p_win) values (%d, %d, %d, 1.5)",
		runID, matchID, athleteID))
}

func TestDeletingExperimentRunCascadesPredictionsAndModelsOnly(t *testing.T) {
	ctx, pool := integrationPool(t)
	resetIntegrationSchema(t, ctx, pool)
	seedExistingMatch(t, ctx, pool)
	runID, matchID, athleteID := seedCompletedRunAndFixtureIdentity(t, ctx, pool)

	if _, err := pool.Exec(ctx, "insert into run_predictions (run_id, match_id, athlete_id, p_win) values ($1, $2, $3, 0.5)", runID, matchID, athleteID); err != nil {
		t.Fatalf("insert prediction: %v", err)
	}
	if _, err := pool.Exec(ctx, "insert into run_models (run_id, params) values ($1, '{}')", runID); err != nil {
		t.Fatalf("insert model: %v", err)
	}

	if _, err := pool.Exec(ctx, "delete from experiment_runs where id = $1", runID); err != nil {
		t.Fatalf("delete run: %v", err)
	}
	assertCount(t, ctx, pool, "run_predictions", 0)
	assertCount(t, ctx, pool, "run_models", 0)
	assertCount(t, ctx, pool, "eval_protocols", 1)
}

// seedFeatureSpec returns the id of the migration-seeded 'outcomes_elo'
// feature spec. feature_specs is never truncated by resetIntegrationSchema
// (nothing cascades into it), so this row always exists.
func seedFeatureSpec(t *testing.T, ctx context.Context, pool *pgxpool.Pool) int64 {
	t.Helper()
	var featureSpecID int64
	if err := pool.QueryRow(ctx, "select id from feature_specs where name = 'outcomes_elo' and version = 1").Scan(&featureSpecID); err != nil {
		t.Fatalf("read seeded feature spec: %v", err)
	}
	return featureSpecID
}

func seedProtocol(t *testing.T, ctx context.Context, pool *pgxpool.Pool, name, kind string) int64 {
	t.Helper()
	var protocolID int64
	if err := pool.QueryRow(ctx, "insert into eval_protocols (name, kind) values ($1, $2) returning id", name, kind).Scan(&protocolID); err != nil {
		t.Fatalf("insert protocol: %v", err)
	}
	return protocolID
}

// seedCompletedRunAndFixtureIdentity seeds one protocol, one completed run
// against it, and returns the run id alongside an existing match/athlete
// pair from seedExistingMatch for use as a prediction target.
func seedCompletedRunAndFixtureIdentity(t *testing.T, ctx context.Context, pool *pgxpool.Pool) (runID, matchID, athleteID int64) {
	t.Helper()
	protocolID := seedProtocol(t, ctx, pool, "dev", "rolling_origin")
	featureSpecID := seedFeatureSpec(t, ctx, pool)
	if err := pool.QueryRow(ctx, `
		insert into experiment_runs (git_sha, git_dirty, protocol_id, feature_spec_id, model_family, seed, status)
		values ('abc123', false, $1, $2, 'elo', 1, 'completed') returning id`, protocolID, featureSpecID).Scan(&runID); err != nil {
		t.Fatalf("insert run: %v", err)
	}
	if err := pool.QueryRow(ctx, "select id from matches limit 1").Scan(&matchID); err != nil {
		t.Fatalf("read match id: %v", err)
	}
	if err := pool.QueryRow(ctx, "select id from athletes limit 1").Scan(&athleteID); err != nil {
		t.Fatalf("read athlete id: %v", err)
	}
	return runID, matchID, athleteID
}
