package youtubeingest

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
	"github.com/mpieke/armwrestling-math/services/importer/internal/matchup"
	"github.com/mpieke/armwrestling-math/services/importer/internal/research"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtube"
)

type Options struct {
	MatchNaturalKey string
	VideoIDs        []string
	MaxVideos       int
	SearchPageSize  int
}

type Result struct {
	Selected  int
	Completed int
	Failed    int
	Skipped   int
}

func Run(ctx context.Context, pool *pgxpool.Pool, youtubeClient youtube.Client, geminiClient youtube.GeminiClient, options Options) (Result, error) {
	matchContext, err := matchup.Resolve(ctx, pool, options.MatchNaturalKey)
	if err != nil {
		return Result{}, err
	}
	var selected []research.Candidate
	if len(options.VideoIDs) > 0 {
		for _, videoID := range options.VideoIDs {
			selected = append(selected, research.Candidate{VideoID: videoID, MatchedQueries: []string{"explicit-video-id"}})
		}
		selected = research.Select([][]research.Candidate{selected}, options.MaxVideos)
	} else {
		queries, err := research.BuildPlan(matchContext)
		if err != nil {
			return Result{}, err
		}
		lists := make([][]research.Candidate, 0, len(queries))
		for _, query := range queries {
			candidates, err := youtubeClient.Search(ctx, query, options.SearchPageSize)
			if err != nil {
				return Result{}, fmt.Errorf("search YouTube for %q: %w", query, err)
			}
			lists = append(lists, candidates)
		}
		selected = research.Select(lists, options.MaxVideos)
	}
	result := Result{Selected: len(selected)}
	for _, candidate := range selected {
		video, err := youtubeClient.Video(ctx, candidate.VideoID)
		if err != nil {
			result.Failed++
			continue
		}
		exists, err := ingest.CompletedExtractionExists(ctx, pool, matchContext.NaturalKey, "youtube", video.ID, "gemini", geminiClient.Model, youtube.PromptVersion)
		if err != nil {
			return result, err
		}
		if exists {
			result.Skipped++
			continue
		}
		extractedAt := time.Now().UTC()
		analysis, analysisErr := geminiClient.Analyze(ctx, video, matchContext.Competitors, matchContext.Arm)
		if analysisErr != nil {
			if _, err := ingest.Submit(ctx, pool, youtube.FailedSubmission(video, matchContext.NaturalKey, geminiClient.Model, candidate.MatchedQueries, extractedAt, analysisErr)); err != nil {
				return result, err
			}
			result.Failed++
			continue
		}
		submission, err := youtube.Submission(video, matchContext.NaturalKey, analysis, matchContext.Competitors, geminiClient.Model, candidate.MatchedQueries, extractedAt)
		if err != nil {
			if _, submitErr := ingest.Submit(ctx, pool, youtube.FailedSubmission(video, matchContext.NaturalKey, geminiClient.Model, candidate.MatchedQueries, extractedAt, err)); submitErr != nil {
				return result, submitErr
			}
			result.Failed++
			continue
		}
		if _, err := ingest.Submit(ctx, pool, submission); err != nil {
			return result, err
		}
		result.Completed++
	}
	return result, nil
}
