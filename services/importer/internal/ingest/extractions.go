package ingest

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
)

func CompletedExtractionExists(ctx context.Context, pool *pgxpool.Pool, matchNaturalKey, sourceType, externalID, provider, model, promptVersion string) (bool, error) {
	return dbgen.New(pool).CompletedExtractionExists(ctx, dbgen.CompletedExtractionExistsParams{
		NaturalKey: matchNaturalKey, SourceType: sourceType, ExternalID: externalID,
		Provider: provider, Model: model, PromptVersion: promptVersion,
	})
}
