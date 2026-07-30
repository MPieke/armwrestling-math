package ingest

import (
	"encoding/json"
	"time"
)

type IngestBatch struct {
	BatchKey string
	Athletes []AthleteInput
	Match    MatchInput
	Sources  []SourceInput
	Claims   []ClaimInput
}

type AthleteInput struct {
	Key           string
	CanonicalName string
}

type MatchInput struct {
	Key         string
	NaturalKey  string
	Label       string
	Arm         string
	ScheduledAt *time.Time
	Competitors []string
}

type SourceInput struct {
	Key         string
	SourceType  string
	ExternalID  string
	URL         string
	Title       *string
	PublishedAt *time.Time
	RawPayload  json.RawMessage
}

type ClaimInput struct {
	SourceKey        string
	MatchKey         string
	SubjectKeys      []string
	Text             string
	TimestampSeconds *int
	Speaker          *string
	Confidence       *string
	Relevance        *string
	ObservedAt       *time.Time
	ExtractedAt      time.Time
	ExtractionModel  *string
	RawPayload       json.RawMessage
}

// EvidenceSubmission is the database-independent boundary used by source
// adapters. Match and athlete identities remain canonical database data.
type EvidenceSubmission struct {
	SchemaVersion   string
	BatchKey        string
	MatchNaturalKey string
	Sources         []SourceInput
	Claims          []EvidenceClaimInput
}

type EvidenceClaimInput struct {
	SourceKey        string
	SubjectNames     []string
	Text             string
	TimestampSeconds *int
	Speaker          *string
	Confidence       *string
	Relevance        *string
	ObservedAt       *time.Time
	ExtractedAt      time.Time
	ExtractionModel  string
	RawPayload       json.RawMessage
}

func evidenceSubmissionFromBatch(batch IngestBatch) EvidenceSubmission {
	athleteNames := make(map[string]string, len(batch.Athletes))
	for _, athlete := range batch.Athletes {
		athleteNames[athlete.Key] = athlete.CanonicalName
	}
	claims := make([]EvidenceClaimInput, 0, len(batch.Claims))
	for _, claim := range batch.Claims {
		subjectNames := make([]string, 0, len(claim.SubjectKeys))
		for _, subjectKey := range claim.SubjectKeys {
			subjectNames = append(subjectNames, athleteNames[subjectKey])
		}
		extractionModel := ""
		if claim.ExtractionModel != nil {
			extractionModel = *claim.ExtractionModel
		}
		claims = append(claims, EvidenceClaimInput{
			SourceKey: claim.SourceKey, SubjectNames: subjectNames, Text: claim.Text,
			TimestampSeconds: claim.TimestampSeconds, Speaker: claim.Speaker,
			Confidence: claim.Confidence, Relevance: claim.Relevance, ObservedAt: claim.ObservedAt,
			ExtractedAt: claim.ExtractedAt, ExtractionModel: extractionModel, RawPayload: claim.RawPayload,
		})
	}
	return EvidenceSubmission{
		SchemaVersion: evidenceSubmissionSchemaVersion, BatchKey: batch.BatchKey,
		MatchNaturalKey: batch.Match.NaturalKey, Sources: batch.Sources, Claims: claims,
	}
}
