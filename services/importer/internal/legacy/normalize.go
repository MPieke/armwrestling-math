package legacy

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

var athleteAliases = map[string]string{
	"ermes gasparini": "ermes",
	"ermes":           "ermes",
	"artyom morozov":  "morozov",
	"artem morozov":   "morozov",
	"morozov":         "morozov",
	"steelmorozov":    "morozov",
}

func inferSubjects(text, speaker, relevance string) []string {
	haystack := strings.ToLower(text + " " + speaker + " " + relevance)
	found := make(map[string]bool)
	for alias, key := range athleteAliases {
		if strings.Contains(haystack, alias) {
			found[key] = true
		}
	}
	keys := make([]string, 0, len(found))
	for key := range found {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func parseTimestamp(value string) (*int, error) {
	if value == "" {
		return nil, nil
	}
	parts := strings.Split(value, ":")
	if len(parts) != 2 && len(parts) != 3 {
		return nil, fmt.Errorf("invalid timestamp %q", value)
	}
	seconds := 0
	for _, part := range parts {
		unit, err := strconv.Atoi(part)
		if err != nil || unit < 0 {
			return nil, fmt.Errorf("invalid timestamp %q", value)
		}
		seconds = seconds*60 + unit
	}
	return &seconds, nil
}

func parseTime(value string) (*time.Time, error) {
	if value == "" {
		return nil, nil
	}
	parsed, err := time.Parse(time.RFC3339, value)
	if err != nil {
		return nil, fmt.Errorf("parse time %q: %w", value, err)
	}
	return &parsed, nil
}

func datePeriod(value string) (string, error) {
	if value == "" {
		return "", nil
	}
	parsed, err := time.Parse("January 2006", value)
	if err != nil {
		return "", fmt.Errorf("parse date context %q: %w", value, err)
	}
	return parsed.Format("2006-01"), nil
}

func stringPointer(value string) *string {
	if value == "" {
		return nil
	}
	return &value
}
