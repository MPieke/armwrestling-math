package ingest

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestValidate(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*IngestBatch)
		want   string
	}{
		{name: "accepts a complete consistent batch"},
		{
			name: "requires batch key",
			mutate: func(batch *IngestBatch) {
				batch.BatchKey = ""
			},
			want: "batch key is required",
		},
		{
			name: "requires athlete key and canonical name",
			mutate: func(batch *IngestBatch) {
				batch.Athletes[0].CanonicalName = ""
			},
			want: "athletes require key and canonical name",
		},
		{
			name: "rejects duplicate athlete key",
			mutate: func(batch *IngestBatch) {
				batch.Athletes = append(batch.Athletes, AthleteInput{Key: "ermes", CanonicalName: "Duplicate"})
			},
			want: "duplicate athlete key: ermes",
		},
		{
			name: "requires match identity",
			mutate: func(batch *IngestBatch) {
				batch.Match.NaturalKey = ""
			},
			want: "match requires key, natural key, and arm",
		},
		{
			name: "rejects unknown match competitor",
			mutate: func(batch *IngestBatch) {
				batch.Match.Competitors = append(batch.Match.Competitors, "unknown")
			},
			want: "match references unknown athlete: unknown",
		},
		{
			name: "requires source identity and location",
			mutate: func(batch *IngestBatch) {
				batch.Sources[0].URL = ""
			},
			want: "sources require key, type, external ID, and URL",
		},
		{
			name: "rejects duplicate source key",
			mutate: func(batch *IngestBatch) {
				batch.Sources = append(batch.Sources, SourceInput{Key: "youtube:fixture", SourceType: "youtube", ExternalID: "duplicate", URL: "https://example.com/duplicate"})
			},
			want: "duplicate source key: youtube:fixture",
		},
		{
			name: "requires claim fields",
			mutate: func(batch *IngestBatch) {
				batch.Claims[0].ExtractedAt = time.Time{}
			},
			want: "claim 0 requires source, match, text, and extracted-at",
		},
		{
			name: "rejects unknown claim match",
			mutate: func(batch *IngestBatch) {
				batch.Claims[0].MatchKey = "unknown"
			},
			want: "claim 0 references unknown match: unknown",
		},
		{
			name: "rejects unknown claim source",
			mutate: func(batch *IngestBatch) {
				batch.Claims[0].SourceKey = "unknown"
			},
			want: "claim 0 references unknown source: unknown",
		},
		{
			name: "rejects unknown claim subject",
			mutate: func(batch *IngestBatch) {
				batch.Claims[0].SubjectKeys = append(batch.Claims[0].SubjectKeys, "unknown")
			},
			want: "claim 0 references unknown subject: unknown",
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			batch := validBatch()
			if test.mutate != nil {
				test.mutate(&batch)
			}

			err := Validate(batch)
			if test.want == "" {
				if err != nil {
					t.Fatalf("Validate() error = %v, want nil", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), test.want) {
				t.Fatalf("Validate() error = %v, want error containing %q", err, test.want)
			}
		})
	}
}

func TestRunRejectsInvalidBatchBeforeDatabaseWork(t *testing.T) {
	_, err := Run(context.Background(), nil, IngestBatch{})
	if err == nil || !strings.Contains(err.Error(), "batch key is required") {
		t.Fatalf("Run() error = %v, want validation error", err)
	}
}

func validBatch() IngestBatch {
	return IngestBatch{
		BatchKey: "validation-fixture",
		Athletes: []AthleteInput{
			{Key: "ermes", CanonicalName: "Ermes Gasparini"},
			{Key: "morozov", CanonicalName: "Artyom Morozov"},
		},
		Match: MatchInput{
			Key:         "match",
			NaturalKey:  "2026-06:artyom-morozov:ermes-gasparini:right",
			Arm:         "right",
			Competitors: []string{"ermes", "morozov"},
		},
		Sources: []SourceInput{{
			Key:        "youtube:fixture",
			SourceType: "youtube",
			ExternalID: "fixture",
			URL:        "https://www.youtube.com/watch?v=fixture",
		}},
		Claims: []ClaimInput{{
			SourceKey:   "youtube:fixture",
			MatchKey:    "match",
			SubjectKeys: []string{"ermes"},
			Text:        "Ermes claim",
			ExtractedAt: time.Date(2026, time.June, 1, 0, 0, 0, 0, time.UTC),
		}},
	}
}
