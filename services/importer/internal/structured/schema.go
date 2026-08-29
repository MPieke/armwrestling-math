package structured

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
)

type Output interface {
	StructuredOutput()
}

type Schema struct {
	Type                 string            `json:"type"`
	Properties           map[string]Schema `json:"properties,omitempty"`
	Required             []string          `json:"required,omitempty"`
	AdditionalProperties *bool             `json:"additionalProperties,omitempty"`
	AnyOf                []Schema          `json:"anyOf,omitempty"`
	Items                *Schema           `json:"items,omitempty"`
	Enum                 []string          `json:"enum,omitempty"`
}

func SchemaFor(output Output) (Schema, error) {
	outputType := reflect.TypeOf(output)
	if outputType.Kind() != reflect.Pointer || outputType.Elem().Kind() != reflect.Struct {
		return Schema{}, fmt.Errorf("structured output must be a pointer to struct")
	}
	return schemaForType(outputType.Elem())
}

func Decode(raw []byte, destination Output) error {
	if err := json.Unmarshal(raw, destination); err != nil {
		return fmt.Errorf("decode structured output: %w", err)
	}
	return nil
}

func schemaForType(valueType reflect.Type) (Schema, error) {
	switch valueType.Kind() {
	case reflect.Pointer:
		value, err := schemaForType(valueType.Elem())
		return Schema{AnyOf: []Schema{value, {Type: "null"}}}, err
	case reflect.String:
		return Schema{Type: "string"}, nil
	case reflect.Int:
		return Schema{Type: "integer"}, nil
	case reflect.Slice:
		item, err := schemaForType(valueType.Elem())
		return Schema{Type: "array", Items: &item}, err
	case reflect.Struct:
		additionalProperties := false
		result := Schema{Type: "object", Properties: make(map[string]Schema), AdditionalProperties: &additionalProperties}
		for index := 0; index < valueType.NumField(); index++ {
			field := valueType.Field(index)
			jsonName := strings.Split(field.Tag.Get("json"), ",")[0]
			if jsonName == "" || jsonName == "-" {
				continue
			}
			property, err := schemaForType(field.Type)
			if err != nil {
				return Schema{}, err
			}
			if enum := field.Tag.Get("enum"); enum != "" {
				property.Enum = strings.Split(enum, ",")
			}
			result.Properties[jsonName] = property
			// OpenAI strict structured outputs require every property to be
			// required. Pointer fields are represented as nullable anyOf schemas.
			result.Required = append(result.Required, jsonName)
		}
		return result, nil
	default:
		return Schema{}, fmt.Errorf("unsupported structured output kind: %s", valueType.Kind())
	}
}
