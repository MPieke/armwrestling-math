package ingest

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/dbgen"
)

const EvidenceSubmissionSchemaVersion = "evidence-submission-v1"

func Submit(ctx context.Context, databasePool *pgxpool.Pool, submission EvidenceSubmission) (result Result, err error) {
	if err := ValidateEvidence(submission); err != nil {
		return Result{}, err
	}
	databaseQueries := dbgen.New(databasePool)
	match, err := databaseQueries.GetMatchByNaturalKey(ctx, submission.MatchNaturalKey)
	if err != nil {
		if err == pgx.ErrNoRows {
			return Result{}, fmt.Errorf("match not found: %s", submission.MatchNaturalKey)
		}
		return Result{}, fmt.Errorf("resolve match %q: %w", submission.MatchNaturalKey, err)
	}
	competitors, err := databaseQueries.ListMatchCompetitors(ctx, match.ID)
	if err != nil {
		return Result{}, fmt.Errorf("list match competitors: %w", err)
	}
	competitorIDs := make(map[string]int64, len(competitors))
	for _, competitor := range competitors {
		competitorIDs[competitor.CanonicalName] = competitor.ID
	}
	if len(competitorIDs) == 0 {
		return Result{}, fmt.Errorf("match has no competitors: %s", submission.MatchNaturalKey)
	}
	if err := validateEvidenceSubjects(submission, competitorIDs); err != nil {
		return Result{}, err
	}

	runID, err := databaseQueries.CreateIngestionRun(ctx, submission.BatchKey)
	if err != nil {
		return Result{}, fmt.Errorf("create ingestion run: %w", err)
	}
	result = Result{RunID: runID, Sources: len(submission.Sources), Claims: len(submission.Claims)}
	transaction, err := databasePool.Begin(ctx)
	if err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	defer func() { _ = transaction.Rollback(ctx) }()
	transactionQueries := databaseQueries.WithTx(transaction)
	if err := submitEvidence(ctx, transactionQueries, match.ID, competitorIDs, submission); err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transactionQueries.CompleteIngestionRun(ctx, dbgen.CompleteIngestionRunParams{ID: runID, Summary: evidenceSummary(result)}); err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	if err := transaction.Commit(ctx); err != nil {
		return result, failRun(ctx, databaseQueries, runID, err)
	}
	return result, nil
}

func ValidateEvidence(submission EvidenceSubmission) error {
	problems := make([]string, 0)
	if submission.SchemaVersion != EvidenceSubmissionSchemaVersion {
		problems = append(problems, "unsupported evidence submission schema version")
	}
	if submission.BatchKey == "" || submission.MatchNaturalKey == "" {
		problems = append(problems, "evidence submission requires batch key and match natural key")
	}
	sources := make(map[string]struct{}, len(submission.Sources))
	for _, source := range submission.Sources {
		if source.Key == "" || source.SourceType == "" || source.ExternalID == "" || source.URL == "" {
			problems = append(problems, "sources require key, type, external ID, and URL")
			continue
		}
		if _, exists := sources[source.Key]; exists {
			problems = append(problems, "duplicate source key: "+source.Key)
		}
		sources[source.Key] = struct{}{}
	}
	extractions := make(map[string]SourceExtractionInput, len(submission.Extractions))
	for _, extraction := range submission.Extractions {
		if extraction.Key == "" || extraction.SourceKey == "" || extraction.Provider == "" ||
			extraction.Model == "" || extraction.PromptVersion == "" || extraction.ExtractedAt.IsZero() {
			problems = append(problems, "extractions require key, source, provider, model, prompt version, and extracted-at")
		}
		if extraction.Status != "completed" && extraction.Status != "failed" {
			problems = append(problems, "extraction status must be completed or failed")
		}
		if extraction.Status == "failed" && extraction.ErrorMessage == nil {
			problems = append(problems, "failed extraction requires an error message")
		}
		if extraction.Status == "completed" && extraction.ErrorMessage != nil {
			problems = append(problems, "completed extraction cannot contain an error message")
		}
		if _, exists := sources[extraction.SourceKey]; !exists {
			problems = append(problems, "extraction references unknown source: "+extraction.SourceKey)
		}
		if _, exists := extractions[extraction.Key]; exists {
			problems = append(problems, "duplicate extraction key: "+extraction.Key)
		}
		extractions[extraction.Key] = extraction
	}
	for index, claim := range submission.Claims {
		if claim.SourceKey == "" || claim.Text == "" || claim.ExtractedAt.IsZero() {
			problems = append(problems, fmt.Sprintf("claim %d requires source, text, and extracted-at", index))
		}
		if _, exists := sources[claim.SourceKey]; !exists {
			problems = append(problems, fmt.Sprintf("claim %d references unknown source: %s", index, claim.SourceKey))
		}
		if len(claim.SubjectNames) == 0 {
			problems = append(problems, fmt.Sprintf("claim %d requires at least one subject", index))
		}
		if claim.ExtractionKey != "" {
			extraction, exists := extractions[claim.ExtractionKey]
			if !exists {
				problems = append(problems, fmt.Sprintf("claim %d references unknown extraction: %s", index, claim.ExtractionKey))
			} else if extraction.Status != "completed" || extraction.SourceKey != claim.SourceKey {
				problems = append(problems, fmt.Sprintf("claim %d extraction must be completed and reference the same source", index))
			}
		}
	}
	if len(problems) == 0 {
		return nil
	}
	sort.Strings(problems)
	return fmt.Errorf("invalid evidence submission: %s", strings.Join(problems, "; "))
}

