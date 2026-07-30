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
	RunID    int64
	Athletes int
	Sources  int
	Claims   int
}

func Run(ctx context.Context, databasePool *pgxpool.Pool, batch IngestBatch) (result Result, err error) {
	if err := Validate(batch); err != nil {
		return Result{}, err
	}
	return Submit(ctx, databasePool, evidenceSubmissionFromBatch(batch))
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
