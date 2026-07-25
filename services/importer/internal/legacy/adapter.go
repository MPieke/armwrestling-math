package legacy

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
)

const batchKey = "legacy-ermes-morozov-v1"

func BuildBatch(paths []string) (ingest.IngestBatch, error) {
	if len(paths) == 0 {
		return ingest.IngestBatch{}, fmt.Errorf("at least one legacy evidence path is required")
	}
	var match matchRecord
	sources := make(map[string]sourceInput)
	claims := make([]ingest.ClaimInput, 0)

	for _, path := range paths {
		document, err := readDocument(path)
		if err != nil {
			return ingest.IngestBatch{}, err
		}
		if err := mergeMatch(&match, document.Match); err != nil {
			return ingest.IngestBatch{}, fmt.Errorf("%s: %w", path, err)
		}
		extractedAt, err := requiredTime(document.GeneratedAt, "generated_at")
		if err != nil {
			return ingest.IngestBatch{}, fmt.Errorf("%s: %w", path, err)
		}
		metadata, err := decodeSources(document.Videos, document.Sources)
		if err != nil {
			return ingest.IngestBatch{}, fmt.Errorf("%s: %w", path, err)
		}
		// The primary export's videos are evidence sources; the expanded export's
		// sources are candidates, so only its claim-referenced sources are imported.
		if len(document.Videos) > 0 {
			for id, source := range metadata {
				if _, exists := sources[id]; !exists {
					sources[id] = source
				}
			}
		}
		for _, rawClaim := range document.Claims {
			claim, err := decodeClaim(rawClaim, extractedAt)
			if err != nil {
				return ingest.IngestBatch{}, fmt.Errorf("%s: %w", path, err)
			}
			if _, exists := sources[claim.sourceID]; !exists {
				if source, known := metadata[claim.sourceID]; known {
					sources[claim.sourceID] = source
				} else {
					sources[claim.sourceID] = claim.source
				}
			}
			claims = append(claims, claim.input)
		}
	}
	return makeBatch(match, sources, claims)
}

type sourceInput struct{ input ingest.SourceInput }
type decodedClaim struct {
	sourceID string
	source   sourceInput
	input    ingest.ClaimInput
}

func readDocument(path string) (document, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return document{}, fmt.Errorf("read %s: %w", path, err)
	}
	var parsed document
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return document{}, fmt.Errorf("parse %s: %w", path, err)
	}
	return parsed, nil
}

func decodeSources(groups ...[]json.RawMessage) (map[string]sourceInput, error) {
	result := make(map[string]sourceInput)
	for _, group := range groups {
		for _, raw := range group {
			var source sourceRecord
			if err := json.Unmarshal(raw, &source); err != nil {
				return nil, fmt.Errorf("parse source: %w", err)
			}
			if source.ID == "" || source.URL == "" {
				continue
			}
			publishedAt, err := parseTime(source.PublishedAt)
			if err != nil {
				return nil, err
			}
			result[source.ID] = sourceInput{input: ingest.SourceInput{
				Key: sourceKey(source.ID), SourceType: "youtube", ExternalID: source.ID, URL: source.URL,
				Title: stringPointer(source.Title), PublishedAt: publishedAt, RawPayload: raw,
			}}
		}
	}
	return result, nil
}

func decodeClaim(raw json.RawMessage, extractedAt time.Time) (decodedClaim, error) {
	var claim claimRecord
	if err := json.Unmarshal(raw, &claim); err != nil {
		return decodedClaim{}, fmt.Errorf("parse claim: %w", err)
	}
	if claim.VideoID == "" || claim.Claim == "" {
		return decodedClaim{}, fmt.Errorf("claim requires video_id and claim")
	}
	timestamp, err := parseTimestamp(claim.Timestamp)
	if err != nil {
		return decodedClaim{}, err
	}
	publishedAt, err := parseTime(claim.SourcePublished)
	if err != nil {
		return decodedClaim{}, err
	}
	sourceURL := claim.SourceURL
	if sourceURL == "" {
		sourceURL = "https://www.youtube.com/watch?v=" + claim.VideoID
	}
	return decodedClaim{
		sourceID: claim.VideoID,
		source: sourceInput{input: ingest.SourceInput{
			Key: sourceKey(claim.VideoID), SourceType: "youtube", ExternalID: claim.VideoID, URL: sourceURL,
			Title: stringPointer(claim.VideoTitle), PublishedAt: publishedAt,
			RawPayload: raw,
		}},
		input: ingest.ClaimInput{
			SourceKey: sourceKey(claim.VideoID), MatchKey: "ermes-vs-morozov-2026", Text: claim.Claim,
			SubjectKeys:      inferSubjects(claim.Claim, claim.Speaker, claim.Relevance),
			TimestampSeconds: timestamp, Speaker: stringPointer(claim.Speaker), Confidence: stringPointer(claim.Confidence),
			Relevance: stringPointer(claim.Relevance), ObservedAt: publishedAt, ExtractedAt: extractedAt,
			ExtractionModel: stringPointer(claim.SelectedModel), RawPayload: raw,
		},
	}, nil
}

func makeBatch(match matchRecord, sources map[string]sourceInput, claims []ingest.ClaimInput) (ingest.IngestBatch, error) {
	period, err := datePeriod(match.DateContext)
	if err != nil {
		return ingest.IngestBatch{}, err
	}
	if period == "" {
		return ingest.IngestBatch{}, fmt.Errorf("match date_context is required for the natural key")
	}
	competitors := []string{"ermes", "morozov"}
	slugs := []string{"ermes-gasparini", "artyom-morozov"}
	sort.Strings(slugs)
	sourceList := make([]ingest.SourceInput, 0, len(sources))
	for _, source := range sources {
		sourceList = append(sourceList, source.input)
	}
	sort.Slice(sourceList, func(i, j int) bool { return sourceList[i].Key < sourceList[j].Key })
	return ingest.IngestBatch{
		BatchKey: batchKey,
		Athletes: []ingest.AthleteInput{{Key: "ermes", CanonicalName: "Ermes Gasparini"}, {Key: "morozov", CanonicalName: "Artyom Morozov"}},
		Match: ingest.MatchInput{
			Key: "ermes-vs-morozov-2026", NaturalKey: strings.Join(append([]string{period}, slugs...), ":") + ":" + match.Arm,
			Label: match.AthleteA + " vs " + match.AthleteB, Arm: match.Arm, Competitors: competitors,
		},
		Sources: sourceList, Claims: claims,
	}, nil
}

func mergeMatch(current *matchRecord, next matchRecord) error {
	if current.AthleteA == "" {
		*current = next
		return nil
	}
	if current.AthleteA != next.AthleteA || current.AthleteB != next.AthleteB || current.Arm != next.Arm {
		return fmt.Errorf("legacy files describe different matches")
	}
	if current.DateContext == "" {
		current.DateContext = next.DateContext
	}
	return nil
}

func requiredTime(value, field string) (time.Time, error) {
	parsed, err := parseTime(value)
	if err != nil {
		return time.Time{}, err
	}
	if parsed == nil {
		return time.Time{}, fmt.Errorf("%s is required", field)
	}
	return *parsed, nil
}

func sourceKey(id string) string { return "youtube:" + id }
