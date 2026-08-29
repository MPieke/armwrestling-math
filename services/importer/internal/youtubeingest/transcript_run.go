package youtubeingest

import (
	"context"
	"log/slog"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
	"github.com/mpieke/armwrestling-math/services/importer/internal/matchup"
	"github.com/mpieke/armwrestling-math/services/importer/internal/research"
	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtube"
)

func RunTranscript(ctx context.Context, pool *pgxpool.Pool, youtubeClient youtube.Client, audioSource transcript.AudioSource, transcriber transcript.TranscriptionProvider, extractor transcript.ClaimExtractor, options Options) (Result, error) {
	logger := options.Logger
	if logger == nil {
		logger = slog.Default()
	}
	if options.AudioTimeout <= 0 {
		options.AudioTimeout = 15 * time.Minute
	}
	matchContext, err := matchup.Resolve(ctx, pool, options.MatchNaturalKey)
	if err != nil {
		logger.Error("match resolution failed", "error", err)
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
			started := time.Now()
			logger.Info("YouTube search started", "query", query, "result_limit", options.SearchPageSize)
			candidates, err := youtubeClient.Search(ctx, query, options.SearchPageSize)
			if err != nil {
				logger.Error("YouTube search failed", "query", query, "duration", time.Since(started), "error", err)
				return Result{}, err
			}
			logger.Info("YouTube search completed", "query", query, "candidates", len(candidates), "duration", time.Since(started))
			lists = append(lists, candidates)
		}
		selected = research.Select(lists, options.MaxVideos)
	}
	result := Result{Selected: len(selected)}
	logger.Info("candidates selected", "selected", len(selected))
	for _, candidate := range selected {
		video, err := youtubeClient.Video(ctx, candidate.VideoID)
		if err != nil {
			logger.Error("video metadata lookup failed", "video_id", candidate.VideoID, "error", err)
			result.Failed++
			continue
		}
		exists, err := ingest.CompletedExtractionExists(ctx, pool, matchContext.NaturalKey, "youtube", video.ID, "openai", extractorModel(extractor), youtube.PromptVersion)
		if err != nil {
			return result, err
		}
		if exists {
			logger.Info("video skipped because extraction already exists", "video_id", video.ID)
			result.Skipped++
			continue
		}
		extractedAt := time.Now().UTC()
		logger.Info("audio acquisition started", "video_id", video.ID)
		audioStarted := time.Now()
		audioContext, cancelAudio := context.WithTimeout(ctx, options.AudioTimeout)
		audio, err := audioSource.Acquire(audioContext, video.URL)
		cancelAudio()
		if err != nil {
			logger.Error("audio acquisition failed", "video_id", video.ID, "duration", time.Since(audioStarted), "error", err)
			if _, submitErr := ingest.Submit(ctx, pool, youtube.FailedTranscriptSubmission(video, matchContext.NaturalKey, extractorModel(extractor), candidate.MatchedQueries, extractedAt, err)); submitErr != nil {
				return result, submitErr
			}
			result.Failed++
			continue
		}
		logger.Info("audio acquisition completed", "video_id", video.ID, "duration", time.Since(audioStarted))
		transcriptionStarted := time.Now()
		logger.Info("transcription started", "video_id", video.ID)
		transcribed, rawTranscript, usage, err := transcriber.Transcribe(ctx, audio, matchContext.Competitors)
		if cleanupErr := audioSource.Cleanup(audio); cleanupErr != nil {
			logger.Warn("audio cleanup failed", "video_id", video.ID, "error", cleanupErr)
		}
		if err != nil {
			logger.Error("transcription failed", "video_id", video.ID, "duration", time.Since(transcriptionStarted), "error", err)
			if _, submitErr := ingest.Submit(ctx, pool, youtube.FailedTranscriptSubmission(video, matchContext.NaturalKey, extractorModel(extractor), candidate.MatchedQueries, extractedAt, err)); submitErr != nil {
				return result, submitErr
			}
			result.Failed++
			continue
		}
		logger.Info("transcription completed", "video_id", video.ID, "duration", time.Since(transcriptionStarted), "segments", len(transcribed.Segments))
		extractionStarted := time.Now()
		logger.Info("claim extraction started", "video_id", video.ID, "model", extractorModel(extractor))
		structured, rawExtraction, extractionUsage, err := extractor.Extract(ctx, transcribed, transcript.MatchContext{NaturalKey: matchContext.NaturalKey, Competitors: matchContext.Competitors, Arm: matchContext.Arm})
		if err != nil {
			logger.Error("claim extraction failed", "video_id", video.ID, "duration", time.Since(extractionStarted), "error", err)
			if _, submitErr := ingest.Submit(ctx, pool, youtube.FailedTranscriptSubmission(video, matchContext.NaturalKey, extractorModel(extractor), candidate.MatchedQueries, extractedAt, err)); submitErr != nil {
				return result, submitErr
			}
			result.Failed++
			continue
		}
		logger.Info("claim extraction completed", "video_id", video.ID, "duration", time.Since(extractionStarted), "claims", len(structured.Claims))
		submission, err := youtube.TranscriptSubmission(video, matchContext.NaturalKey, structured, rawExtraction, extractionUsage, matchContext.Competitors, extractorModel(extractor), candidate.MatchedQueries, extractedAt)
		if err != nil {
			result.Failed++
			continue
		}
		if _, err := ingest.Submit(ctx, pool, submission); err != nil {
			return result, err
		}
		_ = rawTranscript
		_ = usage
		logger.Info("transcript-derived evidence persisted", "video_id", video.ID, "claims", len(structured.Claims))
		result.Completed++
	}
	logger.Info("ingestion completed", "selected", result.Selected, "completed", result.Completed, "failed", result.Failed, "skipped", result.Skipped)
	return result, nil
}

type modelProvider interface{ ModelName() string }

func extractorModel(extractor transcript.ClaimExtractor) string {
	if provider, ok := extractor.(modelProvider); ok {
		return provider.ModelName()
	}
	return "openai"
}
