package structured

import "testing"

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
	if schema.Type != "object" || schema.Properties["name"].Type != "string" || len(schema.Required) != 1 {
		t.Fatalf("schema = %#v", schema)
	}
	var decoded fixture
	if err := Decode([]byte(`{"name":"evidence","count":2}`), &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded.Name != "evidence" || decoded.Count == nil || *decoded.Count != 2 {
		t.Fatalf("decoded = %#v", decoded)
	}
}
