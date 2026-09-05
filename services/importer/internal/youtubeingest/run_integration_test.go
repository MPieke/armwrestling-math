//go:build integration

package youtubeingest

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtube"
)

const integrationDatabaseLockID int64 = 742016

func TestRunEndToEndWithFakeProvidersAndPostgreSQL(t *testing.T) {
	ctx := context.Background()
	pool := integrationPool(t, ctx)
	resetAndSeed(t, ctx, pool)
	var mutex sync.Mutex
	searchCalls, metadataCalls := 0, 0
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		mutex.Lock()
		defer mutex.Unlock()
		switch request.URL.Path {
		case "/youtube/v3/search":
			searchCalls++
			fmt.Fprint(writer, `{"items":[{"id":{"videoId":"good"}},{"id":{"videoId":"bad"}}]}`)
		case "/youtube/v3/videos":
			metadataCalls++
			videoID := request.URL.Query().Get("id")
			fmt.Fprintf(writer, `{"items":[{"id":%q,"snippet":{"title":%q,"channelTitle":"Fixture","publishedAt":"2026-06-01T00:00:00Z"},"contentDetails":{"duration":"PT2M"}}]}`, videoID, videoID+" video")
		default:
			http.NotFound(writer, request)
		}
	}))
	defer server.Close()
	youtubeClient := youtube.Client{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture"}
	audio := &fakeAudioSource{}
	transcriber := fakeTranscriber{}
	extractor := &fakeExtractor{}
	options := Options{MatchNaturalKey: "fixture:right", MaxVideos: 2, SearchPageSize: 2}

	first, err := Run(ctx, pool, youtubeClient, audio, transcriber, extractor, options)
	if err != nil {
		t.Fatal(err)
	}
	if first.Completed != 1 || first.Failed != 1 || first.Skipped != 0 {
		t.Fatalf("first result = %+v", first)
	}
	assertCount(t, ctx, pool, "sources", 2)
	assertCount(t, ctx, pool, "source_extractions where provider = 'openai' and status = 'completed'", 1)
	assertCount(t, ctx, pool, "source_extractions where provider = 'openai' and status = 'failed'", 1)
	assertCount(t, ctx, pool, "claims where source_extraction_id is not null", 1)
	if audio.acquired != 2 || audio.cleaned != 2 || extractor.calls != 2 {
		t.Fatalf("fake provider calls audio=(%d,%d) extractor=%d", audio.acquired, audio.cleaned, extractor.calls)
	}

	second, err := Run(ctx, pool, youtubeClient, audio, transcriber, extractor, options)
	if err != nil {
		t.Fatal(err)
	}
	if second.Completed != 0 || second.Failed != 1 || second.Skipped != 1 {
		t.Fatalf("second result = %+v", second)
	}
	if audio.acquired != 3 || audio.cleaned != 3 || extractor.calls != 3 {
		t.Fatalf("replay calls audio=(%d,%d) extractor=%d", audio.acquired, audio.cleaned, extractor.calls)
	}

	direct, err := Run(ctx, pool, youtubeClient, audio, transcriber, extractor, Options{MatchNaturalKey: "fixture:right", VideoIDs: []string{"good"}, MaxVideos: 1, SearchPageSize: 2})
	if err != nil {
		t.Fatal(err)
	}
	if direct.Skipped != 1 || searchCalls != 20 || metadataCalls != 5 || audio.acquired != 3 || extractor.calls != 3 {
		t.Fatalf("direct result=%+v calls search=%d metadata=%d audio=%d extractor=%d", direct, searchCalls, metadataCalls, audio.acquired, extractor.calls)
	}
}

// TestRunSearchesForAdditionalVideosWhenMaxVideosExceedsExplicitIDs proves
// an explicit video ID no longer forecloses discovering other videos about
// the same match (e.g. a separate interview): it's always included, and
// search fills any remaining MaxVideos slots.
func TestRunSearchesForAdditionalVideosWhenMaxVideosExceedsExplicitIDs(t *testing.T) {
	ctx := context.Background()
	pool := integrationPool(t, ctx)
	resetAndSeed(t, ctx, pool)
	searchCalls := 0
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		switch request.URL.Path {
		case "/youtube/v3/search":
			searchCalls++
			fmt.Fprint(writer, `{"items":[{"id":{"videoId":"discovered"}}]}`)
		case "/youtube/v3/videos":
			videoID := request.URL.Query().Get("id")
			fmt.Fprintf(writer, `{"items":[{"id":%q,"snippet":{"title":%q,"channelTitle":"Fixture","publishedAt":"2026-06-01T00:00:00Z"},"contentDetails":{"duration":"PT2M"}}]}`, videoID, videoID+" video")
		default:
			http.NotFound(writer, request)
		}
	}))
	defer server.Close()
	youtubeClient := youtube.Client{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture"}
	extractor := &fakeExtractor{}

	result, err := Run(ctx, pool, youtubeClient, &fakeAudioSource{}, fakeTranscriber{}, extractor,
		Options{MatchNaturalKey: "fixture:right", VideoIDs: []string{"known"}, MaxVideos: 2, SearchPageSize: 2})
	if err != nil {
		t.Fatal(err)
	}
	if searchCalls == 0 {
		t.Fatal("expected search to run because MaxVideos (2) exceeds the explicit video count (1)")
	}
	if result.Selected != 2 {
		t.Fatalf("selected = %d, want 2 (the explicit video plus one discovered)", result.Selected)
	}
	assertCount(t, ctx, pool, "sources where external_id = 'known'", 1)
	assertCount(t, ctx, pool, "sources where external_id = 'discovered'", 1)
}

