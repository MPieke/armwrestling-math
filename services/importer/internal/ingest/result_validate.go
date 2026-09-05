package ingest

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
)

const ResultSubmissionSchemaVersion = "result-submission-v1"

var recognizedArms = map[string]bool{"left": true, "right": true}
var recognizedStatuses = map[string]bool{"scheduled": true, "completed": true, "dq": true, "no_contest": true}
var recognizedCompetitorResults = map[string]bool{"": true, "win": true, "loss": true, "no_contest": true}

// ValidateResult enforces the cross-row invariants a single PostgreSQL check
// constraint cannot express. It performs no I/O; a rejected submission never
// reaches the database.
func ValidateResult(submission ResultSubmission) error {
	problems := make([]string, 0)

	if submission.SchemaVersion != ResultSubmissionSchemaVersion {
		problems = append(problems, "unsupported result submission schema version")
	}
	if submission.BatchKey == "" {
		problems = append(problems, "result submission requires a batch key")
	}
	if submission.Event.Slug == "" || submission.Event.Promoter == "" ||
		submission.Event.Name == "" || submission.Event.HeldOn.IsZero() {
		problems = append(problems, "result submission requires an event with slug, promoter, name, and held-on date")
	}
	if !recognizedArms[submission.Arm] {
		problems = append(problems, "unrecognized arm: "+submission.Arm)
	}
	if !recognizedStatuses[submission.Status] {
		problems = append(problems, "unrecognized status: "+submission.Status)
	}
	if submission.ScheduledAt.IsZero() {
		problems = append(problems, "result submission requires a scheduled-at date")
	}
	if len(submission.Competitors) != 2 {
		problems = append(problems, fmt.Sprintf("result submission requires exactly two competitors, got %d", len(submission.Competitors)))
	}
	problems = append(problems, validateCompetitors(submission)...)

	if len(problems) == 0 {
		return nil
	}
	sort.Strings(problems)
	return fmt.Errorf("invalid result submission: %s", strings.Join(problems, "; "))
}

func validateCompetitors(submission ResultSubmission) []string {
	problems := make([]string, 0)
	names := make(map[string]bool, len(submission.Competitors))
	winners := 0
	for index, competitor := range submission.Competitors {
		switch {
		case competitor.AthleteName == "":
			problems = append(problems, fmt.Sprintf("competitor %d requires a name", index))
		case names[competitor.AthleteName]:
			problems = append(problems, "duplicate competitor name: "+competitor.AthleteName)
		}
		names[competitor.AthleteName] = true

		if !recognizedCompetitorResults[competitor.Result] {
			problems = append(problems, fmt.Sprintf("competitor %d has an unrecognized result: %s", index, competitor.Result))
		}
		if competitor.Result == "win" {
			winners++
		}
		if submission.Status == "completed" && competitor.Score == nil {
			problems = append(problems, fmt.Sprintf("competitor %d requires a score for a completed match", index))
		}
	}
	if submission.Status == "completed" && winners != 1 {
		problems = append(problems, fmt.Sprintf("a completed match requires exactly one winner, got %d", winners))
	}
	return problems
}

var nonAlphanumericRun = regexp.MustCompile(`[^a-z0-9]+`)

func slugify(value string) string {
	return strings.Trim(nonAlphanumericRun.ReplaceAllString(strings.ToLower(value), "-"), "-")
}

// buildBaseNaturalKey computes the natural key ResultSubmission mints for a
// match, before any rematch sequence suffix. Athlete slugs are sorted so the
// same match produces the same key regardless of competitor order in the
// source data.
func buildBaseNaturalKey(eventSlug string, competitors []CompetitorResultInput, arm string) string {
	names := make([]string, len(competitors))
	for index, competitor := range competitors {
		names[index] = slugify(competitor.AthleteName)
	}
	sort.Strings(names)
	return eventSlug + ":" + strings.Join(names, ":") + ":" + arm
}
