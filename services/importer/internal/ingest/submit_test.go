package ingest

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestValidateEvidence(t *testing.T) {
	valid := func() EvidenceSubmission {
		extractedAt := time.Date(2026, time.June, 1, 0, 0, 0, 0, time.UTC)
		return EvidenceSubmission{
			SchemaVersion: EvidenceSubmissionSchemaVersion, BatchKey: "batch", MatchNaturalKey: "match",
			Sources:     []SourceInput{{Key: "source", SourceType: "youtube", ExternalID: "video", URL: "https://example.test/video", RawPayload: json.RawMessage(`{}`)}},
			Extractions: []SourceExtractionInput{{Key: "extraction", SourceKey: "source", Provider: "gemini", Model: "model", PromptVersion: "v1", Status: "completed", ExtractedAt: extractedAt}},
			Claims:      []EvidenceClaimInput{{SourceKey: "source", ExtractionKey: "extraction", SubjectNames: []string{"Ermes"}, Text: "claim", ExtractedAt: extractedAt, RawPayload: json.RawMessage(`{}`)}},
		}
	}
	tests := []struct {
		name   string
		mutate func(*EvidenceSubmission)
		want   string
	}{
		{name: "accepts consistent submission"},
		{name: "rejects schema version", mutate: func(value *EvidenceSubmission) { value.SchemaVersion = "future" }, want: "unsupported"},
		{name: "rejects unknown source", mutate: func(value *EvidenceSubmission) { value.Claims[0].SourceKey = "missing" }, want: "unknown source"},
		{name: "rejects unknown extraction", mutate: func(value *EvidenceSubmission) { value.Claims[0].ExtractionKey = "missing" }, want: "unknown extraction"},
		{name: "rejects failed extraction without error", mutate: func(value *EvidenceSubmission) { value.Extractions[0].Status = "failed" }, want: "error message"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			submission := valid()
			if test.mutate != nil {
				test.mutate(&submission)
			}
			err := ValidateEvidence(submission)
			if test.want == "" && err != nil {
				t.Fatal(err)
			}
			if test.want != "" && (err == nil || !strings.Contains(err.Error(), test.want)) {
				t.Fatalf("error = %v, want containing %q", err, test.want)
			}
		})
	}
}

func TestSubmitRejectsInvalidEvidenceBeforeDatabaseWork(t *testing.T) {
	if _, err := Submit(context.Background(), nil, EvidenceSubmission{}); err == nil {
		t.Fatal("Submit() accepted invalid evidence with a nil database pool")
	}
}
