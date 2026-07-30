package research

import (
	"reflect"
	"testing"
)

func TestBuildPlanAndSelect(t *testing.T) {
	plan, err := BuildPlan(MatchContext{Arm: "right", Competitors: []string{"Ermes", "Morozov"}})
	if err != nil {
		t.Fatal(err)
	}
	if len(plan) != 10 || plan[0] != "Ermes Morozov" || plan[9] != "Morozov injury recovery" {
		t.Fatalf("plan = %#v", plan)
	}
	selected := Select([][]Candidate{{{VideoID: "a", MatchedQueries: []string{"q1"}}, {VideoID: "b"}}, {{VideoID: "c"}, {VideoID: "a", MatchedQueries: []string{"q2"}}}}, 4)
	if ids := []string{selected[0].VideoID, selected[1].VideoID, selected[2].VideoID}; !reflect.DeepEqual(ids, []string{"a", "c", "b"}) {
		t.Fatalf("selection = %#v", ids)
	}
	if !reflect.DeepEqual(selected[0].MatchedQueries, []string{"q1", "q2"}) {
		t.Fatalf("provenance = %#v", selected[0].MatchedQueries)
	}
}
