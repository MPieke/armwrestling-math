package ingest

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
)

type Result struct {
	RunID    int64
	Athletes int
	Sources  int
	Claims   int
}

func Run(ctx context.Context, databasePool *pgxpool.Pool, batch IngestBatch) (result Result, err error) {
	if err := Validate(batch); err != nil {
		return Result{}, err
	}
	// Run audit records use the pool so a failed attempt can outlive a rolled-back
	// evidence transaction.
	databaseQueries := dbgen.New(databasePool)
	runID, err := databaseQueries.CreateIngestionRun(ctx, batch.BatchKey)
	if err != nil {
		return Result{}, fmt.Errorf("create ingestion run: %w", err)
	}
	result = Result{RunID: runID, Athletes: len(batch.Athletes), Sources: len(batch.Sources), Claims: len(batch.Claims)}

	transaction, err := databasePool.Begin(ctx)
	if err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	// Rollback is a safety net for every return path; after Commit it is a no-op.
	defer func() { _ = transaction.Rollback(ctx) }()
	// Canonical evidence writes must use this transaction-bound query set.
	transactionQueries := databaseQueries.WithTx(transaction)
	if err := runBatch(ctx, transactionQueries, batch); err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	summary, err := json.Marshal(map[string]int{
		"athletes": result.Athletes,
		"sources":  result.Sources,
		"claims":   result.Claims,
	})
	if err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	// Completion is transactional: a completed run always has its evidence writes.
	if err := transactionQueries.CompleteIngestionRun(ctx, dbgen.CompleteIngestionRunParams{ID: runID, Summary: summary}); err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transaction.Commit(ctx); err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	return result, nil
}

func runBatch(ctx context.Context, transactionQueries *dbgen.Queries, batch IngestBatch) error {
	// These phases stay together because each one produces IDs required by the
	// next, and their ordering mirrors the transaction's referential integrity.
	athleteIDs := make(map[string]int64, len(batch.Athletes))
	for _, athlete := range batch.Athletes {
		id, err := transactionQueries.UpsertAthlete(ctx, athlete.CanonicalName)
		if err != nil {
			return fmt.Errorf("upsert athlete %q: %w", athlete.Key, err)
		}
		athleteIDs[athlete.Key] = id
	}
	matchID, err := transactionQueries.UpsertMatch(ctx, dbgen.UpsertMatchParams{
		NaturalKey:  batch.Match.NaturalKey,
		Label:       textValue(batch.Match.Label),
		Arm:         batch.Match.Arm,
		ScheduledAt: timeValue(batch.Match.ScheduledAt),
	})
	if err != nil {
		return fmt.Errorf("upsert match: %w", err)
	}
	for _, key := range batch.Match.Competitors {
		if err := transactionQueries.LinkMatchCompetitor(ctx, dbgen.LinkMatchCompetitorParams{MatchID: matchID, AthleteID: athleteIDs[key]}); err != nil {
			return fmt.Errorf("link match competitor %q: %w", key, err)
		}
	}
	sourceIDs := make(map[string]int64, len(batch.Sources))
	for _, source := range batch.Sources {
		id, err := transactionQueries.UpsertSource(ctx, dbgen.UpsertSourceParams{
			SourceType: source.SourceType, ExternalID: source.ExternalID, Url: source.URL,
			Title: textPointer(source.Title), PublishedAt: timeValue(source.PublishedAt), RawPayload: source.RawPayload,
		})
		if err != nil {
			return fmt.Errorf("upsert source %q: %w", source.Key, err)
		}
		sourceIDs[source.Key] = id
	}
	for _, claim := range batch.Claims {
		claimID, err := transactionQueries.UpsertClaim(ctx, dbgen.UpsertClaimParams{
			SourceID: sourceIDs[claim.SourceKey], MatchID: matchID, ClaimText: claim.Text,
			TimestampSeconds: intPointer(claim.TimestampSeconds), Speaker: textPointer(claim.Speaker),
			Confidence: textPointer(claim.Confidence), Relevance: textPointer(claim.Relevance),
			ObservedAt: timeValue(claim.ObservedAt), ExtractedAt: timeValue(&claim.ExtractedAt),
			ExtractionModel: textPointer(claim.ExtractionModel), RawPayload: claim.RawPayload,
		})
		if err != nil {
			return fmt.Errorf("upsert claim %q: %w", claim.Text, err)
		}
		for _, key := range claim.SubjectKeys {
			if err := transactionQueries.LinkClaimSubject(ctx, dbgen.LinkClaimSubjectParams{ClaimID: claimID, AthleteID: athleteIDs[key]}); err != nil {
				return fmt.Errorf("link claim subject %q: %w", key, err)
			}
		}
	}
	return nil
}

func failRun(ctx context.Context, databaseQueries *dbgen.Queries, runID int64, cause error) error {
	failErr := databaseQueries.FailIngestionRun(ctx, dbgen.FailIngestionRunParams{ID: runID, ErrorMessage: textValue(cause.Error())})
	if failErr != nil {
		return fmt.Errorf("ingestion failed: %w; also could not record failed run: %v", cause, failErr)
	}
	return fmt.Errorf("ingestion failed: %w", cause)
}

func textValue(value string) pgtype.Text { return pgtype.Text{String: value, Valid: value != ""} }
func textPointer(value *string) pgtype.Text {
	if value == nil {
		return pgtype.Text{}
	}
	return pgtype.Text{String: *value, Valid: true}
}
func intPointer(value *int) pgtype.Int4 {
	if value == nil {
		return pgtype.Int4{}
	}
	return pgtype.Int4{Int32: int32(*value), Valid: true}
}
func timeValue(value *time.Time) pgtype.Timestamptz {
	if value != nil {
		return pgtype.Timestamptz{Time: *value, Valid: true}
	}
	return pgtype.Timestamptz{}
}
