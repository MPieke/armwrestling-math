package annotate

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/mpieke/armwrestling-math/services/importer/internal/structured"
	"github.com/mpieke/armwrestling-math/services/importer/internal/transcript"
)

type OpenAIAnnotator struct {
	HTTPClient *http.Client
	BaseURL    string
	APIKey     string
	Model      string
}

func (annotator OpenAIAnnotator) ModelName() string { return annotator.Model }

func (annotator OpenAIAnnotator) Annotate(ctx context.Context, claim ClaimContext) (ClaimAnnotation, json.RawMessage, json.RawMessage, error) {
	var output ClaimAnnotation
	schema, err := structured.SchemaFor(&output)
	if err != nil {
		return ClaimAnnotation{}, nil, nil, err
	}
	prompt := fmt.Sprintf(
		"Annotate this armwrestling claim about a match between %s. Use schema version %s. "+
			"subject_athlete_name must be exactly one of the two competitor names if the claim is "+
			"clearly about one of them, or empty if it is general or about both.",
		strings.Join(claim.Competitors, " vs "), AnnotationSchemaVersion,
	)
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
	}{Model: annotator.Model}
	requestBody.Messages = []struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	}{{Role: "system", Content: prompt}, {Role: "user", Content: claim.ClaimText}}
	requestBody.ResponseFormat.Type = "json_schema"
	requestBody.ResponseFormat.JSONSchema.Name = "claim_annotation"
	requestBody.ResponseFormat.JSONSchema.Strict = true
	requestBody.ResponseFormat.JSONSchema.Schema = schema
	encoded, err := json.Marshal(requestBody)
	if err != nil {
		return ClaimAnnotation{}, nil, nil, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(annotator.BaseURL, "/")+"/v1/chat/completions", bytes.NewReader(encoded))
	if err != nil {
		return ClaimAnnotation{}, nil, nil, err
	}
	request.Header.Set("Authorization", "Bearer "+annotator.APIKey)
	request.Header.Set("Content-Type", "application/json")
	client := annotator.HTTPClient
	if client == nil {
		client = http.DefaultClient
	}
	response, err := client.Do(request)
	if err != nil {
		return ClaimAnnotation{}, nil, nil, fmt.Errorf("OpenAI annotation request failed: %s", transcript.Redact(err, annotator.APIKey))
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(response.Body)
	if err != nil {
		return ClaimAnnotation{}, nil, nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return ClaimAnnotation{}, raw, nil, fmt.Errorf("OpenAI annotation HTTP %d: %s", response.StatusCode, strings.TrimSpace(string(raw)))
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
		return ClaimAnnotation{}, raw, nil, fmt.Errorf("decode OpenAI annotation: %w", err)
	}
	if len(envelope.Choices) != 1 || envelope.Choices[0].Message.Content == "" {
		return ClaimAnnotation{}, raw, envelope.Usage, fmt.Errorf("OpenAI annotation response contains no structured output")
	}
	if err := structured.Decode([]byte(envelope.Choices[0].Message.Content), &output); err != nil {
		return ClaimAnnotation{}, raw, envelope.Usage, err
	}
	return output, raw, envelope.Usage, nil
}
