package annotate

import (
	"strings"
	"testing"
)

func validAnnotation() ClaimAnnotation {
	return ClaimAnnotation{
		ClaimType:          "tactic",
		Concepts:           []string{"top_roll", "reserve_strength"},
		SubjectAthleteName: "Ermes Gasparini",
		Arm:                "right",
		Temporality:        "current_form",
		Certainty:          "observed",
	}
}

func TestValidateAnnotation(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*ClaimAnnotation)
		want   string
	}{
		{name: "accepts a well-formed annotation"},
		{
			name:   "rejects an unrecognized claim_type",
			mutate: func(a *ClaimAnnotation) { a.ClaimType = "not-a-real-type" },
			want:   "unrecognized claim_type",
		},
		{
			name:   "rejects an empty concepts list",
			mutate: func(a *ClaimAnnotation) { a.Concepts = nil },
			want:   "at least one concept",
		},
		{
			name:   "rejects an unrecognized concept",
			mutate: func(a *ClaimAnnotation) { a.Concepts = []string{"not_a_real_concept"} },
			want:   "unrecognized concept",
		},
		{
			name:   "rejects an unrecognized arm",
			mutate: func(a *ClaimAnnotation) { a.Arm = "both" },
			want:   "unrecognized arm",
		},
		{
			name:   "accepts unclear arm",
			mutate: func(a *ClaimAnnotation) { a.Arm = "unclear" },
		},
		{
			name:   "rejects an unrecognized temporality",
			mutate: func(a *ClaimAnnotation) { a.Temporality = "yesterday" },
			want:   "unrecognized temporality",
		},
		{
			name:   "rejects an unrecognized certainty",
			mutate: func(a *ClaimAnnotation) { a.Certainty = "definitely" },
			want:   "unrecognized certainty",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			annotation := validAnnotation()
			if test.mutate != nil {
				test.mutate(&annotation)
			}
			err := ValidateAnnotation(annotation)
			if test.want == "" {
				if err != nil {
					t.Fatalf("ValidateAnnotation() error = %v, want nil", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("ValidateAnnotation() error = %v, want containing %q", err, test.want)
			}
		})
	}
}
