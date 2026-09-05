package resultsloader

import (
	"strings"
	"testing"
	"time"
)

const csvHeader = "event_slug,event_name,promoter,event_date,arm,weight_class,athlete_a,athlete_b,score_a,score_b,status,video_id,bout\n"

func TestParseBuildsResultSubmission(t *testing.T) {
	parsed, err := Parse(strings.NewReader(csvHeader +
		"evw-25,East vs West 25,Core Sports,2026-08-01,right,105 kg,Adam Wawrzynski,Nurdaulet Aidarkhan,3,2,completed,video-1,\n"), "fixture.csv")
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if len(parsed) != 1 {
		t.Fatalf("len(parsed) = %d, want 1", len(parsed))
	}
	got := parsed[0]
	if got.Event.Slug != "evw-25" || got.WeightClass != "105 kg" || got.VideoIDs[0] != "video-1" {
		t.Errorf("submission = %+v, want event, weight class, and video preserved", got)
	}
	if !got.ScheduledAt.Equal(time.Date(2026, time.August, 1, 0, 0, 0, 0, time.UTC)) {
		t.Errorf("scheduledAt = %s, want event date", got.ScheduledAt)
	}
}

func TestParseReportsAllMalformedRows(t *testing.T) {
	_, err := Parse(strings.NewReader(csvHeader +
		"evw-25,East vs West 25,Core Sports,2026-08-01,wrong,105 kg,A,B,three,2,completed,,\n"+
		"evw-26,East vs West 26,Core Sports,2026-08-02,right,,C,D,,,cancelled,,\n"), "fixture.csv")
	if err == nil {
		t.Fatal("Parse() succeeded, want row errors")
	}
	for _, want := range []string{"row 2", "row 3", "non-numeric score", "unrecognized arm", "weight_class", "unrecognized status"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("Parse() error = %q, want %q", err, want)
		}
	}
}

func TestParseRejectsUndisambiguatedSameDayRematches(t *testing.T) {
	_, err := Parse(strings.NewReader(csvHeader +
		"evw-25,East vs West 25,Core Sports,2026-08-01,right,105 kg,A,B,3,2,completed,,\n"+
		"evw-25,East vs West 25,Core Sports,2026-08-01,right,105 kg,B,A,3,1,completed,,\n"), "fixture.csv")
	if err == nil || !strings.Contains(err.Error(), "rows 2, 3") || !strings.Contains(err.Error(), "bout") {
		t.Fatalf("Parse() error = %v, want duplicated rows and bout requirement", err)
	}
}

func TestParseUsesDistinctBoutMinutesForSameDayRematches(t *testing.T) {
	parsed, err := Parse(strings.NewReader(csvHeader +
		"evw-25,East vs West 25,Core Sports,2026-08-01,right,105 kg,A,B,3,2,completed,,1\n"+
		"evw-25,East vs West 25,Core Sports,2026-08-01,right,105 kg,B,A,3,1,completed,,2\n"), "fixture.csv")
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if len(parsed) != 2 || !parsed[0].ScheduledAt.Before(parsed[1].ScheduledAt) {
		t.Fatalf("scheduled times = %v, %v, want two ordered timestamps", parsed[0].ScheduledAt, parsed[1].ScheduledAt)
	}
}
