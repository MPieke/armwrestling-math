package youtube

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestValidateExtraction(t *testing.T) {
	timestamp := 12
	valid := GeminiExtractionResponse{SchemaVersion: GeminiExtractionSchemaVersionV1, Claims: []GeminiClaim{{Text: "claim", Relevance: "relevant", TimestampSeconds: &timestamp, SubjectNames: []string{"Ermes"}, Confidence: ClaimConfidenceHigh, ClaimType: GeminiClaimTypeForm}}}
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
	base := func() GeminiExtractionResponse {
		return GeminiExtractionResponse{SchemaVersion: GeminiExtractionSchemaVersionV1, Claims: []GeminiClaim{{
			Text: "claim", Relevance: "relevant", TimestampSeconds: &timestamp,
			SubjectNames: []string{"Ermes"}, Confidence: ClaimConfidenceHigh, ClaimType: GeminiClaimTypeForm,
		}}}
	}
	tests := []struct {
		name   string
		mutate func(*GeminiExtractionResponse)
		want   string
	}{
		{name: "unknown schema", mutate: func(value *GeminiExtractionResponse) { value.SchemaVersion = "future" }, want: "unsupported"},
		{name: "empty claim", mutate: func(value *GeminiExtractionResponse) { value.Claims[0].Text = "" }, want: "requires text"},
		{name: "bad timestamp", mutate: func(value *GeminiExtractionResponse) { invalid := 31; value.Claims[0].TimestampSeconds = &invalid }, want: "outside"},
		{name: "bad confidence", mutate: func(value *GeminiExtractionResponse) { value.Claims[0].Confidence = "certain" }, want: "confidence"},
		{name: "bad type", mutate: func(value *GeminiExtractionResponse) { value.Claims[0].ClaimType = "prediction" }, want: "claim type"},
		{name: "zero unexplained claims", mutate: func(value *GeminiExtractionResponse) { value.Claims = nil }, want: "limitation"},
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

func TestSubmissionRoundTripsWithoutLosingRawPayloads(t *testing.T) {
	video := Video{ID: "fixture", Title: "Fixture", PublishedAt: time.Unix(10, 0).UTC(), DurationSeconds: 30, URL: "https://youtube.test/fixture", RawPayload: json.RawMessage(`{"video":true}`)}
	analysis := Analysis{Output: GeminiExtractionResponse{SchemaVersion: GeminiExtractionSchemaVersionV1, Claims: []GeminiClaim{{Text: "claim", Relevance: "why", SubjectNames: []string{"Ermes"}, Confidence: ClaimConfidenceHigh, ClaimType: GeminiClaimTypeForm}}}, RawResponse: json.RawMessage(`{"model":true}`), Usage: json.RawMessage(`{"tokens":1}`)}
	submission, err := Submission(video, "match", analysis, []string{"Ermes", "Morozov"}, "model", []string{"query"}, time.Unix(20, 0).UTC())
	if err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(submission)
	if err != nil {
		t.Fatal(err)
	}
	var decoded struct {
		SchemaVersion string `json:"schema_version"`
		Sources       []struct {
			Raw json.RawMessage `json:"raw_payload"`
		} `json:"sources"`
		Extractions []struct {
			Raw json.RawMessage `json:"raw_response"`
		} `json:"extractions"`
		Claims []struct {
			Raw json.RawMessage `json:"raw_payload"`
		} `json:"claims"`
	}
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded.SchemaVersion != "evidence-submission-v1" || len(decoded.Sources) != 1 || len(decoded.Extractions) != 1 || len(decoded.Claims) != 1 ||
		!strings.Contains(string(decoded.Sources[0].Raw), `"video":true`) || !strings.Contains(string(decoded.Extractions[0].Raw), `"model":true`) || !strings.Contains(string(decoded.Claims[0].Raw), `"text":"claim"`) {
		t.Fatalf("round trip lost evidence: %s", raw)
	}
}
