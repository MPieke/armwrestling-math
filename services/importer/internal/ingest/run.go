package ingest

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
)

type Result struct {
	RunID   int64
	Sources int
	Claims  int
}

// runIngestion is the shared ingestion-run lifecycle: create a run, run
// `work` inside a transaction, and record completion or failure. Submit
// (evidence) and SubmitResult share this shape; only what `work` does
// inside the transaction, and any precondition checks before calling this,
// differ between them.
func runIngestion(ctx context.Context, databasePool *pgxpool.Pool, batchKey string, work func(*dbgen.Queries) ([]byte, error)) (runID int64, err error) {
	databaseQueries := dbgen.New(databasePool)
	runID, err = databaseQueries.CreateIngestionRun(ctx, batchKey)
	if err != nil {
		return 0, fmt.Errorf("create ingestion run: %w", err)
	}
	transaction, err := databasePool.Begin(ctx)
	if err != nil {
		return runID, failRun(ctx, databaseQueries, runID, err)
	}
	defer func() { _ = transaction.Rollback(ctx) }()
	transactionQueries := databaseQueries.WithTx(transaction)

	summary, err := work(transactionQueries)
	if err != nil {
		return runID, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transactionQueries.CompleteIngestionRun(ctx, dbgen.CompleteIngestionRunParams{ID: runID, Summary: summary}); err != nil {
		return runID, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transaction.Commit(ctx); err != nil {
		return runID, failRun(ctx, databaseQueries, runID, err)
	}
	return runID, nil
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
func int64Value(value int64, valid bool) pgtype.Int8 {
	return pgtype.Int8{Int64: value, Valid: valid}
}
func timeValue(value *time.Time) pgtype.Timestamptz {
	if value != nil {
		return pgtype.Timestamptz{Time: *value, Valid: true}
	}
	return pgtype.Timestamptz{}
}
func dateValue(value time.Time) pgtype.Date { return pgtype.Date{Time: value, Valid: true} }
