package youtube

import (
	"encoding/json"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
)

func TestValidateExtraction(t *testing.T) {
	timestamp := 12
	valid := transcript.StructuredExtraction{SchemaVersion: transcript.ExtractionSchemaVersion, Claims: []transcript.Claim{{Text: "claim", Relevance: "relevant", TimestampSeconds: &timestamp, SubjectNames: []string{"Ermes"}, Confidence: "high", ClaimType: "form"}}}
	if err := ValidateExtraction(valid, map[string]struct{}{"Ermes": {}}, 30); err != nil {
		t.Fatal(err)
	}
	valid.Claims[0].SubjectNames = []string{"Unknown"}
	if err := ValidateExtraction(valid, map[string]struct{}{"Ermes": {}}, 30); err == nil {
		t.Fatal("unknown subject accepted")
	}
}

func TestValidateExtractionRejectsSemanticFailures(t *testing.T) {
	timestamp := 12
	base := func() transcript.StructuredExtraction {
		return transcript.StructuredExtraction{SchemaVersion: transcript.ExtractionSchemaVersion, Claims: []transcript.Claim{{
			Text: "claim", Relevance: "relevant", TimestampSeconds: &timestamp,
			SubjectNames: []string{"Ermes"}, Confidence: "high", ClaimType: "form",
		}}}
	}
	tests := []struct {
		name   string
		mutate func(*transcript.StructuredExtraction)
		want   string
	}{
		{name: "unknown schema", mutate: func(value *transcript.StructuredExtraction) { value.SchemaVersion = "future" }, want: "unsupported"},
		{name: "empty claim", mutate: func(value *transcript.StructuredExtraction) { value.Claims[0].Text = "" }, want: "requires text"},
		{name: "bad timestamp", mutate: func(value *transcript.StructuredExtraction) {
			invalid := 31
			value.Claims[0].TimestampSeconds = &invalid
		}, want: "outside"},
		{name: "bad confidence", mutate: func(value *transcript.StructuredExtraction) { value.Claims[0].Confidence = "certain" }, want: "confidence"},
		{name: "bad type", mutate: func(value *transcript.StructuredExtraction) { value.Claims[0].ClaimType = "prediction" }, want: "claim type"},
		{name: "zero unexplained claims", mutate: func(value *transcript.StructuredExtraction) { value.Claims = nil }, want: "limitation"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			value := base()
			test.mutate(&value)
			if err := ValidateExtraction(value, map[string]struct{}{"Ermes": {}}, 30); err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("error = %v, want containing %q", err, test.want)
			}
		})
	}
}

func TestSubmissionMapsTranscriptClaimsWithOpenAIProvenance(t *testing.T) {
	video := Video{ID: "fixture", Title: "Fixture", PublishedAt: time.Unix(10, 0).UTC(), DurationSeconds: 30, URL: "https://youtube.test/fixture", RawPayload: json.RawMessage(`{"video":true}`)}
	extraction := transcript.StructuredExtraction{SchemaVersion: transcript.ExtractionSchemaVersion, Claims: []transcript.Claim{{Text: "claim", Relevance: "why", SubjectNames: []string{"Ermes"}, Confidence: "high", ClaimType: "form"}}}
	submission, err := Submission(video, "match", extraction, json.RawMessage(`{"model":true}`), json.RawMessage(`{"tokens":1}`), []string{"Ermes", "Morozov"}, "gpt-4.1-mini", []string{"query"}, time.Unix(20, 0).UTC())
	if err != nil {
		t.Fatal(err)
	}
	if submission.Extractions[0].Provider != "openai" || !strings.HasPrefix(submission.Extractions[0].Key, "openai:fixture:") || submission.Claims[0].ExtractionKey != submission.Extractions[0].Key {
		t.Fatalf("submission provenance = %+v", submission)
	}
	raw, err := json.Marshal(submission)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(raw), `"video":true`) || !strings.Contains(string(raw), `"model":true`) || !strings.Contains(string(raw), `"claim_type":"form"`) {
		t.Fatalf("round trip lost evidence: %s", raw)
	}
}

func TestFailedSubmissionUsesOpenAIProvenance(t *testing.T) {
	video := Video{ID: "fixture", Title: "Fixture", PublishedAt: time.Unix(10, 0).UTC(), URL: "https://youtube.test/fixture"}
	submission := FailedSubmission(video, "match", "gpt-4.1-mini", []string{"query"}, time.Unix(20, 0).UTC(), errors.New("failure"))
	if submission.Extractions[0].Provider != "openai" || submission.Extractions[0].Status != "failed" || !strings.HasPrefix(submission.Extractions[0].Key, "openai:fixture:") {
		t.Fatalf("failed submission = %+v", submission)
	}
}
