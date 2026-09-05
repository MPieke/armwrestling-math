package youtubeingest

import (
	"context"
	"log/slog"
	"math"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
	"github.com/mpieke/armwrestling-math/services/importer/internal/matchup"
	"github.com/mpieke/armwrestling-math/services/importer/internal/research"
	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtube"
)

type Options struct {
	MatchNaturalKey string
	VideoIDs        []string
	MaxVideos       int
	SearchPageSize  int
	AudioTimeout    time.Duration
	Logger          *slog.Logger
}

type Result struct {
	Selected  int
	Completed int
	Failed    int
	Skipped   int
}

func Run(ctx context.Context, pool *pgxpool.Pool, youtubeClient youtube.Client, audioSource transcript.AudioSource, transcriber transcript.TranscriptionProvider, extractor transcript.ClaimExtractor, options Options) (Result, error) {
	logger := options.Logger
	if logger == nil {
		logger = slog.Default()
	}
	if options.AudioTimeout <= 0 {
		options.AudioTimeout = 15 * time.Minute
	}
	logger.Info("ingestion started", "match_natural_key", options.MatchNaturalKey, "explicit_video_ids", len(options.VideoIDs), "max_videos", options.MaxVideos)
	matchContext, err := matchup.Resolve(ctx, pool, options.MatchNaturalKey)
	if err != nil {
		logger.Error("match resolution failed", "error", err)
		return Result{}, err
	}
	logger.Info("match resolved", "match_natural_key", matchContext.NaturalKey, "competitors", matchContext.Competitors, "arm", matchContext.Arm)
	selected, err := selectCandidates(ctx, youtubeClient, matchContext, options, logger)
	if err != nil {
		return Result{}, err
	}
	result := Result{Selected: len(selected)}
	logger.Info("candidates selected", "selected", len(selected))
	for _, candidate := range selected {
		if err := ingestCandidate(ctx, pool, youtubeClient, audioSource, transcriber, extractor, matchContext, candidate, options, logger, &result); err != nil {
			return result, err
		}
	}
	logger.Info("ingestion completed", "selected", result.Selected, "completed", result.Completed, "failed", result.Failed, "skipped", result.Skipped)
	return result, nil
}

// selectCandidates always includes every explicit VideoID (guaranteed, not
// merely preferred -- an operator who names a video wants it processed).
// It also searches for additional candidates whenever there's room left
// under MaxVideos, so a known "full match" video no longer forecloses
// discovering separate interview/analysis/breakdown videos about the same
// match. It skips the search entirely (no YouTube quota spent, no added
// latency) when the explicit list already fills MaxVideos on its own.
func selectCandidates(ctx context.Context, youtubeClient youtube.Client, matchContext research.MatchContext, options Options, logger *slog.Logger) ([]research.Candidate, error) {
	var lists [][]research.Candidate
	if len(options.VideoIDs) > 0 {
		explicit := make([]research.Candidate, 0, len(options.VideoIDs))
		for _, videoID := range options.VideoIDs {
			explicit = append(explicit, research.Candidate{VideoID: videoID, MatchedQueries: []string{"explicit-video-id"}})
		}
		lists = append(lists, explicit)
	}
	if len(options.VideoIDs) < options.MaxVideos {
		searchLists, err := searchCandidates(ctx, youtubeClient, matchContext, options, logger)
		if err != nil {
			return nil, err
		}
		lists = append(lists, searchLists...)
	}
	return research.Select(lists, options.MaxVideos), nil
}

func searchCandidates(ctx context.Context, youtubeClient youtube.Client, matchContext research.MatchContext, options Options, logger *slog.Logger) ([][]research.Candidate, error) {
	queries, err := research.BuildPlan(matchContext)
	if err != nil {
		return nil, err
	}
	lists := make([][]research.Candidate, 0, len(queries))
	for _, query := range queries {
		started := time.Now()
		logger.Info("YouTube search started", "query", query, "result_limit", options.SearchPageSize)
		candidates, err := youtubeClient.Search(ctx, query, options.SearchPageSize)
		if err != nil {
			logger.Error("YouTube search failed", "query", query, "duration", time.Since(started), "error", err)
			return nil, err
		}
		logger.Info("YouTube search completed", "query", query, "candidates", len(candidates), "duration", time.Since(started))
		lists = append(lists, candidates)
	}
	return lists, nil
}