func validateEvidenceSubjects(submission EvidenceSubmission, competitorIDs map[string]int64) error {
	for index, claim := range submission.Claims {
		for _, subjectName := range claim.SubjectNames {
			if _, exists := competitorIDs[subjectName]; !exists {
				return fmt.Errorf("claim %d subject is not a match competitor: %s", index, subjectName)
			}
		}
	}
	return nil
}

func submitEvidence(ctx context.Context, queries *dbgen.Queries, matchID int64, competitorIDs map[string]int64, submission EvidenceSubmission) error {
	sourceIDs := make(map[string]int64, len(submission.Sources))
	for _, source := range submission.Sources {
		id, err := queries.UpsertSource(ctx, dbgen.UpsertSourceParams{
			SourceType:  source.SourceType,
			ExternalID:  source.ExternalID,
			Url:         source.URL,
			Title:       textPointer(source.Title),
			PublishedAt: timeValue(source.PublishedAt),
			RawPayload:  source.RawPayload,
		})
		if err != nil {
			return fmt.Errorf("upsert source %q: %w", source.Key, err)
		}
		sourceIDs[source.Key] = id
	}
	extractionIDs := make(map[string]int64, len(submission.Extractions))
	for _, extraction := range submission.Extractions {
		id, err := queries.CreateSourceExtraction(ctx, dbgen.CreateSourceExtractionParams{
			SourceID: sourceIDs[extraction.SourceKey], MatchID: matchID,
			Provider: extraction.Provider, Model: extraction.Model, PromptVersion: extraction.PromptVersion,
			Status: extraction.Status, ExtractedAt: timeValue(&extraction.ExtractedAt),
			RawResponse: extraction.RawResponse, Usage: extraction.Usage, ErrorMessage: textPointer(extraction.ErrorMessage),
		})
		if err != nil {
			return fmt.Errorf("create source extraction %q: %w", extraction.Key, err)
		}
		extractionIDs[extraction.Key] = id
	}
	for _, claim := range submission.Claims {
		claimID, err := queries.UpsertClaim(ctx, dbgen.UpsertClaimParams{
			SourceID:           sourceIDs[claim.SourceKey],
			MatchID:            matchID,
			ClaimText:          claim.Text,
			TimestampSeconds:   intPointer(claim.TimestampSeconds),
			Speaker:            textPointer(claim.Speaker),
			Confidence:         textPointer(claim.Confidence),
			Relevance:          textPointer(claim.Relevance),
			ObservedAt:         timeValue(claim.ObservedAt),
			ExtractedAt:        timeValue(&claim.ExtractedAt),
			ExtractionModel:    textPointer(&claim.ExtractionModel),
			RawPayload:         claim.RawPayload,
			SourceExtractionID: int64Value(extractionIDs[claim.ExtractionKey], claim.ExtractionKey != ""),
		})
		if err != nil {
			return fmt.Errorf("upsert claim %q: %w", claim.Text, err)
		}
		for _, subjectName := range claim.SubjectNames {
			if err := queries.LinkClaimSubject(ctx, dbgen.LinkClaimSubjectParams{ClaimID: claimID, AthleteID: competitorIDs[subjectName]}); err != nil {
				return fmt.Errorf("link claim subject %q: %w", subjectName, err)
			}
		}
	}
	return nil
}

func evidenceSummary(result Result) []byte {
	return []byte(fmt.Sprintf(`{"sources":%d,"claims":%d}`, result.Sources, result.Claims))
}
