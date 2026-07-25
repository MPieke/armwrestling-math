package ingest

import (
	"strings"
	"testing"
	"time"
)

func TestValidateRejectsUnresolvedReferencesBeforeDatabaseWork(t *testing.T) {
	batch := IngestBatch{
		BatchKey: "test", Athletes: []AthleteInput{{Key: "ermes", CanonicalName: "Ermes Gasparini"}},
		Match:  MatchInput{Key: "match", NaturalKey: "key", Arm: "right", Competitors: []string{"ermes"}},
		Claims: []ClaimInput{{SourceKey: "missing", MatchKey: "match", Text: "claim", ExtractedAt: time.Now()}},
	}
	err := Validate(batch)
	if err == nil || !strings.Contains(err.Error(), "unknown source: missing") {
		t.Fatalf("Validate() error = %v, want unresolved source", err)
	}
}
