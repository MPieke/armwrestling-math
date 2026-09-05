package ingest

import (
	"strings"
	"testing"
	"time"
)

func validResult() ResultSubmission {
	score := func(value int) *int { return &value }
	return ResultSubmission{
		SchemaVersion: ResultSubmissionSchemaVersion,
		BatchKey:      "batch",
		Event: EventInput{
			Slug: "east-vs-west-25", Promoter: "East vs West", Name: "East vs West 25",
			HeldOn: time.Date(2026, time.August, 1, 0, 0, 0, 0, time.UTC),
		},
		Arm:         "right",
		WeightClass: "105 kg",
		ScheduledAt: time.Date(2026, time.August, 1, 18, 0, 0, 0, time.UTC),
		Status:      "completed",
		Competitors: []CompetitorResultInput{
			{AthleteName: "Adam Wawrzynski", Score: score(3), Result: "win"},
			{AthleteName: "Nurdaulet Aidarkhan", Score: score(2), Result: "loss"},
		},
	}
}

func TestValidateResult(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*ResultSubmission)
		want   string
	}{
		{name: "accepts a well-formed completed result"},
		{
			name:   "rejects a completed match with zero winners",
			mutate: func(r *ResultSubmission) { r.Competitors[0].Result = "loss" },
			want:   "exactly one winner",
		},
		{
			name: "rejects a completed match with two winners",
			mutate: func(r *ResultSubmission) {
				r.Competitors[0].Result = "win"
				r.Competitors[1].Result = "win"
			},
			want: "exactly one winner",
		},
		{
			name:   "rejects a competitor count other than two",
			mutate: func(r *ResultSubmission) { r.Competitors = r.Competitors[:1] },
			want:   "exactly two competitors",
		},
		{
			name:   "rejects an unrecognized arm",
			mutate: func(r *ResultSubmission) { r.Arm = "both" },
			want:   "unrecognized arm",
		},
		{
			name:   "rejects an unrecognized status",
			mutate: func(r *ResultSubmission) { r.Status = "cancelled" },
			want:   "unrecognized status",
		},
		{
			name:   "rejects an unrecognized competitor result",
			mutate: func(r *ResultSubmission) { r.Competitors[0].Result = "forfeit" },
			want:   "unrecognized result",
		},
		{
			name:   "rejects duplicate competitor names",
			mutate: func(r *ResultSubmission) { r.Competitors[1].AthleteName = r.Competitors[0].AthleteName },
			want:   "duplicate competitor name",
		},
		{
			name:   "rejects an empty competitor name",
			mutate: func(r *ResultSubmission) { r.Competitors[0].AthleteName = "" },
			want:   "requires a name",
		},
		{
			name:   "rejects a submission with no event date",
			mutate: func(r *ResultSubmission) { r.Event.HeldOn = time.Time{} },
			want:   "event",
		},
		{
			name:   "rejects a completed match missing a score",
			mutate: func(r *ResultSubmission) { r.Competitors[1].Score = nil },
			want:   "requires a score",
		},
		{
			name: "accepts a no_contest match with no winner",
			mutate: func(r *ResultSubmission) {
				r.Status = "no_contest"
				r.Competitors[0].Result = "no_contest"
				r.Competitors[1].Result = "no_contest"
				r.Competitors[0].Score = nil
				r.Competitors[1].Score = nil
			},
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			submission := validResult()
			if test.mutate != nil {
				test.mutate(&submission)
			}
			err := ValidateResult(submission)
			if test.want == "" {
				if err != nil {
					t.Fatalf("ValidateResult() error = %v, want nil", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("ValidateResult() error = %v, want containing %q", err, test.want)
			}
		})
	}
}

func TestBuildBaseNaturalKeyIsOrderIndependent(t *testing.T) {
	a := CompetitorResultInput{AthleteName: "Adam Wawrzynski"}
	b := CompetitorResultInput{AthleteName: "Nurdaulet Aidarkhan"}

	forward := buildBaseNaturalKey("east-vs-west-25", []CompetitorResultInput{a, b}, "right")
	backward := buildBaseNaturalKey("east-vs-west-25", []CompetitorResultInput{b, a}, "right")

	if forward != backward {
		t.Fatalf("buildBaseNaturalKey() order-dependent: %q != %q", forward, backward)
	}
	if forward != "east-vs-west-25:adam-wawrzynski:nurdaulet-aidarkhan:right" {
		t.Fatalf("buildBaseNaturalKey() = %q, unexpected shape", forward)
	}
}
