package youtube

import "fmt"

func ValidateExtraction(response GeminiExtractionResponse, competitors map[string]struct{}, durationSeconds int) error {
	if response.SchemaVersion != GeminiExtractionSchemaVersionV1 {
		return fmt.Errorf("unsupported extraction schema version: %s", response.SchemaVersion)
	}
	if len(response.Claims) == 0 && len(response.Limitations) == 0 {
		return fmt.Errorf("zero claims require a limitation")
	}
	for index, claim := range response.Claims {
		if claim.Text == "" || claim.Relevance == "" {
			return fmt.Errorf("claim %d requires text and relevance", index)
		}
		if claim.TimestampSeconds != nil && (*claim.TimestampSeconds < 0 || *claim.TimestampSeconds > durationSeconds) {
			return fmt.Errorf("claim %d timestamp is outside video duration", index)
		}
		if claim.Confidence != ClaimConfidenceLow && claim.Confidence != ClaimConfidenceMedium && claim.Confidence != ClaimConfidenceHigh {
			return fmt.Errorf("claim %d has unknown confidence", index)
		}
		if !validClaimType(claim.ClaimType) {
			return fmt.Errorf("claim %d has unknown claim type", index)
		}
		for _, subject := range claim.SubjectNames {
			if _, exists := competitors[subject]; !exists {
				return fmt.Errorf("claim %d references unknown subject: %s", index, subject)
			}
		}
	}
	return nil
}
func validClaimType(value GeminiClaimType) bool {
	switch value {
	case GeminiClaimTypeForm, GeminiClaimTypeTactic, GeminiClaimTypeInjury, GeminiClaimTypeEndurance, GeminiClaimTypeSetup, GeminiClaimTypeOpponentComparison, GeminiClaimTypeOther:
		return true
	}
	return false
}
