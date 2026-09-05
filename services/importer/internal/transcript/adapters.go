package transcript

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type YTDLPAudioSource struct {
	Command string
}

func (source YTDLPAudioSource) Acquire(ctx context.Context, videoURL string) (AudioArtifact, error) {
	command := source.Command
	if command == "" {
		command = "yt-dlp"
	}
	directory, err := os.MkdirTemp("", "armwrestling-audio-")
	if err != nil {
		return AudioArtifact{}, fmt.Errorf("create audio temporary directory: %w", err)
	}
	outputPattern := filepath.Join(directory, "audio.%(ext)s")
	arguments := []string{"--no-playlist", "--extract-audio", "--audio-format", "mp3", "--output", outputPattern, videoURL}
	commandProcess := exec.CommandContext(ctx, command, arguments...)
	if output, err := commandProcess.CombinedOutput(); err != nil {
		_ = os.RemoveAll(directory)
		return AudioArtifact{}, fmt.Errorf("yt-dlp failed: %w: %s", err, strings.TrimSpace(string(output)))
	}
	files, err := filepath.Glob(filepath.Join(directory, "audio.*"))
	if err != nil || len(files) != 1 {
		_ = os.RemoveAll(directory)
		return AudioArtifact{}, fmt.Errorf("yt-dlp did not produce exactly one audio file")
	}
	return AudioArtifact{SchemaVersion: AudioArtifactSchemaVersion, Path: files[0], Format: "mp3"}, nil
}

func (YTDLPAudioSource) Cleanup(artifact AudioArtifact) error {
	return os.RemoveAll(filepath.Dir(artifact.Path))
}

type OpenAITranscriber struct {
	HTTPClient *http.Client
	BaseURL    string
	APIKey     string
	Model      string
}

func (provider OpenAITranscriber) Transcribe(ctx context.Context, artifact AudioArtifact, keywords []string) (Transcript, json.RawMessage, json.RawMessage, error) {
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
	model := provider.Model
	if model == "" {
		model = "whisper-1"
	}
	_ = writer.WriteField("model", model)
	_ = writer.WriteField("response_format", "verbose_json")
	if len(keywords) > 0 {
		_ = writer.WriteField("prompt", strings.Join(keywords, ", "))
	}
	if err := writer.Close(); err != nil {
		return Transcript{}, nil, nil, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(provider.BaseURL, "/")+"/v1/audio/transcriptions", body)
	if err != nil {
		return Transcript{}, nil, nil, err
	}
	request.Header.Set("Authorization", "Bearer "+provider.APIKey)
	request.Header.Set("Content-Type", writer.FormDataContentType())
	client := provider.HTTPClient
	if client == nil {
		client = http.DefaultClient
	}
	response, err := client.Do(request)
	if err != nil {
		return Transcript{}, nil, nil, fmt.Errorf("OpenAI transcription request failed: %s", Redact(err, provider.APIKey))
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(response.Body)
	if err != nil {
		return Transcript{}, nil, nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return Transcript{}, raw, nil, fmt.Errorf("OpenAI transcription HTTP %d: %s", response.StatusCode, strings.TrimSpace(string(raw)))
	}
	var decoded struct {
		Text     string `json:"text"`
		Language string `json:"language"`
		Segments []struct {
			Start float64 `json:"start"`
			End   float64 `json:"end"`
			Text  string  `json:"text"`
		} `json:"segments"`
	}
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return Transcript{}, raw, nil, fmt.Errorf("decode OpenAI transcript: %w", err)
	}
	transcript := Transcript{SchemaVersion: TranscriptSchemaVersion, Language: decoded.Language, Text: decoded.Text}
	for _, segment := range decoded.Segments {
		transcript.Segments = append(transcript.Segments, Segment{StartSeconds: segment.Start, EndSeconds: segment.End, Text: strings.TrimSpace(segment.Text)})
	}
	return transcript, raw, nil, nil
}

// Redact strips a secret (and its URL-escaped form) from an error message.
// Exported so other OpenAI-calling packages (internal/annotate) don't
// duplicate it.
func Redact(err error, secret string) string {
	message := strings.ReplaceAll(err.Error(), secret, "[REDACTED]")
	return strings.ReplaceAll(message, url.QueryEscape(secret), "[REDACTED]")
}
