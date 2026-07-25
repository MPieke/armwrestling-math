package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
	"github.com/mpieke/armwrestling-math/services/importer/internal/legacy"
)

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		return fmt.Errorf("DATABASE_URL is required")
	}
	batch, err := legacy.BuildBatch(evidencePaths(os.Getenv("LEGACY_EVIDENCE_PATHS")))
	if err != nil {
		return err
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return fmt.Errorf("connect to database: %w", err)
	}
	defer pool.Close()
	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("ping database: %w", err)
	}
	result, err := ingest.Run(ctx, pool, batch)
	if err != nil {
		return err
	}
	log.Printf("completed ingestion run %d: athletes=%d sources=%d claims=%d", result.RunID, result.Athletes, result.Sources, result.Claims)
	return nil
}

func evidencePaths(value string) []string {
	if value == "" {
		return []string{
			"../../data/app/ermes_morozov_evidence_v1.json",
			"../../data/app/ermes_morozov_expanded_evidence_v1.json",
		}
	}
	paths := strings.Split(value, string(os.PathListSeparator))
	result := make([]string, 0, len(paths))
	for _, path := range paths {
		if path != "" {
			result = append(result, path)
		}
	}
	return result
}
