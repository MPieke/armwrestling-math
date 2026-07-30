package ingest

import (
	"encoding/json"
	"time"
)

type SourceInput struct {
	Key         string          `json:"key"`
	SourceType  string          `json:"source_type"`
	ExternalID  string          `json:"external_id"`
	URL         string          `json:"url"`
	Title       *string         `json:"title,omitempty"`
	PublishedAt *time.Time      `json:"published_at,omitempty"`
	RawPayload  json.RawMessage `json:"raw_payload"`
}

// EvidenceSubmission is the database-independent boundary used by source
// adapters. Match and athlete identities remain canonical database data.
type EvidenceSubmission struct {
	SchemaVersion   string                  `json:"schema_version"`
	BatchKey        string                  `json:"batch_key"`
	MatchNaturalKey string                  `json:"match_natural_key"`
	Sources         []SourceInput           `json:"sources"`
	Extractions     []SourceExtractionInput `json:"extractions"`
	Claims          []EvidenceClaimInput    `json:"claims"`
}

type SourceExtractionInput struct {
	Key           string          `json:"key"`
	SourceKey     string          `json:"source_key"`
	Provider      string          `json:"provider"`
	Model         string          `json:"model"`
	PromptVersion string          `json:"prompt_version"`
	Status        string          `json:"status"`
	ExtractedAt   time.Time       `json:"extracted_at"`
	RawResponse   json.RawMessage `json:"raw_response,omitempty"`
	Usage         json.RawMessage `json:"usage,omitempty"`
	ErrorMessage  *string         `json:"error_message,omitempty"`
}

type EvidenceClaimInput struct {
	SourceKey        string          `json:"source_key"`
	ExtractionKey    string          `json:"extraction_key,omitempty"`
	SubjectNames     []string        `json:"subject_names"`
	Text             string          `json:"text"`
	TimestampSeconds *int            `json:"timestamp_seconds,omitempty"`
	Speaker          *string         `json:"speaker,omitempty"`
	Confidence       *string         `json:"confidence,omitempty"`
	Relevance        *string         `json:"relevance,omitempty"`
	ObservedAt       *time.Time      `json:"observed_at,omitempty"`
	ExtractedAt      time.Time       `json:"extracted_at"`
	ExtractionModel  string          `json:"extraction_model"`
	RawPayload       json.RawMessage `json:"raw_payload"`
}
