package youtube

import (
	"fmt"

	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
)

func ValidateExtraction(extraction transcript.StructuredExtraction, competitors map[string]struct{}, durationSeconds int) error {
	if extraction.SchemaVersion != transcript.ExtractionSchemaVersion {
		return fmt.Errorf("unsupported extraction schema version: %s", extraction.SchemaVersion)
	}
	if len(extraction.Claims) == 0 && len(extraction.Limitations) == 0 {
		return fmt.Errorf("zero claims require a limitation")
	}
	for index, claim := range extraction.Claims {
		if claim.Text == "" || claim.Relevance == "" {
			return fmt.Errorf("claim %d requires text and relevance", index)
		}
		if claim.TimestampSeconds != nil && (*claim.TimestampSeconds < 0 || *claim.TimestampSeconds > durationSeconds) {
			return fmt.Errorf("claim %d timestamp is outside video duration", index)
		}
		if claim.Confidence != "low" && claim.Confidence != "medium" && claim.Confidence != "high" {
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
func validClaimType(value string) bool {
	switch value {
	case "form", "tactic", "injury", "endurance", "setup", "opponent_comparison", "other":
		return true
	}
	return false
}
