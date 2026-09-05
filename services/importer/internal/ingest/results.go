package ingest

import "time"

// EventInput identifies the event a submitted match belongs to.
type EventInput struct {
	Slug     string    `json:"slug"`
	Promoter string    `json:"promoter"`
	Name     string    `json:"name"`
	HeldOn   time.Time `json:"held_on"`
}

// CompetitorResultInput is one side of a submitted match. Score and Result
// are empty for a scheduled match with no outcome yet.
type CompetitorResultInput struct {
	AthleteName string `json:"athlete_name"`
	Score       *int   `json:"score,omitempty"`
	Result      string `json:"result,omitempty"`
}

// ResultSubmission is the database-independent boundary that OWNS creating
// event, athlete, match, and competitor-outcome identity -- the opposite
// trust direction from EvidenceSubmission, which only reads existing
// identity and can never create it. Importing a result is how a match
// enters the system in the first place. See docs/architecture/ingestion.md.
type ResultSubmission struct {
	SchemaVersion string                  `json:"schema_version"`
	BatchKey      string                  `json:"batch_key"`
	Event         EventInput              `json:"event"`
	MatchLabel    string                  `json:"match_label,omitempty"`
	Arm           string                  `json:"arm"`
	WeightClass   string                  `json:"weight_class"`
	ScheduledAt   time.Time               `json:"scheduled_at"`
	Status        string                  `json:"status"`
	VideoIDs      []string                `json:"video_ids,omitempty"`
	Competitors   []CompetitorResultInput `json:"competitors"`
}
