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
	selected := make([]Candidate, 0, maximum)
	seen := make(map[string]int)
	for offset := 0; len(selected) < maximum; offset++ {
		progressed := false
		for _, list := range lists {
			if offset >= len(list) || len(selected) == maximum {
				continue
			}
			candidate := list[offset]
			if candidate.VideoID == "" {
				continue
			}
			if index, exists := seen[candidate.VideoID]; exists {
				selected[index].MatchedQueries = appendUnique(selected[index].MatchedQueries, candidate.MatchedQueries...)
				continue
			}
			candidate.MatchedQueries = appendUnique(nil, candidate.MatchedQueries...)
			seen[candidate.VideoID] = len(selected)
			selected = append(selected, candidate)
			progressed = true
		}
		if !progressed && offset >= longest(lists) {
			return selected
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
