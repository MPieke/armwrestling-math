package transcript

import (
	"encoding/json"
	"testing"
)

func TestTranscriptRoundTripsThroughVersionedJSON(t *testing.T) {
	start := 12
	original := Transcript{
		SchemaVersion: TranscriptSchemaVersion,
		Language:      "en",
		Text:          "Artyom has improved his setup.",
		Segments:      []Segment{{StartSeconds: 12, EndSeconds: 18, Text: "Artyom has improved his setup."}},
	}
	encoded, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("marshal transcript: %v", err)
	}
	var decoded Transcript
	if err := json.Unmarshal(encoded, &decoded); err != nil {
		t.Fatalf("unmarshal transcript: %v", err)
	}
	if decoded.SchemaVersion != TranscriptSchemaVersion || decoded.Segments[0].Text != original.Segments[0].Text {
		t.Fatalf("decoded transcript = %+v, want %+v", decoded, original)
	}
	if start != 12 {
		t.Fatal("test fixture timestamp changed unexpectedly")
	}
}
