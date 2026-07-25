package legacy

import (
	"path/filepath"
	"testing"

	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
)

func TestBuildBatchFromCommittedEvidence(t *testing.T) {
	root := filepath.Join("..", "..", "..", "..")
	batch, err := BuildBatch([]string{
		filepath.Join(root, "data", "app", "ermes_morozov_evidence_v1.json"),
		filepath.Join(root, "data", "app", "ermes_morozov_expanded_evidence_v1.json"),
	})
	if err != nil {
		t.Fatalf("BuildBatch() error = %v", err)
	}
	if err := ingest.Validate(batch); err != nil {
		t.Fatalf("Validate() error = %v", err)
	}
	if got, want := len(batch.Athletes), 2; got != want {
		t.Errorf("athletes = %d, want %d", got, want)
	}
	if got, want := len(batch.Sources), 16; got != want {
		t.Errorf("sources = %d, want %d", got, want)
	}
	if got, want := len(batch.Claims), 115; got != want {
		t.Errorf("claims = %d, want %d", got, want)
	}
	subjectLinks := 0
	for _, claim := range batch.Claims {
		subjectLinks += len(claim.SubjectKeys)
	}
	if subjectLinks == 0 {
		t.Error("subject inference produced no links for evidence that names both athletes")
	}
	if got, want := batch.Match.NaturalKey, "2026-06:artyom-morozov:ermes-gasparini:right"; got != want {
		t.Errorf("natural key = %q, want %q", got, want)
	}
	if batch.Match.ScheduledAt != nil {
		t.Errorf("scheduled at = %v, want nil", batch.Match.ScheduledAt)
	}
}

func TestInferSubjectsUsesKnownAliasesAndAllowsUnknown(t *testing.T) {
	if got := inferSubjects("Artem Morozov was ready", "", "Ermes disagreed"); len(got) != 2 || got[0] != "ermes" || got[1] != "morozov" {
		t.Errorf("inferSubjects() = %v, want [ermes morozov]", got)
	}
	if got := inferSubjects("He was ready", "", ""); len(got) != 0 {
		t.Errorf("inferSubjects() = %v, want no subjects", got)
	}
}
