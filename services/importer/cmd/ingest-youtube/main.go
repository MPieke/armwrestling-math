package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
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

func run() int {
	var videoIDs repeatedStrings
	matchNaturalKey := flag.String("match-natural-key", "", "existing match natural key")
	maxVideos := flag.Int("max-videos", 10, "maximum videos to analyze")
	searchPageSize := flag.Int("search-page-size", 10, "results requested per deterministic query")
	flag.Var(&videoIDs, "video-id", "explicit YouTube video ID; repeatable")
	flag.Parse()
	required := []string{"DATABASE_URL", "YOUTUBE_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL"}
	for _, name := range required {
		if os.Getenv(name) == "" {
			fmt.Fprintf(os.Stderr, "%s is required\n", name)
			return 2
		}
	}
	if *matchNaturalKey == "" || *maxVideos < 1 || *searchPageSize < 1 {
		fmt.Fprintln(os.Stderr, "--match-natural-key and positive limits are required")
		return 2
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	defer pool.Close()
	youtubeBaseURL := os.Getenv("YOUTUBE_API_BASE_URL")
	if youtubeBaseURL == "" {
		youtubeBaseURL = "https://www.googleapis.com"
	}
	geminiBaseURL := os.Getenv("GEMINI_API_BASE_URL")
	if geminiBaseURL == "" {
		geminiBaseURL = "https://generativelanguage.googleapis.com"
	}
	result, err := youtubeingest.Run(ctx, pool,
		youtube.Client{HTTPClient: http.DefaultClient, BaseURL: youtubeBaseURL, APIKey: os.Getenv("YOUTUBE_API_KEY")},
		youtube.GeminiClient{HTTPClient: http.DefaultClient, BaseURL: geminiBaseURL, APIKey: os.Getenv("GEMINI_API_KEY"), Model: os.Getenv("GEMINI_MODEL")},
		youtubeingest.Options{MatchNaturalKey: *matchNaturalKey, VideoIDs: videoIDs, MaxVideos: *maxVideos, SearchPageSize: *searchPageSize},
	)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	fmt.Printf("selected=%d completed=%d failed=%d skipped=%d\n", result.Selected, result.Completed, result.Failed, result.Skipped)
	return 0
}
