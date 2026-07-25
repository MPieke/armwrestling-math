package ingest

import (
	"fmt"
	"sort"
	"strings"
)

func Validate(batch IngestBatch) error {
	problems := make([]string, 0)
	if batch.BatchKey == "" {
		problems = append(problems, "batch key is required")
	}
	athletes := make(map[string]struct{}, len(batch.Athletes))
	for _, athlete := range batch.Athletes {
		if athlete.Key == "" || athlete.CanonicalName == "" {
			problems = append(problems, "athletes require key and canonical name")
			continue
		}
		if _, exists := athletes[athlete.Key]; exists {
			problems = append(problems, "duplicate athlete key: "+athlete.Key)
		}
		athletes[athlete.Key] = struct{}{}
	}
	if batch.Match.Key == "" || batch.Match.NaturalKey == "" || batch.Match.Arm == "" {
		problems = append(problems, "match requires key, natural key, and arm")
	}
	for _, key := range batch.Match.Competitors {
		if _, exists := athletes[key]; !exists {
			problems = append(problems, "match references unknown athlete: "+key)
		}
	}
	sources := make(map[string]struct{}, len(batch.Sources))
	for _, source := range batch.Sources {
		if source.Key == "" || source.SourceType == "" || source.ExternalID == "" || source.URL == "" {
			problems = append(problems, "sources require key, type, external ID, and URL")
			continue
		}
		if _, exists := sources[source.Key]; exists {
			problems = append(problems, "duplicate source key: "+source.Key)
		}
		sources[source.Key] = struct{}{}
	}
	for index, claim := range batch.Claims {
		if claim.SourceKey == "" || claim.MatchKey == "" || claim.Text == "" || claim.ExtractedAt.IsZero() {
			problems = append(problems, fmt.Sprintf("claim %d requires source, match, text, and extracted-at", index))
		}
		if claim.MatchKey != batch.Match.Key {
			problems = append(problems, fmt.Sprintf("claim %d references unknown match: %s", index, claim.MatchKey))
		}
		if _, exists := sources[claim.SourceKey]; !exists {
			problems = append(problems, fmt.Sprintf("claim %d references unknown source: %s", index, claim.SourceKey))
		}
		for _, key := range claim.SubjectKeys {
			if _, exists := athletes[key]; !exists {
				problems = append(problems, fmt.Sprintf("claim %d references unknown subject: %s", index, key))
			}
		}
	}
	if len(problems) == 0 {
		return nil
	}
	sort.Strings(problems)
	return fmt.Errorf("invalid ingestion batch: %s", strings.Join(problems, "; "))
}
