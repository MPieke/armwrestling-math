package structured

import (
	"encoding/json"
	"strings"
	"testing"
)

type fixture struct {
	Name  string `json:"name"`
	Count *int   `json:"count,omitempty"`
}

func (*fixture) StructuredOutput() {}

func TestSchemaForAndDecode(t *testing.T) {
	schema, err := SchemaFor(&fixture{})
	if err != nil {
		t.Fatal(err)
	}
	if schema.Type != "object" || schema.Properties["name"].Type != "string" || len(schema.Required) != 2 {
		t.Fatalf("schema = %#v", schema)
	}
	if len(schema.Properties["count"].AnyOf) != 2 || schema.Properties["count"].AnyOf[1].Type != "null" {
		t.Fatalf("nullable count schema = %#v", schema.Properties["count"])
	}
	encoded, err := json.Marshal(schema)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(encoded), `"type":""`) {
		t.Fatalf("schema contains an empty type: %s", encoded)
	}
	if schema.AdditionalProperties == nil || *schema.AdditionalProperties {
		t.Fatalf("schema additionalProperties = %#v, want false", schema.AdditionalProperties)
	}
	var decoded fixture
	if err := Decode([]byte(`{"name":"evidence","count":2}`), &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded.Name != "evidence" || decoded.Count == nil || *decoded.Count != 2 {
		t.Fatalf("decoded = %#v", decoded)
	}
}
