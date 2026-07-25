package legacy

import "encoding/json"

type document struct {
	GeneratedAt string            `json:"generated_at"`
	Match       matchRecord       `json:"match"`
	Videos      []json.RawMessage `json:"videos"`
	Sources     []json.RawMessage `json:"sources"`
	Claims      []json.RawMessage `json:"claims"`
}

type matchRecord struct {
	AthleteA    string `json:"athlete_a"`
	AthleteB    string `json:"athlete_b"`
	Arm         string `json:"arm"`
	DateContext string `json:"date_context"`
}

type sourceRecord struct {
	ID            string `json:"id"`
	Title         string `json:"title"`
	URL           string `json:"url"`
	PublishedAt   string `json:"published_at"`
	SelectedModel string `json:"selected_model"`
}

type claimRecord struct {
	VideoID         string `json:"video_id"`
	VideoTitle      string `json:"video_title"`
	SourceURL       string `json:"source_url"`
	SourcePublished string `json:"source_published_at"`
	Claim           string `json:"claim"`
	Timestamp       string `json:"timestamp"`
	Speaker         string `json:"speaker_or_source"`
	Confidence      string `json:"confidence"`
	Relevance       string `json:"relevance"`
	SelectedModel   string `json:"selected_model"`
}
