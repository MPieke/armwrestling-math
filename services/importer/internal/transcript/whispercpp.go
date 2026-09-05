package transcript

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

// WhisperCPPTranscriber talks to a self-hosted whisper.cpp whisper-server
// instance (docker/whisper/Dockerfile, or the native binary for local
// Metal-accelerated development) instead of OpenAI's API. Its /inference
// endpoint is deliberately OpenAI-response-compatible, so this shares
// decodeVerboseJSONTranscript with OpenAITranscriber rather than
// re-deriving the segment mapping. No API key: self-hosted, nothing to
// redact from an error.
type WhisperCPPTranscriber struct {
	HTTPClient *http.Client
	BaseURL    string
}

func (provider WhisperCPPTranscriber) Transcribe(ctx context.Context, artifact AudioArtifact, keywords []string) (Transcript, json.RawMessage, json.RawMessage, error) {
	file, err := os.Open(artifact.Path)
	if err != nil {
		return Transcript{}, nil, nil, fmt.Errorf("open audio artifact: %w", err)
	}
	defer file.Close()
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	filePart, err := writer.CreateFormFile("file", filepath.Base(artifact.Path))
	if err != nil {
		return Transcript{}, nil, nil, err
	}
	if _, err := io.Copy(filePart, file); err != nil {
		return Transcript{}, nil, nil, fmt.Errorf("copy audio artifact: %w", err)
	}
	_ = writer.WriteField("response_format", "verbose_json")
	_ = writer.WriteField("temperature", "0.0")
	if len(keywords) > 0 {
		_ = writer.WriteField("prompt", strings.Join(keywords, ", "))
	}
	if err := writer.Close(); err != nil {
		return Transcript{}, nil, nil, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(provider.BaseURL, "/")+"/inference", body)
	if err != nil {
		return Transcript{}, nil, nil, err
	}
	request.Header.Set("Content-Type", writer.FormDataContentType())
	client := provider.HTTPClient
	if client == nil {
		client = http.DefaultClient
	}
	response, err := client.Do(request)
	if err != nil {
		return Transcript{}, nil, nil, fmt.Errorf("whisper.cpp transcription request failed: %w", err)
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(response.Body)
	if err != nil {
		return Transcript{}, nil, nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return Transcript{}, raw, nil, fmt.Errorf("whisper.cpp transcription HTTP %d: %s", response.StatusCode, strings.TrimSpace(string(raw)))
	}
	transcript, err := decodeVerboseJSONTranscript(raw)
	if err != nil {
		return Transcript{}, raw, nil, fmt.Errorf("decode whisper.cpp transcript: %w", err)
	}
	return transcript, raw, nil, nil
}
