package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/resultsloader"
)

func main() { os.Exit(run()) }

func run() int {
	fileName := flag.String("file", "", "CSV results file")
	flag.Parse()
	if *fileName == "" || os.Getenv("DATABASE_URL") == "" {
		fmt.Fprintln(os.Stderr, "--file and DATABASE_URL are required")
		return 2
	}
	file, err := os.Open(*fileName)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	defer file.Close()
	submissions, err := resultsloader.Parse(file, *fileName)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	pool, err := pgxpool.New(context.Background(), os.Getenv("DATABASE_URL"))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	defer pool.Close()
	results, err := resultsloader.SubmitAll(context.Background(), pool, submissions)
	for _, result := range results {
		if result.Err != nil {
			fmt.Fprintf(os.Stderr, "row %d failed: %v\n", result.RowNumber, result.Err)
			continue
		}
		fmt.Printf("row %d completed: event_id=%d match_id=%d\n", result.RowNumber, result.Outcome.EventID, result.Outcome.MatchID)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	return 0
}
