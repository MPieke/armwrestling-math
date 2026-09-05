package transcript

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/mpieke/armwrestling-math/services/importer/internal/structured"
)

type OpenAIClaimExtractor struct {
	HTTPClient *http.Client
	BaseURL    string
	APIKey     string
	Model      string
}

func (extractor OpenAIClaimExtractor) ModelName() string { return extractor.Model }

func (extractor OpenAIClaimExtractor) Extract(ctx context.Context, value Transcript, match MatchContext) (StructuredExtraction, json.RawMessage, json.RawMessage, error) {
	var output StructuredExtraction
	schema, err := structured.SchemaFor(&output)
	if err != nil {
		return StructuredExtraction{}, nil, nil, err
	}
	prompt := fmt.Sprintf("Extract match-relevant claims about %s versus %s on the %s arm. Use schema version %s. Every timestamp must refer to the transcript segment containing the claim.", match.Competitors[0], match.Competitors[1], match.Arm, ExtractionSchemaVersion)
	requestBody := struct {
		Model    string `json:"model"`
		Messages []struct {
			Role    string `json:"role"`
			Content string `json:"content"`
		} `json:"messages"`
		ResponseFormat struct {
			Type       string `json:"type"`
			JSONSchema struct {
				Name   string            `json:"name"`
				Strict bool              `json:"strict"`
				Schema structured.Schema `json:"schema"`
			} `json:"json_schema"`
		} `json:"response_format"`
	}{Model: extractor.Model}
	requestBody.Messages = []struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	}{{Role: "system", Content: prompt}, {Role: "user", Content: value.Text}}
	requestBody.ResponseFormat.Type = "json_schema"
	requestBody.ResponseFormat.JSONSchema.Name = "youtube_claims"
	requestBody.ResponseFormat.JSONSchema.Strict = true
	requestBody.ResponseFormat.JSONSchema.Schema = schema
	encoded, err := json.Marshal(requestBody)
	if err != nil {
		return StructuredExtraction{}, nil, nil, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(extractor.BaseURL, "/")+"/v1/chat/completions", bytes.NewReader(encoded))
	if err != nil {
		return StructuredExtraction{}, nil, nil, err
	}
	request.Header.Set("Authorization", "Bearer "+extractor.APIKey)
	request.Header.Set("Content-Type", "application/json")
	client := extractor.HTTPClient
	if client == nil {
		client = http.DefaultClient
	}
	response, err := client.Do(request)
	if err != nil {
		return StructuredExtraction{}, nil, nil, fmt.Errorf("OpenAI extraction request failed: %s", Redact(err, extractor.APIKey))
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(response.Body)
	if err != nil {
		return StructuredExtraction{}, nil, nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return StructuredExtraction{}, raw, nil, fmt.Errorf("OpenAI extraction HTTP %d: %s", response.StatusCode, strings.TrimSpace(string(raw)))
	}
	var envelope struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Usage json.RawMessage `json:"usage"`
	}
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return StructuredExtraction{}, raw, nil, fmt.Errorf("decode OpenAI extraction: %w", err)
	}
	if len(envelope.Choices) != 1 || envelope.Choices[0].Message.Content == "" {
		return StructuredExtraction{}, raw, envelope.Usage, fmt.Errorf("OpenAI extraction response contains no structured output")
	}
	if err := structured.Decode([]byte(envelope.Choices[0].Message.Content), &output); err != nil {
		return StructuredExtraction{}, raw, envelope.Usage, err
	}
	return output, raw, envelope.Usage, nil
}