type fakeAudioSource struct{ acquired, cleaned int }

func (source *fakeAudioSource) Acquire(_ context.Context, videoURL string) (transcript.AudioArtifact, error) {
	source.acquired++
	return transcript.AudioArtifact{SchemaVersion: transcript.AudioArtifactSchemaVersion, Path: videoURL, Format: "mp3"}, nil
}

func (source *fakeAudioSource) Cleanup(transcript.AudioArtifact) error {
	source.cleaned++
	return nil
}

type fakeTranscriber struct{}

func (fakeTranscriber) Transcribe(_ context.Context, artifact transcript.AudioArtifact, _ []string) (transcript.Transcript, json.RawMessage, json.RawMessage, error) {
	return transcript.Transcript{SchemaVersion: transcript.TranscriptSchemaVersion, Text: artifact.Path, Segments: []transcript.Segment{{StartSeconds: 0, EndSeconds: 121, Text: artifact.Path}}}, json.RawMessage(`{"text":"fixture"}`), json.RawMessage(`{"total_tokens":1}`), nil
}

type fakeExtractor struct{ calls int }

func (extractor *fakeExtractor) ModelName() string { return "fixture-model" }

func (extractor *fakeExtractor) Extract(_ context.Context, value transcript.Transcript, _ transcript.MatchContext) (transcript.StructuredExtraction, json.RawMessage, json.RawMessage, error) {
	extractor.calls++
	if strings.Contains(value.Text, "bad") {
		return transcript.StructuredExtraction{}, nil, nil, errors.New("fixture extraction failure")
	}
	timestamp := 121
	return transcript.StructuredExtraction{SchemaVersion: transcript.ExtractionSchemaVersion, Claims: []transcript.Claim{{Text: "Ermes has improved his setup", TimestampSeconds: &timestamp, SubjectNames: []string{"Ermes Gasparini"}, Confidence: "high", Relevance: "Relevant setup evidence", ClaimType: "setup"}}}, json.RawMessage(`{"claims":1}`), json.RawMessage(`{"total_tokens":1}`), nil
}

func integrationPool(t *testing.T, ctx context.Context) *pgxpool.Pool {
	t.Helper()
	databaseURL := os.Getenv("INGEST_TEST_DATABASE_URL")
	configuration, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	if configuration.ConnConfig.Database != "armwrestling_math_test" {
		t.Fatalf("integration database must be armwrestling_math_test, got %q", configuration.ConnConfig.Database)
	}
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	connection, err := pool.Acquire(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := connection.Exec(ctx, "select pg_advisory_lock($1)", integrationDatabaseLockID); err != nil {
		connection.Release()
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_, _ = connection.Exec(ctx, "select pg_advisory_unlock($1)", integrationDatabaseLockID)
		connection.Release()
	})
	return pool
}

func resetAndSeed(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()
	_, err := pool.Exec(ctx, `truncate claim_subjects, claims, source_extractions, sources, match_videos, match_competitors, matches, events, athletes, ingestion_runs restart identity cascade`)
	if err != nil {
		t.Fatal(err)
	}
	_, err = pool.Exec(ctx, `
		with a as (insert into athletes (canonical_name) values ('Artyom Morozov') returning id),
		     b as (insert into athletes (canonical_name) values ('Ermes Gasparini') returning id),
		     e as (insert into events (slug, promoter, name, held_on) values ('fixture-event', 'Fixture Promoter', 'Fixture Event', '2026-06-15') returning id),
		     m as (
		         insert into matches (natural_key, label, arm, weight_class, scheduled_at, event_id, status)
		         select 'fixture:right', 'Fixture', 'right', '105 kg', '2026-06-15T18:30:00Z', e.id, 'scheduled' from e
		         returning id
		     )
		insert into match_competitors (match_id, athlete_id)
		select m.id, athlete.id from m cross join (select id from a union all select id from b) athlete`)
	if err != nil {
		t.Fatal(err)
	}
}

func assertCount(t *testing.T, ctx context.Context, pool *pgxpool.Pool, relation string, want int) {
	t.Helper()
	var got int
	if err := pool.QueryRow(ctx, "select count(*) from "+relation).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("%s count = %d, want %d", relation, got, want)
	}
}