func ingestCandidate(ctx context.Context, pool *pgxpool.Pool, youtubeClient youtube.Client, audioSource transcript.AudioSource, transcriber transcript.TranscriptionProvider, extractor transcript.ClaimExtractor, matchContext research.MatchContext, candidate research.Candidate, options Options, logger *slog.Logger, result *Result) error {
	metadataStarted := time.Now()
	logger.Info("video metadata lookup started", "video_id", candidate.VideoID)
	video, err := youtubeClient.Video(ctx, candidate.VideoID)
	if err != nil {
		logger.Error("video metadata lookup failed", "video_id", candidate.VideoID, "duration", time.Since(metadataStarted), "error", err)
		result.Failed++
		return nil
	}
	logger.Info("video metadata lookup completed", "video_id", video.ID, "title", video.Title, "duration", time.Since(metadataStarted))
	model := extractorModel(extractor)
	exists, err := ingest.CompletedExtractionExists(ctx, pool, matchContext.NaturalKey, "youtube", video.ID, "openai", model, youtube.PromptVersion)
	if err != nil {
		return err
	}
	if exists {
		logger.Info("video skipped because extraction already exists", "video_id", video.ID)
		result.Skipped++
		return nil
	}
	extractedAt := time.Now().UTC()
	audio, err := acquireAudio(ctx, audioSource, video, options.AudioTimeout, logger)
	if err != nil {
		return auditFailure(ctx, pool, video, matchContext.NaturalKey, model, candidate.MatchedQueries, extractedAt, err, logger, result)
	}
	transcribed, rawTranscript, transcriptionUsage, err := transcribe(ctx, audioSource, transcriber, audio, video, matchContext.Competitors, logger)
	if err != nil {
		return auditFailure(ctx, pool, video, matchContext.NaturalKey, model, candidate.MatchedQueries, extractedAt, err, logger, result)
	}
	structured, rawExtraction, extractionUsage, err := extract(ctx, extractor, transcribed, matchContext, video, logger)
	if err != nil {
		return auditFailure(ctx, pool, video, matchContext.NaturalKey, model, candidate.MatchedQueries, extractedAt, err, logger, result)
	}
	for _, segment := range transcribed.Segments {
		if transcriptDuration := int(math.Ceil(segment.EndSeconds)); transcriptDuration > video.DurationSeconds {
			video.DurationSeconds = transcriptDuration
		}
	}
	submission, err := youtube.Submission(video, matchContext.NaturalKey, structured, rawExtraction, extractionUsage, matchContext.Competitors, model, candidate.MatchedQueries, extractedAt)
	if err != nil {
		logger.Error("evidence submission construction failed", "video_id", video.ID, "error", err)
		return auditFailure(ctx, pool, video, matchContext.NaturalKey, model, candidate.MatchedQueries, extractedAt, err, logger, result)
	}
	if _, err := ingest.Submit(ctx, pool, submission); err != nil {
		logger.Error("evidence persistence failed", "video_id", video.ID, "error", err)
		return err
	}
	_ = rawTranscript
	_ = transcriptionUsage
	logger.Info("transcript-derived evidence persisted", "video_id", video.ID, "claims", len(structured.Claims))
	result.Completed++
	return nil
}

func acquireAudio(ctx context.Context, audioSource transcript.AudioSource, video youtube.Video, timeout time.Duration, logger *slog.Logger) (transcript.AudioArtifact, error) {
	logger.Info("audio acquisition started", "video_id", video.ID)
	started := time.Now()
	audioContext, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	audio, err := audioSource.Acquire(audioContext, video.URL)
	if err != nil {
		logger.Error("audio acquisition failed", "video_id", video.ID, "duration", time.Since(started), "error", err)
		return transcript.AudioArtifact{}, err
	}
	logger.Info("audio acquisition completed", "video_id", video.ID, "duration", time.Since(started))
	return audio, nil
}

func transcribe(ctx context.Context, audioSource transcript.AudioSource, transcriber transcript.TranscriptionProvider, audio transcript.AudioArtifact, video youtube.Video, competitors []string, logger *slog.Logger) (transcript.Transcript, []byte, []byte, error) {
	started := time.Now()
	logger.Info("transcription started", "video_id", video.ID)
	transcribed, rawTranscript, usage, err := transcriber.Transcribe(ctx, audio, competitors)
	if cleanupErr := audioSource.Cleanup(audio); cleanupErr != nil {
		logger.Warn("audio cleanup failed", "video_id", video.ID, "error", cleanupErr)
	}
	if err != nil {
		logger.Error("transcription failed", "video_id", video.ID, "duration", time.Since(started), "error", err)
		return transcript.Transcript{}, nil, nil, err
	}
	logger.Info("transcription completed", "video_id", video.ID, "duration", time.Since(started), "segments", len(transcribed.Segments))
	return transcribed, rawTranscript, usage, nil
}

func extract(ctx context.Context, extractor transcript.ClaimExtractor, transcribed transcript.Transcript, matchContext research.MatchContext, video youtube.Video, logger *slog.Logger) (transcript.StructuredExtraction, []byte, []byte, error) {
	started := time.Now()
	model := extractorModel(extractor)
	logger.Info("claim extraction started", "video_id", video.ID, "model", model)
	structured, rawExtraction, usage, err := extractor.Extract(ctx, transcribed, transcript.MatchContext{NaturalKey: matchContext.NaturalKey, Competitors: matchContext.Competitors, Arm: matchContext.Arm})
	if err != nil {
		logger.Error("claim extraction failed", "video_id", video.ID, "duration", time.Since(started), "error", err)
		return transcript.StructuredExtraction{}, nil, nil, err
	}
	logger.Info("claim extraction completed", "video_id", video.ID, "duration", time.Since(started), "claims", len(structured.Claims))
	return structured, rawExtraction, usage, nil
}

func auditFailure(ctx context.Context, pool *pgxpool.Pool, video youtube.Video, matchNaturalKey, model string, matchedQueries []string, extractedAt time.Time, cause error, logger *slog.Logger, result *Result) error {
	if _, err := ingest.Submit(ctx, pool, youtube.FailedSubmission(video, matchNaturalKey, model, matchedQueries, extractedAt, cause)); err != nil {
		return err
	}
	result.Failed++
	return nil
}

type modelProvider interface{ ModelName() string }

func extractorModel(extractor transcript.ClaimExtractor) string {
	if provider, ok := extractor.(modelProvider); ok && provider.ModelName() != "" {
		return provider.ModelName()
	}
	return openAIProvider
}

const openAIProvider = "openai"
