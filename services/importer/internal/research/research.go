package research

import "fmt"

type MatchContext struct {
	NaturalKey  string
	Arm         string
	Competitors []string
}

type Candidate struct {
	VideoID        string
	MatchedQueries []string
}

func BuildPlan(context MatchContext) ([]string, error) {
	if len(context.Competitors) != 2 || context.Competitors[0] == "" || context.Competitors[1] == "" || context.Arm == "" {
		return nil, fmt.Errorf("match context requires two competitors and arm")
	}
	a, b := context.Competitors[0], context.Competitors[1]
	return []string{
		a + " " + b, a + " " + b + " " + context.Arm + " arm", a + " " + b + " prediction", a + " " + b + " analysis",
		a + " interview " + context.Arm + " arm", b + " interview " + context.Arm + " arm",
		a + " training " + context.Arm + " arm", b + " training " + context.Arm + " arm", a + " injury recovery", b + " injury recovery",
	}, nil
}

func Select(lists [][]Candidate, maximum int) []Candidate {
	if maximum <= 0 {
		return nil
	}
	provenance := make(map[string][]string)
	for _, list := range lists {
		for _, candidate := range list {
			provenance[candidate.VideoID] = appendUnique(provenance[candidate.VideoID], candidate.MatchedQueries...)
		}
	}
	selected := make([]Candidate, 0, maximum)
	seen := make(map[string]struct{})
	for offset := 0; offset < longest(lists) && len(selected) < maximum; offset++ {
		for _, list := range lists {
			if offset >= len(list) || len(selected) >= maximum {
				continue
			}
			candidate := list[offset]
			if candidate.VideoID == "" {
				continue
			}
			if _, exists := seen[candidate.VideoID]; exists {
				continue
			}
			candidate.MatchedQueries = provenance[candidate.VideoID]
			seen[candidate.VideoID] = struct{}{}
			selected = append(selected, candidate)
		}
	}
	return selected
}

func appendUnique(values []string, additions ...string) []string {
	seen := make(map[string]struct{}, len(values))
	for _, value := range values {
		seen[value] = struct{}{}
	}
	for _, value := range additions {
		if _, exists := seen[value]; !exists {
			values = append(values, value)
			seen[value] = struct{}{}
		}
	}
	return values
}

func longest(lists [][]Candidate) int {
	length := 0
	for _, list := range lists {
		if len(list) > length {
			length = len(list)
		}
	}
	return length
}
