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
