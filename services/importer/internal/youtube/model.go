package youtube

import (
	"encoding/json"
	"time"
)

type Video struct {
	ID              string
	Title           string
	ChannelName     string
	PublishedAt     time.Time
	DurationSeconds int
	URL             string
	RawPayload      json.RawMessage
}

type GeminiExtractionSchemaVersion string

const GeminiExtractionSchemaVersionV1 GeminiExtractionSchemaVersion = "youtube-claims-v1"

type ClaimConfidence string

const (
	ClaimConfidenceLow    ClaimConfidence = "low"
	ClaimConfidenceMedium ClaimConfidence = "medium"
	ClaimConfidenceHigh   ClaimConfidence = "high"
)

type GeminiClaimType string

const (
	GeminiClaimTypeForm               GeminiClaimType = "form"
	GeminiClaimTypeTactic             GeminiClaimType = "tactic"
	GeminiClaimTypeInjury             GeminiClaimType = "injury"
	GeminiClaimTypeEndurance          GeminiClaimType = "endurance"
	GeminiClaimTypeSetup              GeminiClaimType = "setup"
	GeminiClaimTypeOpponentComparison GeminiClaimType = "opponent_comparison"
	GeminiClaimTypeOther              GeminiClaimType = "other"
)

type GeminiExtractionResponse struct {
	SchemaVersion GeminiExtractionSchemaVersion `json:"schema_version"`
	Claims        []GeminiClaim                 `json:"claims"`
	Limitations   []string                      `json:"limitations"`
}

func (*GeminiExtractionResponse) StructuredOutput() {}

type GeminiClaim struct {
	Text             string          `json:"text"`
	TimestampSeconds *int            `json:"timestamp_seconds,omitempty"`
	SubjectNames     []string        `json:"subject_names"`
	Speaker          *string         `json:"speaker,omitempty"`
	Confidence       ClaimConfidence `json:"confidence" enum:"low,medium,high"`
	Relevance        string          `json:"relevance"`
	ClaimType        GeminiClaimType `json:"claim_type" enum:"form,tactic,injury,endurance,setup,opponent_comparison,other"`
}
