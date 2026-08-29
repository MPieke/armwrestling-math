package youtube

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
)

func Submission(video Video, matchNaturalKey string, analysis Analysis, competitors []string, model string, matchedQueries []string, extractedAt time.Time) (ingest.EvidenceSubmission, error) {
	allowed := make(map[string]struct{}, len(competitors))
	for _, competitor := range competitors {
		allowed[competitor] = struct{}{}
	}
	if err := ValidateExtraction(analysis.Output, allowed, video.DurationSeconds); err != nil {
		return ingest.EvidenceSubmission{}, err
	}
	sourcePayload, err := json.Marshal(struct {
		Metadata       json.RawMessage `json:"metadata"`
		MatchedQueries []string        `json:"matched_queries"`
	}{Metadata: video.RawPayload, MatchedQueries: matchedQueries})
	if err != nil {
		return ingest.EvidenceSubmission{}, err
	}
	sourceKey, extractionKey := "youtube:"+video.ID, "gemini:"+video.ID+":"+model+":"+PromptVersion
	title, publishedAt := video.Title, video.PublishedAt
	submission := ingest.EvidenceSubmission{
		SchemaVersion: ingest.EvidenceSubmissionSchemaVersion, BatchKey: extractionKey, MatchNaturalKey: matchNaturalKey,
		Sources:     []ingest.SourceInput{{Key: sourceKey, SourceType: "youtube", ExternalID: video.ID, URL: video.URL, Title: &title, PublishedAt: &publishedAt, RawPayload: sourcePayload}},
		Extractions: []ingest.SourceExtractionInput{{Key: extractionKey, SourceKey: sourceKey, Provider: "gemini", Model: model, PromptVersion: PromptVersion, Status: "completed", ExtractedAt: extractedAt, RawResponse: analysis.RawResponse, Usage: analysis.Usage}},
	}
	for _, claim := range analysis.Output.Claims {
		rawClaim, err := json.Marshal(claim)
		if err != nil {
			return ingest.EvidenceSubmission{}, fmt.Errorf("marshal claim: %w", err)
		}
		confidence, relevance := string(claim.Confidence), claim.Relevance
		submission.Claims = append(submission.Claims, ingest.EvidenceClaimInput{
			SourceKey: sourceKey, ExtractionKey: extractionKey, SubjectNames: claim.SubjectNames,
			Text: claim.Text, TimestampSeconds: claim.TimestampSeconds, Speaker: claim.Speaker,
			Confidence: &confidence, Relevance: &relevance, ExtractedAt: extractedAt,
			ExtractionModel: model, RawPayload: rawClaim,
		})
	}
	return submission, nil
}

func TranscriptSubmission(video Video, matchNaturalKey string, extraction transcript.StructuredExtraction, rawResponse, usage json.RawMessage, competitors []string, model string, matchedQueries []string, extractedAt time.Time) (ingest.EvidenceSubmission, error) {
	claims := make([]GeminiClaim, 0, len(extraction.Claims))
	for _, claim := range extraction.Claims {
		claims = append(claims, GeminiClaim{Text: claim.Text, TimestampSeconds: claim.TimestampSeconds, SubjectNames: claim.SubjectNames, Speaker: claim.Speaker, Confidence: ClaimConfidence(claim.Confidence), Relevance: claim.Relevance, ClaimType: GeminiClaimType(claim.ClaimType)})
	}
	analysis := Analysis{Output: GeminiExtractionResponse{SchemaVersion: GeminiExtractionSchemaVersion(extraction.SchemaVersion), Claims: claims, Limitations: extraction.Limitations}, RawResponse: rawResponse, Usage: usage}
	submission, err := Submission(video, matchNaturalKey, analysis, competitors, model, matchedQueries, extractedAt)
	if err != nil {
		return ingest.EvidenceSubmission{}, err
	}
	return rewriteProviderSubmission(submission, "openai", model), nil
}

func FailedTranscriptSubmission(video Video, matchNaturalKey, model string, matchedQueries []string, extractedAt time.Time, cause error) ingest.EvidenceSubmission {
	return rewriteProviderSubmission(FailedSubmission(video, matchNaturalKey, model, matchedQueries, extractedAt, cause), "openai", model)
}

func rewriteProviderSubmission(submission ingest.EvidenceSubmission, provider, model string) ingest.EvidenceSubmission {
	oldSourceKey, oldExtractionKey := "youtube:"+submission.Sources[0].ExternalID, submission.Extractions[0].Key
	newExtractionKey := provider + ":" + submission.Sources[0].ExternalID + ":" + model + ":" + PromptVersion
	submission.Extractions[0].Key = newExtractionKey
	submission.Extractions[0].Provider = provider
	submission.Extractions[0].Model = model
	for i := range submission.Claims {
		if submission.Claims[i].SourceKey == oldSourceKey {
			submission.Claims[i].SourceKey = oldSourceKey
		}
		if submission.Claims[i].ExtractionKey == oldExtractionKey {
			submission.Claims[i].ExtractionKey = newExtractionKey
		}
		submission.Claims[i].ExtractionModel = model
	}
	return submission
}

func FailedSubmission(video Video, matchNaturalKey, model string, matchedQueries []string, extractedAt time.Time, cause error) ingest.EvidenceSubmission {
	sourceKey, extractionKey := "youtube:"+video.ID, "gemini:"+video.ID+":"+model+":"+PromptVersion
	title, publishedAt, message := video.Title, video.PublishedAt, cause.Error()
	sourcePayload, _ := json.Marshal(struct {
		Metadata       json.RawMessage `json:"metadata"`
		MatchedQueries []string        `json:"matched_queries"`
	}{Metadata: video.RawPayload, MatchedQueries: matchedQueries})
	return ingest.EvidenceSubmission{
		SchemaVersion: ingest.EvidenceSubmissionSchemaVersion, BatchKey: extractionKey + ":failed", MatchNaturalKey: matchNaturalKey,
		Sources:     []ingest.SourceInput{{Key: sourceKey, SourceType: "youtube", ExternalID: video.ID, URL: video.URL, Title: &title, PublishedAt: &publishedAt, RawPayload: sourcePayload}},
		Extractions: []ingest.SourceExtractionInput{{Key: extractionKey, SourceKey: sourceKey, Provider: "gemini", Model: model, PromptVersion: PromptVersion, Status: "failed", ExtractedAt: extractedAt, ErrorMessage: &message}},
	}
}
