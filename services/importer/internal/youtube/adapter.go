package youtube

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
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
		SchemaVersion: "evidence-submission-v1", BatchKey: extractionKey, MatchNaturalKey: matchNaturalKey,
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

func FailedSubmission(video Video, matchNaturalKey, model string, matchedQueries []string, extractedAt time.Time, cause error) ingest.EvidenceSubmission {
	sourceKey, extractionKey := "youtube:"+video.ID, "gemini:"+video.ID+":"+model+":"+PromptVersion
	title, publishedAt, message := video.Title, video.PublishedAt, cause.Error()
	sourcePayload, _ := json.Marshal(struct {
		Metadata       json.RawMessage `json:"metadata"`
		MatchedQueries []string        `json:"matched_queries"`
	}{Metadata: video.RawPayload, MatchedQueries: matchedQueries})
	return ingest.EvidenceSubmission{
		SchemaVersion: "evidence-submission-v1", BatchKey: extractionKey + ":failed", MatchNaturalKey: matchNaturalKey,
		Sources:     []ingest.SourceInput{{Key: sourceKey, SourceType: "youtube", ExternalID: video.ID, URL: video.URL, Title: &title, PublishedAt: &publishedAt, RawPayload: sourcePayload}},
		Extractions: []ingest.SourceExtractionInput{{Key: extractionKey, SourceKey: sourceKey, Provider: "gemini", Model: model, PromptVersion: PromptVersion, Status: "failed", ExtractedAt: extractedAt, ErrorMessage: &message}},
	}
}
