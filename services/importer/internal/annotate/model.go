// Package annotate adds a structured interpretation layer on top of
// already-persisted claims (MPI-16), following the same structured-output
// pattern as internal/transcript: a Go type derives the OpenAI schema,
// the response decodes back into that type, then semantic validation runs
// before persistence. It never creates or modifies a claim -- only
// annotates one that already exists.
package annotate

import (
	"context"
	"encoding/json"
)

const AnnotationSchemaVersion = "claim-annotation-v1"

// ClaimAnnotation is what one call to the model produces for one claim.
// claim_type reuses transcript.Claim's existing extraction-time vocabulary
// (services/importer/internal/transcript/model.go) rather than inventing a
// second, overlapping one. concepts and temporality/certainty are this
// package's own vocabulary -- the latter two reuse the dimensions already
// sketched in scripts/evidence_dimension_models.py during early discovery
// work, condensed to what a single claim (not a whole transcript) needs.
type ClaimAnnotation struct {
	ClaimType          string   `json:"claim_type" enum:"form,tactic,injury,endurance,setup,opponent_comparison,other"`
	Concepts           []string `json:"concepts" enum:"top_roll,hook,press,side_pressure,back_pressure,wrist_control,supination,grip_strength,arm_length,hand_size,frame_and_leverage,reserve_strength,explosive_strength,start_position,shoulder_engagement,elbow_discipline,injury_or_recovery_status,training_regimen,mental_focus,matchup_specific_history"`
	SubjectAthleteName string   `json:"subject_athlete_name"`
	Arm                string   `json:"arm" enum:"left,right,unclear"`
	Temporality        string   `json:"temporality" enum:"current_form,recent_context,historical_event,durable_style,future_prediction,general_principle,unclear"`
	Certainty          string   `json:"certainty" enum:"observed,self_reported,analyst_interpretation,community_narrative,unclear"`
}

func (*ClaimAnnotation) StructuredOutput() {}

// ClaimContext is what the annotator needs about the claim being annotated
// and the match it belongs to -- enough to resolve SubjectAthleteName back
// to an athlete id without asking the model to output a foreign key.
type ClaimContext struct {
	ClaimID     int64
	ClaimText   string
	Competitors []string
}

type Annotator interface {
	ModelName() string
	Annotate(context.Context, ClaimContext) (ClaimAnnotation, json.RawMessage, json.RawMessage, error)
}
