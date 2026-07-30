package matchup

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
	"github.com/mpieke/armwrestling-math/services/importer/internal/research"
)

func Resolve(ctx context.Context, pool *pgxpool.Pool, naturalKey string) (research.MatchContext, error) {
	queries := dbgen.New(pool)
	match, err := queries.GetMatchByNaturalKey(ctx, naturalKey)
	if err != nil {
		if err == pgx.ErrNoRows {
			return research.MatchContext{}, fmt.Errorf("match not found: %s", naturalKey)
		}
		return research.MatchContext{}, err
	}
	rows, err := queries.ListMatchCompetitors(ctx, match.ID)
	if err != nil {
		return research.MatchContext{}, err
	}
	competitors := make([]string, 0, len(rows))
	for _, row := range rows {
		competitors = append(competitors, row.CanonicalName)
	}
	if len(competitors) != 2 {
		return research.MatchContext{}, fmt.Errorf("match %s requires exactly two competitors", naturalKey)
	}
	return research.MatchContext{NaturalKey: naturalKey, Arm: match.Arm, Competitors: competitors}, nil
}
