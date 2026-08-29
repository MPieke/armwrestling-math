package transcript

import (
	"context"
	"encoding/json"
)

const (
	AudioArtifactSchemaVersion = "audio-artifact-v1"
	TranscriptSchemaVersion    = "transcript-v1"
	ExtractionSchemaVersion    = "youtube-claims-v1"
)

type AudioArtifact struct {
	SchemaVersion string `json:"schema_version"`
	Path          string `json:"path"`
	Format        string `json:"format"`
	Duration      int    `json:"duration_seconds"`
}

type Segment struct {
	StartSeconds float64 `json:"start_seconds"`
	EndSeconds   float64 `json:"end_seconds"`
	Text         string  `json:"text"`
}

type Transcript struct {
	SchemaVersion string    `json:"schema_version"`
	Language      string    `json:"language,omitempty"`
	Text          string    `json:"text"`
	Segments      []Segment `json:"segments"`
}

type MatchContext struct {
	NaturalKey  string
	Competitors []string
	Arm         string
}

type StructuredExtraction struct {
	SchemaVersion string   `json:"schema_version"`
	Claims        []Claim  `json:"claims"`
	Limitations   []string `json:"limitations"`
}

func (*StructuredExtraction) StructuredOutput() {}

type Claim struct {
	Text             string   `json:"text"`
	TimestampSeconds *int     `json:"timestamp_seconds,omitempty"`
	SubjectNames     []string `json:"subject_names"`
	Speaker          *string  `json:"speaker,omitempty"`
	Confidence       string   `json:"confidence"`
	Relevance        string   `json:"relevance"`
	ClaimType        string   `json:"claim_type"`
}

type AudioSource interface {
	Acquire(context.Context, string) (AudioArtifact, error)
}

type TranscriptionProvider interface {
	Transcribe(context.Context, AudioArtifact, []string) (Transcript, json.RawMessage, json.RawMessage, error)
}

type ClaimExtractor interface {
	Extract(context.Context, Transcript, MatchContext) (StructuredExtraction, json.RawMessage, json.RawMessage, error)
}
