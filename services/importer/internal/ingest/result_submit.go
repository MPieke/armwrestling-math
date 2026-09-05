package ingest

import (
	"context"
	"fmt"
	"strconv"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
)

// ResultOutcome identifies what a ResultSubmission created or updated.
type ResultOutcome struct {
	RunID   int64
	EventID int64
	MatchID int64
}

// SubmitResult validates and persists a result. Unlike Submit (evidence),
// which requires an existing match, SubmitResult owns creating event,
// athlete, match, and competitor-outcome identity -- importing a result is
// how a match enters the system in the first place.
func SubmitResult(ctx context.Context, databasePool *pgxpool.Pool, submission ResultSubmission) (outcome ResultOutcome, err error) {
	if err := ValidateResult(submission); err != nil {
		return ResultOutcome{}, err
	}
	databaseQueries := dbgen.New(databasePool)

	runID, err := databaseQueries.CreateIngestionRun(ctx, submission.BatchKey)
	if err != nil {
		return ResultOutcome{}, fmt.Errorf("create ingestion run: %w", err)
	}
	outcome = ResultOutcome{RunID: runID}
	transaction, err := databasePool.Begin(ctx)
	if err != nil {
		return outcome, failRun(ctx, databaseQueries, runID, err)
	}
	defer func() { _ = transaction.Rollback(ctx) }()
	transactionQueries := databaseQueries.WithTx(transaction)

	if err := submitResult(ctx, transactionQueries, submission, &outcome); err != nil {
		return outcome, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transactionQueries.CompleteIngestionRun(ctx, dbgen.CompleteIngestionRunParams{ID: runID, Summary: resultSummary(outcome)}); err != nil {
		return outcome, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transaction.Commit(ctx); err != nil {
		return outcome, failRun(ctx, databaseQueries, runID, err)
	}
	return outcome, nil
}

func submitResult(ctx context.Context, queries *dbgen.Queries, submission ResultSubmission, outcome *ResultOutcome) error {
	eventID, err := queries.UpsertEvent(ctx, dbgen.UpsertEventParams{
		Slug: submission.Event.Slug, Promoter: submission.Event.Promoter,
		Name: submission.Event.Name, HeldOn: dateValue(submission.Event.HeldOn),
	})
	if err != nil {
		return fmt.Errorf("upsert event %q: %w", submission.Event.Slug, err)
	}
	outcome.EventID = eventID

	naturalKey, err := resolveNaturalKey(ctx, queries, submission)
	if err != nil {
		return err
	}
	matchID, err := queries.UpsertResultMatch(ctx, dbgen.UpsertResultMatchParams{
		NaturalKey: naturalKey, Label: textPointer(matchLabel(submission)), Arm: submission.Arm,
		ScheduledAt: timeValue(&submission.ScheduledAt), EventID: eventID, Status: submission.Status,
	})
	if err != nil {
		return fmt.Errorf("upsert match %q: %w", naturalKey, err)
	}
	outcome.MatchID = matchID

	for _, competitor := range submission.Competitors {
		athleteID, err := queries.UpsertAthlete(ctx, competitor.AthleteName)
		if err != nil {
			return fmt.Errorf("upsert athlete %q: %w", competitor.AthleteName, err)
		}
		if err := queries.UpsertMatchCompetitorOutcome(ctx, dbgen.UpsertMatchCompetitorOutcomeParams{
			MatchID: matchID, AthleteID: athleteID,
			Score: intPointer(competitor.Score), Result: textValue(competitor.Result),
		}); err != nil {
			return fmt.Errorf("upsert competitor outcome for %q: %w", competitor.AthleteName, err)
		}
	}
	return nil
}

// resolveNaturalKey decides whether this submission is the same real-world
// match as one already stored (reuse its exact key so the upsert updates it
// in place) or a new meeting of the same pair on the same arm and event (a
// rematch, which gets a sequence-suffixed key instead of colliding with the
// first).
func resolveNaturalKey(ctx context.Context, queries *dbgen.Queries, submission ResultSubmission) (string, error) {
	base := buildBaseNaturalKey(submission.Event.Slug, submission.Competitors, submission.Arm)

	existing, err := queries.FindMatchNaturalKeyByBaseAndScheduledAt(ctx, dbgen.FindMatchNaturalKeyByBaseAndScheduledAtParams{
		NaturalKey: base, NaturalKey_2: base + ":%", ScheduledAt: timeValue(&submission.ScheduledAt),
	})
	if err == nil {
		return existing, nil
	}
	if err != pgx.ErrNoRows {
		return "", fmt.Errorf("find existing match by base natural key: %w", err)
	}

	count, err := queries.CountMatchesWithNaturalKeyPrefix(ctx, dbgen.CountMatchesWithNaturalKeyPrefixParams{
		NaturalKey: base, NaturalKey_2: base + ":%",
	})
	if err != nil {
		return "", fmt.Errorf("count matches with natural key prefix: %w", err)
	}
	if count == 0 {
		return base, nil
	}
	return base + ":" + strconv.FormatInt(count+1, 10), nil
}

func matchLabel(submission ResultSubmission) *string {
	if submission.MatchLabel != "" {
		return &submission.MatchLabel
	}
	return nil
}

func resultSummary(outcome ResultOutcome) []byte {
	return []byte(fmt.Sprintf(`{"event_id":%d,"match_id":%d}`, outcome.EventID, outcome.MatchID))
}
