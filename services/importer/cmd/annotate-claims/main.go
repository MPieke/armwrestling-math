package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/annotate"
	"github.com/mpieke/armwrestling-math/services/importer/internal/annotateclaims"
	"github.com/mpieke/armwrestling-math/services/importer/internal/config"
)

func main() {
	os.Exit(run())
}

func run() int {
	promptVersion := flag.String("prompt-version", "v1", "annotation prompt version")
	flag.Parse()

	configuration, err := config.Load(os.Getenv)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	annotationModel := os.Getenv("OPENAI_ANNOTATION_MODEL")
	if annotationModel == "" {
		annotationModel = configuration.OpenAIExtractionModel
	}
	var logHandler slog.Handler
	logOptions := &slog.HandlerOptions{Level: configuration.LogLevel}
	if configuration.LogFormat == "json" {
		logHandler = slog.NewJSONHandler(os.Stderr, logOptions)
	} else {
		logHandler = slog.NewTextHandler(os.Stderr, logOptions)
	}
	logger := slog.New(logHandler)
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, configuration.DatabaseURL)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	defer pool.Close()
	httpClient := &http.Client{Timeout: configuration.HTTPTimeout}
	result, err := annotateclaims.Run(ctx, pool,
		annotate.OpenAIAnnotator{HTTPClient: httpClient, BaseURL: configuration.OpenAIAPIBaseURL, APIKey: configuration.OpenAIAPIKey, Model: annotationModel},
		annotateclaims.Options{PromptVersion: *promptVersion, Logger: logger},
	)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	fmt.Printf("selected=%d completed=%d failed=%d\n", result.Selected, result.Completed, result.Failed)
	return 0
}
