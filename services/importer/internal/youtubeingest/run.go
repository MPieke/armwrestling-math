package youtubeingest

import (
	"context"
	"fmt"
	"log/slog"
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
	Logger          *slog.Logger
}

type Result struct {
	Selected  int
	Completed int
	Failed    int
	Skipped   int
}

func Run(ctx context.Context, pool *pgxpool.Pool, youtubeClient youtube.Client, geminiClient youtube.GeminiClient, options Options) (Result, error) {
	logger := options.Logger
	if logger == nil {
		logger = slog.Default()
	}
	logger.Info("ingestion started", "match_natural_key", options.MatchNaturalKey, "explicit_video_ids", len(options.VideoIDs), "max_videos", options.MaxVideos)
	matchContext, err := matchup.Resolve(ctx, pool, options.MatchNaturalKey)
	if err != nil {
		logger.Error("match resolution failed", "error", err)
		return Result{}, err
	}
	logger.Info("match resolved", "match_natural_key", matchContext.NaturalKey, "competitors", matchContext.Competitors, "arm", matchContext.Arm)
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
			started := time.Now()
			logger.Info("YouTube search started", "query", query, "result_limit", options.SearchPageSize)
			candidates, err := youtubeClient.Search(ctx, query, options.SearchPageSize)
			if err != nil {
				logger.Error("YouTube search failed", "query", query, "duration", time.Since(started), "error", err)
				return Result{}, fmt.Errorf("search YouTube for %q: %w", query, err)
			}
			logger.Info("YouTube search completed", "query", query, "candidates", len(candidates), "duration", time.Since(started))
			lists = append(lists, candidates)
		}
		selected = research.Select(lists, options.MaxVideos)
	}
	result := Result{Selected: len(selected)}
	logger.Info("candidates selected", "selected", len(selected))
	for _, candidate := range selected {
		started := time.Now()
		logger.Info("video metadata lookup started", "video_id", candidate.VideoID)
		video, err := youtubeClient.Video(ctx, candidate.VideoID)
		if err != nil {
			logger.Error("video metadata lookup failed", "video_id", candidate.VideoID, "duration", time.Since(started), "error", err)
			result.Failed++
			continue
		}
		logger.Info("video metadata lookup completed", "video_id", video.ID, "title", video.Title, "duration", time.Since(started))
		exists, err := ingest.CompletedExtractionExists(ctx, pool, matchContext.NaturalKey, "youtube", video.ID, "gemini", geminiClient.Model, youtube.PromptVersion)
		if err != nil {
			logger.Error("completed extraction lookup failed", "video_id", video.ID, "error", err)
			return result, err
		}
		if exists {
			logger.Info("video skipped because extraction already exists", "video_id", video.ID)
			result.Skipped++
			continue
		}
		extractedAt := time.Now().UTC()
		started = time.Now()
		logger.Info("Gemini extraction started", "video_id", video.ID, "model", geminiClient.Model)
		analysis, analysisErr := geminiClient.Analyze(ctx, video, matchContext.Competitors, matchContext.Arm)
		if analysisErr != nil {
			logger.Error("Gemini extraction failed", "video_id", video.ID, "duration", time.Since(started), "error", analysisErr)
			if _, err := ingest.Submit(ctx, pool, youtube.FailedSubmission(video, matchContext.NaturalKey, geminiClient.Model, candidate.MatchedQueries, extractedAt, analysisErr)); err != nil {
				logger.Error("failed extraction audit persistence failed", "video_id", video.ID, "error", err)
				return result, err
			}
			logger.Info("failed extraction audited", "video_id", video.ID)
			result.Failed++
			continue
		}
		logger.Info("Gemini extraction completed", "video_id", video.ID, "duration", time.Since(started), "claims", len(analysis.Output.Claims))
		submission, err := youtube.Submission(video, matchContext.NaturalKey, analysis, matchContext.Competitors, geminiClient.Model, candidate.MatchedQueries, extractedAt)
		if err != nil {
			logger.Error("extraction mapping failed", "video_id", video.ID, "error", err)
			if _, submitErr := ingest.Submit(ctx, pool, youtube.FailedSubmission(video, matchContext.NaturalKey, geminiClient.Model, candidate.MatchedQueries, extractedAt, err)); submitErr != nil {
				return result, submitErr
			}
			result.Failed++
			continue
		}
		if _, err := ingest.Submit(ctx, pool, submission); err != nil {
			logger.Error("evidence persistence failed", "video_id", video.ID, "error", err)
			return result, err
		}
		logger.Info("evidence persisted", "video_id", video.ID)
		result.Completed++
	}
	logger.Info("ingestion completed", "selected", result.Selected, "completed", result.Completed, "failed", result.Failed, "skipped", result.Skipped)
	return result, nil
}
