package youtube

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"

	"github.com/mpieke/armwrestling-math/services/importer/internal/structured"
)

const PromptVersion = "youtube-claims-v1"

type GeminiClient struct {
	HTTPClient *http.Client
	BaseURL    string
	APIKey     string
	Model      string
}

type Analysis struct {
	Output      GeminiExtractionResponse
	RawResponse json.RawMessage
	Usage       json.RawMessage
}

func (client GeminiClient) Analyze(ctx context.Context, video Video, competitors []string, arm string) (Analysis, error) {
	var output GeminiExtractionResponse
	schema, err := structured.SchemaFor(&output)
	if err != nil {
		return Analysis{}, err
	}
	prompt := fmt.Sprintf("Extract match-relevant claims about %s versus %s on the %s arm. Use schema version %s.", competitors[0], competitors[1], arm, GeminiExtractionSchemaVersionV1)
	requestBody := struct {
		Contents []struct {
			Parts []geminiPart `json:"parts"`
		} `json:"contents"`
		GenerationConfig struct {
			ResponseMIMEType   string            `json:"responseMimeType"`
			ResponseJSONSchema structured.Schema `json:"responseJsonSchema"`
		} `json:"generationConfig"`
	}{}
	requestBody.Contents = append(requestBody.Contents, struct {
		Parts []geminiPart `json:"parts"`
	}{Parts: []geminiPart{{Text: prompt}, {FileData: &geminiFileData{FileURI: video.URL, MIMEType: "video/mp4"}}}})
	requestBody.GenerationConfig.ResponseMIMEType = "application/json"
	requestBody.GenerationConfig.ResponseJSONSchema = schema
	encoded, err := json.Marshal(requestBody)
	if err != nil {
		return Analysis{}, err
	}
	endpoint := strings.TrimRight(client.BaseURL, "/") + "/v1beta/models/" + url.PathEscape(client.Model) + ":generateContent?key=" + url.QueryEscape(client.APIKey)
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(encoded))
	if err != nil {
		return Analysis{}, err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := client.HTTPClient.Do(request)
	if err != nil {
		return Analysis{}, fmt.Errorf("Gemini request failed: %s", redactProviderError(err, client.APIKey))
	}
	defer response.Body.Close()
	raw, err := io.ReadAll(response.Body)
	if err != nil {
		return Analysis{}, err
	}
	if response.StatusCode != http.StatusOK {
		return Analysis{}, fmt.Errorf("Gemini HTTP %d: %s", response.StatusCode, raw)
	}
	var envelope struct {
		Candidates []struct {
			Content struct {
				Parts []struct {
					Text string `json:"text"`
				} `json:"parts"`
			} `json:"content"`
		} `json:"candidates"`
		Usage json.RawMessage `json:"usageMetadata"`
	}
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return Analysis{}, fmt.Errorf("decode Gemini response: %w", err)
	}
	if len(envelope.Candidates) != 1 || len(envelope.Candidates[0].Content.Parts) == 0 {
		return Analysis{}, fmt.Errorf("Gemini response contains no structured output")
	}
	if err := structured.Decode([]byte(envelope.Candidates[0].Content.Parts[0].Text), &output); err != nil {
		return Analysis{}, err
	}
	return Analysis{Output: output, RawResponse: raw, Usage: envelope.Usage}, nil
}

type geminiPart struct {
	Text     string          `json:"text,omitempty"`
	FileData *geminiFileData `json:"fileData,omitempty"`
}

type geminiFileData struct {
	FileURI  string `json:"fileUri"`
	MIMEType string `json:"mimeType"`
}
