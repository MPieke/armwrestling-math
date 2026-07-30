//go:build integration

package youtubeingest

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/mpieke/armwrestling-math/services/importer/internal/youtube"
)

const integrationDatabaseLockID int64 = 742016

func TestRunEndToEndWithFakeProvidersAndPostgreSQL(t *testing.T) {
	ctx := context.Background()
	pool := integrationPool(t, ctx)
	resetAndSeed(t, ctx, pool)
	var mutex sync.Mutex
	searchCalls, metadataCalls, geminiCalls := 0, 0, 0
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		mutex.Lock()
		defer mutex.Unlock()
		switch {
		case request.URL.Path == "/youtube/v3/search":
			searchCalls++
			if request.URL.Query().Get("order") != "relevance" || request.URL.Query().Get("q") == "" ||
				request.URL.Query().Get("part") != "snippet" || request.URL.Query().Get("type") != "video" ||
				request.URL.Query().Get("maxResults") != "2" || request.URL.Query().Get("key") != "fixture" {
				t.Errorf("search query = %s", request.URL.RawQuery)
			}
			fmt.Fprint(writer, `{"items":[{"id":{"videoId":"good"}},{"id":{"videoId":"bad"}}]}`)
		case request.URL.Path == "/youtube/v3/videos":
			metadataCalls++
			videoID := request.URL.Query().Get("id")
			if request.URL.Query().Get("part") != "snippet,contentDetails" || request.URL.Query().Get("key") != "fixture" {
				t.Errorf("metadata query = %s", request.URL.RawQuery)
			}
			fmt.Fprintf(writer, `{"items":[{"id":%q,"snippet":{"title":%q,"channelTitle":"Fixture","publishedAt":"2026-06-01T00:00:00Z"},"contentDetails":{"duration":"PT2M"}}]}`, videoID, videoID+" video")
		case strings.Contains(request.URL.Path, ":generateContent"):
			geminiCalls++
			if request.URL.Path != "/v1beta/models/fixture-model:generateContent" || request.URL.Query().Get("key") != "fixture" {
				t.Errorf("Gemini request = %s?%s", request.URL.Path, request.URL.RawQuery)
			}
			body, _ := io.ReadAll(request.Body)
			if !strings.Contains(string(body), `"responseMimeType":"application/json"`) ||
				!strings.Contains(string(body), `"responseJsonSchema"`) {
				t.Errorf("Gemini request lacks structured-output configuration: %s", body)
			}
			if strings.Contains(string(body), "watch?v=bad") {
				http.Error(writer, "fixture failure", http.StatusBadGateway)
				return
			}
			fmt.Fprint(writer, `{"candidates":[{"content":{"parts":[{"text":"{\"schema_version\":\"youtube-claims-v1\",\"claims\":[{\"text\":\"Ermes has improved his setup\",\"timestamp_seconds\":30,\"subject_names\":[\"Ermes Gasparini\"],\"confidence\":\"high\",\"relevance\":\"Relevant setup evidence\",\"claim_type\":\"setup\"}],\"limitations\":[]}"}]}}],"usageMetadata":{"promptTokenCount":10}}`)
		default:
			http.NotFound(writer, request)
		}
	}))
	defer server.Close()
	youtubeClient := youtube.Client{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture"}
	geminiClient := youtube.GeminiClient{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture", Model: "fixture-model"}
	options := Options{MatchNaturalKey: "fixture:right", MaxVideos: 2, SearchPageSize: 2}

	first, err := Run(ctx, pool, youtubeClient, geminiClient, options)
	if err != nil {
		t.Fatal(err)
	}
	if first.Completed != 1 || first.Failed != 1 || first.Skipped != 0 {
		t.Fatalf("first result = %+v", first)
	}
	assertCount(t, ctx, pool, "sources", 2)
	assertCount(t, ctx, pool, "source_extractions where status = 'completed'", 1)
	assertCount(t, ctx, pool, "source_extractions where status = 'failed'", 1)
	assertCount(t, ctx, pool, "claims where source_extraction_id is not null", 1)
	assertCount(t, ctx, pool, "claim_subjects", 1)

	second, err := Run(ctx, pool, youtubeClient, geminiClient, options)
	if err != nil {
		t.Fatal(err)
	}
	if second.Completed != 0 || second.Failed != 1 || second.Skipped != 1 {
		t.Fatalf("second result = %+v", second)
	}
	if searchCalls != 20 || metadataCalls != 4 || geminiCalls != 3 {
		t.Fatalf("provider calls search=%d metadata=%d gemini=%d, want 20, 4, 3", searchCalls, metadataCalls, geminiCalls)
	}
	assertCount(t, ctx, pool, "source_extractions where status = 'completed'", 1)
	assertCount(t, ctx, pool, "source_extractions where status = 'failed'", 2)
	assertCount(t, ctx, pool, "claims", 1)

	direct, err := Run(ctx, pool, youtubeClient, geminiClient, Options{MatchNaturalKey: "fixture:right", VideoIDs: []string{"good"}, MaxVideos: 1, SearchPageSize: 2})
	if err != nil {
		t.Fatal(err)
	}
	if direct.Skipped != 1 || searchCalls != 20 || metadataCalls != 5 || geminiCalls != 3 {
		t.Fatalf("direct result=%+v calls search=%d metadata=%d gemini=%d", direct, searchCalls, metadataCalls, geminiCalls)
	}

	beforeSearch, beforeMetadata, beforeGemini := searchCalls, metadataCalls, geminiCalls
	if _, err := Run(ctx, pool, youtubeClient, geminiClient, Options{MatchNaturalKey: "missing", MaxVideos: 1, SearchPageSize: 1}); err == nil {
		t.Fatal("missing match succeeded")
	}
	if searchCalls != beforeSearch || metadataCalls != beforeMetadata || geminiCalls != beforeGemini {
		t.Fatal("missing match reached an external provider")
	}
}

func integrationPool(t *testing.T, ctx context.Context) *pgxpool.Pool {
	t.Helper()
	databaseURL := os.Getenv("INGEST_TEST_DATABASE_URL")
	config, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	if config.ConnConfig.Database != "armwrestling_math_test" {
		t.Fatalf("integration database must be armwrestling_math_test, got %q", config.ConnConfig.Database)
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
	_, err := pool.Exec(ctx, `truncate claim_subjects, claims, source_extractions, sources, match_competitors, matches, athletes, ingestion_runs restart identity cascade`)
	if err != nil {
		t.Fatal(err)
	}
	_, err = pool.Exec(ctx, `
		with a as (insert into athletes (canonical_name) values ('Artyom Morozov') returning id),
		     b as (insert into athletes (canonical_name) values ('Ermes Gasparini') returning id),
		     m as (insert into matches (natural_key, label, arm) values ('fixture:right', 'Fixture', 'right') returning id)
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
	t.Logf("verified %s count is %d", relation, got)
}
