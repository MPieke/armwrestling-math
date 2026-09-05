package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/config"
	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtube"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtubeingest"
)

type repeatedStrings []string

func (values *repeatedStrings) String() string { return strings.Join(*values, ",") }
func (values *repeatedStrings) Set(value string) error {
	if value == "" {
		return fmt.Errorf("video ID cannot be empty")
	}
	*values = append(*values, value)
	return nil
}

func main() {
	os.Exit(run())
}

// transcriptionProvider selects OpenAI's API or a self-hosted whisper.cpp
// server per TRANSCRIPTION_PROVIDER: the choice that lets local dev run
// against a fast, free, Metal-accelerated native whisper-server while CI
// runs the portable Docker image, without either environment needing a
// different code path.
func transcriptionProvider(httpClient *http.Client, configuration config.Config) transcript.TranscriptionProvider {
	if configuration.TranscriptionProvider == config.TranscriptionProviderWhisper {
		return transcript.WhisperCPPTranscriber{HTTPClient: httpClient, BaseURL: configuration.WhisperServerBaseURL}
	}
	return transcript.OpenAITranscriber{HTTPClient: httpClient, BaseURL: configuration.OpenAIAPIBaseURL, APIKey: configuration.OpenAIAPIKey, Model: configuration.OpenAITranscriptionModel}
}

func run() int {
	var videoIDs repeatedStrings
	matchNaturalKey := flag.String("match-natural-key", "", "existing match natural key")
	maxVideos := flag.Int("max-videos", 10, "maximum videos to analyze")
	searchPageSize := flag.Int("search-page-size", 10, "results requested per deterministic query")
	flag.Var(&videoIDs, "video-id", "explicit YouTube video ID; repeatable")
	flag.Parse()
	if *matchNaturalKey == "" || *maxVideos < 1 || *searchPageSize < 1 {
		fmt.Fprintln(os.Stderr, "--match-natural-key and positive limits are required")
		return 2
	}
	configuration, err := config.Load(os.Getenv)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
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
	result, err := youtubeingest.Run(ctx, pool,
		youtube.Client{HTTPClient: httpClient, BaseURL: configuration.YouTubeAPIBaseURL, APIKey: configuration.YouTubeAPIKey},
		transcript.YTDLPAudioSource{Command: os.Getenv("YTDLP_COMMAND")},
		transcriptionProvider(httpClient, configuration),
		transcript.OpenAIClaimExtractor{HTTPClient: httpClient, BaseURL: configuration.OpenAIAPIBaseURL, APIKey: configuration.OpenAIAPIKey, Model: configuration.OpenAIExtractionModel},
		youtubeingest.Options{MatchNaturalKey: *matchNaturalKey, VideoIDs: videoIDs, MaxVideos: *maxVideos, SearchPageSize: *searchPageSize, AudioTimeout: configuration.AudioTimeout, Logger: logger},
	)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	fmt.Printf("selected=%d completed=%d failed=%d skipped=%d\n", result.Selected, result.Completed, result.Failed, result.Skipped)
	return 0
}
