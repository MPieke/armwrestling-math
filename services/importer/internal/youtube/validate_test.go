package youtube

import "testing"

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
