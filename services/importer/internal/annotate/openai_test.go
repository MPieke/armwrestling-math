package annotate

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestOpenAIAnnotatorParsesStructuredResponse(t *testing.T) {
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
		_, _ = writer.Write([]byte(`{"choices":[{"message":{"content":"{\"claim_type\":\"tactic\",\"concepts\":[\"top_roll\"],\"subject_athlete_name\":\"Ermes Gasparini\",\"arm\":\"right\",\"temporality\":\"current_form\",\"certainty\":\"observed\"}"}}],"usage":{"total_tokens":9}}`))
	}))
	defer server.Close()

	annotation, _, usage, err := (OpenAIAnnotator{HTTPClient: server.Client(), BaseURL: server.URL, APIKey: "fixture-key", Model: "gpt-4.1-mini"}).
		Annotate(context.Background(), ClaimContext{ClaimID: 1, ClaimText: "Ermes has a strong top roll", Competitors: []string{"Ermes Gasparini", "Artyom Morozov"}})
	if err != nil {
		t.Fatalf("Annotate returned error: %v", err)
	}
	if annotation.ClaimType != "tactic" || len(annotation.Concepts) != 1 || annotation.Concepts[0] != "top_roll" {
		t.Fatalf("annotation = %+v", annotation)
	}
	if annotation.SubjectAthleteName != "Ermes Gasparini" {
		t.Fatalf("subject_athlete_name = %q", annotation.SubjectAthleteName)
	}
	if string(usage) != `{"total_tokens":9}` {
		t.Fatalf("usage = %s", usage)
	}
}

func TestOpenAIAnnotatorRedactsAPIKeyOnTransportFailure(t *testing.T) {
	annotator := OpenAIAnnotator{HTTPClient: http.DefaultClient, BaseURL: "http://127.0.0.1:0", APIKey: "super-secret-key", Model: "gpt-4.1-mini"}
	_, _, _, err := annotator.Annotate(context.Background(), ClaimContext{ClaimText: "x", Competitors: []string{"A", "B"}})
	if err == nil {
		t.Fatal("expected a transport error")
	}
	if strings.Contains(err.Error(), "super-secret-key") {
		t.Fatalf("error leaked API key: %v", err)
	}
}
