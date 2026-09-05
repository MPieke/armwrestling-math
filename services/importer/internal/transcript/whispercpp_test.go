package transcript

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestWhisperCPPTranscriberSendsAudioAndPreservesSegments(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/inference" {
			t.Fatalf("path = %q", request.URL.Path)
		}
		if request.Header.Get("Authorization") != "" {
			t.Fatalf("self-hosted request must not send an Authorization header")
		}
		if err := request.ParseMultipartForm(1024 * 1024); err != nil {
			t.Fatalf("parse multipart request: %v", err)
		}
		if request.FormValue("response_format") != "verbose_json" {
			t.Fatalf("response_format = %q", request.FormValue("response_format"))
		}
		_, _ = writer.Write([]byte(`{"text":"hello","language":"english","segments":[{"start":12.5,"end":18.25,"text":" hello "}]}`))
	}))
	defer server.Close()

	directory := t.TempDir()
	path := filepath.Join(directory, "audio.wav")
	if err := os.WriteFile(path, []byte("fixture audio"), 0600); err != nil {
		t.Fatal(err)
	}
	value, _, _, err := (WhisperCPPTranscriber{HTTPClient: server.Client(), BaseURL: server.URL}).Transcribe(context.Background(), AudioArtifact{Path: path}, []string{"Artyom"})
	if err != nil {
		t.Fatalf("Transcribe returned error: %v", err)
	}
	if len(value.Segments) != 1 || value.Segments[0].StartSeconds != 12.5 || value.Segments[0].Text != "hello" {
		t.Fatalf("transcript = %+v", value)
	}
}

func TestWhisperCPPTranscriberReportsHTTPFailures(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.WriteHeader(http.StatusInternalServerError)
		_, _ = writer.Write([]byte("model not loaded"))
	}))
	defer server.Close()

	directory := t.TempDir()
	path := filepath.Join(directory, "audio.wav")
	if err := os.WriteFile(path, []byte("fixture audio"), 0600); err != nil {
		t.Fatal(err)
	}
	_, _, _, err := (WhisperCPPTranscriber{HTTPClient: server.Client(), BaseURL: server.URL}).Transcribe(context.Background(), AudioArtifact{Path: path}, nil)
	if err == nil {
		t.Fatal("expected an error for a non-2xx response")
	}
}
