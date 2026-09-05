package resultsloader

import (
	"context"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
)

// SubmissionResult records one attempted canonical result write. A failed row
// is isolated so later valid rows can still be imported from the same file.
type SubmissionResult struct {
	RowNumber int
	Outcome   ingest.ResultOutcome
	Err       error
}

// SubmitAll writes already parsed submissions in file order. Parsing must be
// completed first, so malformed input never reaches this database boundary.
func SubmitAll(ctx context.Context, databasePool *pgxpool.Pool, submissions []ingest.ResultSubmission) ([]SubmissionResult, error) {
	results := make([]SubmissionResult, 0, len(submissions))
	var problems []string
	for index, submission := range submissions {
		outcome, err := ingest.SubmitResult(ctx, databasePool, submission)
		results = append(results, SubmissionResult{RowNumber: index + 2, Outcome: outcome, Err: err})
		if err != nil {
			problems = append(problems, fmt.Sprintf("row %d: %v", index+2, err))
		}
	}
	if len(problems) > 0 {
		return results, fmt.Errorf("persist result CSV: %s", strings.Join(problems, "; "))
	}
	return results, nil
}
