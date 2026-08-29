package transcript

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestOpenAITranscriberSendsAudioAndPreservesSegments(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/v1/audio/transcriptions" {
			t.Fatalf("path = %q", request.URL.Path)
		}
		if request.Header.Get("Authorization") != "Bearer fixture-key" {
			t.Fatalf("authorization header was not set")
		}
		if err := request.ParseMultipartForm(1024 * 1024); err != nil {
			t.Fatalf("parse multipart request: %v", err)
		}
		if request.FormValue("model") != "whisper-1" || request.FormValue("response_format") != "verbose_json" {
			t.Fatalf("form values = model %q format %q", request.FormValue("model"), request.FormValue("response_format"))
		}
		_, _ = writer.Write([]byte(`{"text":"hello","language":"en","segments":[{"start":12.5,"end":18.25,"text":" hello "}]}`))
	}))
	defer server.Close()

	directory := t.TempDir()
	path := filepath.Join(directory, "audio.mp3")
	if err := os.WriteFile(path, []byte("fixture audio"), 0600); err != nil {
		t.Fatal(err)
	}
	value, _, _, err := (OpenAITranscriber{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture-key", Model: "whisper-1"}).Transcribe(context.Background(), AudioArtifact{Path: path}, []string{"Artyom"})
	if err != nil {
		t.Fatalf("Transcribe returned error: %v", err)
	}
	if len(value.Segments) != 1 || value.Segments[0].StartSeconds != 12.5 || value.Segments[0].Text != "hello" {
		t.Fatalf("transcript = %+v", value)
	}
}

func TestYTDLPAudioSourceUsesDirectCommandAndCleansArtifact(t *testing.T) {
	command := filepath.Join(t.TempDir(), "yt-dlp-fixture")
	script := `#!/bin/sh
output=""
previous=""
last=""
for argument do
  if [ "$previous" = "--output" ]; then output="$argument"; fi
  previous="$argument"
  last="$argument"
done
[ "$last" = "https://youtube.test/watch?v=abc" ] || exit 3
target=$(printf '%s' "$output" | sed 's/%(ext)s/mp3/')
printf 'fixture audio' > "$target"
`
	if err := os.WriteFile(command, []byte(script), 0700); err != nil {
		t.Fatal(err)
	}

	artifact, err := (YTDLPAudioSource{Command: command}).Acquire(context.Background(), "https://youtube.test/watch?v=abc")
	if err != nil {
		t.Fatalf("Acquire returned error: %v", err)
	}
	if artifact.SchemaVersion != AudioArtifactSchemaVersion || artifact.Format != "mp3" {
		t.Fatalf("artifact = %+v", artifact)
	}
	if _, err := os.Stat(artifact.Path); err != nil {
		t.Fatalf("artifact does not exist: %v", err)
	}
	if err := (YTDLPAudioSource{}).Cleanup(artifact); err != nil {
		t.Fatalf("Cleanup returned error: %v", err)
	}
	if _, err := os.Stat(artifact.Path); !os.IsNotExist(err) {
		t.Fatalf("artifact still exists after cleanup, stat error = %v", err)
	}
}

func TestOpenAIClaimExtractorParsesStructuredResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		var body struct {
			Model string `json:"model"`
		}
		if err := json.NewDecoder(request.Body).Decode(&body); err != nil {
			t.Fatalf("decode request: %v", err)
		}
		if body.Model != "gpt-4.1-mini" {
			t.Fatalf("model = %q", body.Model)
		}
		_, _ = writer.Write([]byte(`{"choices":[{"message":{"content":"{\"schema_version\":\"youtube-claims-v1\",\"claims\":[{\"text\":\"improved setup\",\"timestamp_seconds\":12,\"subject_names\":[\"Artyom Morozov\"],\"confidence\":\"high\",\"relevance\":\"form\",\"claim_type\":\"form\"}],\"limitations\":[]}"}}],"usage":{"total_tokens":11}}`))
	}))
	defer server.Close()

	value, _, usage, err := (OpenAIClaimExtractor{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture-key", Model: "gpt-4.1-mini"}).Extract(context.Background(), Transcript{Text: strings.Repeat("claim transcript ", 2)}, MatchContext{Competitors: []string{"Artyom Morozov", "Ermes Gasparini"}, Arm: "right"})
	if err != nil {
		t.Fatalf("Extract returned error: %v", err)
	}
	if len(value.Claims) != 1 || value.Claims[0].Text != "improved setup" || *value.Claims[0].TimestampSeconds != 12 {
		t.Fatalf("extraction = %+v", value)
	}
	if string(usage) != `{"total_tokens":11}` {
		t.Fatalf("usage = %s", usage)
	}
}
