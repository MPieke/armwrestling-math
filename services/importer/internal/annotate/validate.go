package annotate

import "fmt"

var (
	validClaimTypes = set("form", "tactic", "injury", "endurance", "setup", "opponent_comparison", "other")
	validConcepts   = set(
		"top_roll", "hook", "press", "side_pressure", "back_pressure", "wrist_control",
		"supination", "grip_strength", "arm_length", "hand_size", "frame_and_leverage",
		"reserve_strength", "explosive_strength", "start_position", "shoulder_engagement",
		"elbow_discipline", "injury_or_recovery_status", "training_regimen", "mental_focus",
		"matchup_specific_history",
	)
	validArms        = set("left", "right", "unclear")
	validTemporality = set("current_form", "recent_context", "historical_event", "durable_style", "future_prediction", "general_principle", "unclear")
	validCertainty   = set("observed", "self_reported", "analyst_interpretation", "community_narrative", "unclear")
)

func set(values ...string) map[string]bool {
	result := make(map[string]bool, len(values))
	for _, value := range values {
		result[value] = true
	}
	return result
}

// ValidateAnnotation defends against a model returning a value outside its
// requested enum (structured-output "strict" mode should prevent this, but
// semantic validation before persistence -- not trust in a provider
// contract -- is what actually protects claim_annotations' check
// constraints, matching MPI-16's extraction validation pattern).
func ValidateAnnotation(annotation ClaimAnnotation) error {
	if !validClaimTypes[annotation.ClaimType] {
		return fmt.Errorf("unrecognized claim_type %q", annotation.ClaimType)
	}
	if len(annotation.Concepts) == 0 {
		return fmt.Errorf("annotation requires at least one concept")
	}
	for _, concept := range annotation.Concepts {
		if !validConcepts[concept] {
			return fmt.Errorf("unrecognized concept %q", concept)
		}
	}
	if !validArms[annotation.Arm] {
		return fmt.Errorf("unrecognized arm %q", annotation.Arm)
	}
	if !validTemporality[annotation.Temporality] {
		return fmt.Errorf("unrecognized temporality %q", annotation.Temporality)
	}
	if !validCertainty[annotation.Certainty] {
		return fmt.Errorf("unrecognized certainty %q", annotation.Certainty)
	}
	return nil
}
