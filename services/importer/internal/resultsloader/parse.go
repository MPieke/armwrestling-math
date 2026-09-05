// Package resultsloader turns a hand-copied result CSV into validated,
// database-independent result submissions. It intentionally performs no I/O
// other than reading its supplied CSV stream.
package resultsloader

import (
	"encoding/csv"
	"fmt"
	"io"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/mpieke/armwrestling-math/services/importer/internal/ingest"
)

var expectedHeader = []string{
	"event_slug", "event_name", "promoter", "event_date", "arm", "weight_class",
	"athlete_a", "athlete_b", "score_a", "score_b", "status", "video_id", "bout",
}

type parsedRow struct {
	rowNumber  int
	bout       int
	submission ingest.ResultSubmission
}

// Parse validates every CSV row before returning any submission. The source
// name is retained as the ingestion batch key so a persisted result can be
// traced to the file that supplied it.
func Parse(reader io.Reader, sourceName string) ([]ingest.ResultSubmission, error) {
	csvReader := csv.NewReader(reader)
	header, err := csvReader.Read()
	if err != nil {
		return nil, fmt.Errorf("read CSV header: %w", err)
	}
	if !sameHeader(header, expectedHeader) {
		return nil, fmt.Errorf("invalid CSV header: want %s", strings.Join(expectedHeader, ","))
	}

	rows, problems := readRows(csvReader, sourceName)
	problems = append(problems, validateBouts(rows)...)
	if len(problems) > 0 {
		sort.Strings(problems)
		return nil, fmt.Errorf("invalid result CSV: %s", strings.Join(problems, "; "))
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].rowNumber < rows[j].rowNumber })
	submissions := make([]ingest.ResultSubmission, len(rows))
	for index, row := range rows {
		submissions[index] = row.submission
	}
	return submissions, nil
}

func sameHeader(got, want []string) bool {
	if len(got) != len(want) {
		return false
	}
	for index := range want {
		if got[index] != want[index] {
			return false
		}
	}
	return true
}

func readRows(reader *csv.Reader, sourceName string) ([]parsedRow, []string) {
	var rows []parsedRow
	var problems []string
	for rowNumber := 2; ; rowNumber++ {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			problems = append(problems, fmt.Sprintf("row %d: read CSV: %v", rowNumber, err))
			continue
		}
		row, rowProblems := parseRow(record, rowNumber, sourceName)
		problems = append(problems, rowProblems...)
		if len(rowProblems) == 0 {
			rows = append(rows, row)
		}
	}
	return rows, problems
}

func parseRow(record []string, rowNumber int, sourceName string) (parsedRow, []string) {
	if len(record) != len(expectedHeader) {
		return parsedRow{}, []string{fmt.Sprintf("row %d: want %d columns, got %d", rowNumber, len(expectedHeader), len(record))}
	}
	for index := range record {
		record[index] = strings.TrimSpace(record[index])
	}
	problems := requiredProblems(record, rowNumber)
	eventDate, err := time.Parse("2006-01-02", record[3])
	if err != nil {
		problems = append(problems, fmt.Sprintf("row %d: invalid event_date", rowNumber))
	}
	bout, boutProblem := parseBout(record[12], rowNumber)
	if boutProblem != "" {
		problems = append(problems, boutProblem)
	}
	competitors, scoreProblems := parseCompetitors(record, rowNumber)
	problems = append(problems, scoreProblems...)
	statusProblems := validateRowStatus(record[4], record[10], competitors, rowNumber)
	problems = append(problems, statusProblems...)
	if len(problems) > 0 {
		return parsedRow{}, problems
	}

	videoIDs := []string(nil)
	if record[11] != "" {
		videoIDs = []string{record[11]}
	}
	return parsedRow{
		rowNumber: rowNumber,
		bout:      bout,
		submission: ingest.ResultSubmission{
			SchemaVersion: ingest.ResultSubmissionSchemaVersion,
			BatchKey:      "manual-results:" + sourceName,
			Event:         ingest.EventInput{Slug: record[0], Name: record[1], Promoter: record[2], HeldOn: eventDate},
			Arm:           record[4],
			WeightClass:   record[5],
			ScheduledAt:   eventDate,
			Status:        record[10],
			VideoIDs:      videoIDs,
			Competitors:   competitors,
		},
	}, nil
}

func requiredProblems(record []string, rowNumber int) []string {
	fields := []struct {
		index int
		name  string
	}{
		{0, "event_slug"}, {1, "event_name"}, {2, "promoter"}, {3, "event_date"},
		{4, "arm"}, {5, "weight_class"}, {6, "athlete_a"}, {7, "athlete_b"}, {10, "status"},
	}
	var problems []string
	for _, field := range fields {
		if record[field.index] == "" {
			problems = append(problems, fmt.Sprintf("row %d: missing %s", rowNumber, field.name))
		}
	}
	return problems
}

func parseBout(value string, rowNumber int) (int, string) {
	if value == "" {
		return 0, ""
	}
	bout, err := strconv.Atoi(value)
	if err != nil || bout < 1 || bout > 1439 {
		return 0, fmt.Sprintf("row %d: bout must be a minute from 1 through 1439", rowNumber)
	}
	return bout, ""
}

func parseCompetitors(record []string, rowNumber int) ([]ingest.CompetitorResultInput, []string) {
	scoreA, problemA := parseScore(record[8], rowNumber, "score_a")
	scoreB, problemB := parseScore(record[9], rowNumber, "score_b")
	problems := append(problemA, problemB...)
	if len(problems) > 0 {
		return nil, problems
	}
	competitors := []ingest.CompetitorResultInput{
		{AthleteName: record[6], Score: scoreA},
		{AthleteName: record[7], Score: scoreB},
	}
	if record[10] == "completed" && scoreA != nil && scoreB != nil {
		switch {
		case *scoreA > *scoreB:
			competitors[0].Result, competitors[1].Result = "win", "loss"
		case *scoreB > *scoreA:
			competitors[0].Result, competitors[1].Result = "loss", "win"
		}
	}
	if record[10] == "no_contest" {
		competitors[0].Result, competitors[1].Result = "no_contest", "no_contest"
	}
	return competitors, nil
}

func parseScore(value string, rowNumber int, field string) (*int, []string) {
	if value == "" {
		return nil, nil
	}
	score, err := strconv.Atoi(value)
	if err != nil {
		return nil, []string{fmt.Sprintf("row %d: non-numeric score in %s", rowNumber, field)}
	}
	return &score, nil
}

func validateRowStatus(arm, status string, competitors []ingest.CompetitorResultInput, rowNumber int) []string {
	var problems []string
	if arm != "left" && arm != "right" {
		problems = append(problems, fmt.Sprintf("row %d: unrecognized arm %q", rowNumber, arm))
	}
	if status != "completed" && status != "no_contest" && status != "dq" {
		problems = append(problems, fmt.Sprintf("row %d: unrecognized status %q", rowNumber, status))
	}
	if status == "completed" && (len(competitors) != 2 || competitors[0].Score == nil || competitors[1].Score == nil || competitors[0].Result == "") {
		problems = append(problems, fmt.Sprintf("row %d: completed match requires unequal numeric scores", rowNumber))
	}
	return problems
}

func validateBouts(rows []parsedRow) []string {
	groups := make(map[string][]int)
	for index, row := range rows {
		groups[boutGroupKey(row.submission)] = append(groups[boutGroupKey(row.submission)], index)
	}
	var problems []string
	for _, group := range groups {
		if len(group) < 2 {
			continue
		}
		rowNumbers := make([]string, len(group))
		seenBouts := make(map[int]bool, len(group))
		valid := true
		for position, rowIndex := range group {
			row := &rows[rowIndex]
			rowNumbers[position] = strconv.Itoa(row.rowNumber)
			if row.bout == 0 || seenBouts[row.bout] {
				valid = false
			}
			seenBouts[row.bout] = true
			if row.bout != 0 {
				row.submission.ScheduledAt = row.submission.ScheduledAt.Add(time.Duration(row.bout) * time.Minute)
			}
		}
		if !valid {
			sort.Strings(rowNumbers)
			problems = append(problems, fmt.Sprintf("rows %s: repeated same-day match requires distinct bout values", strings.Join(rowNumbers, ", ")))
		}
	}
	return problems
}

func boutGroupKey(submission ingest.ResultSubmission) string {
	names := []string{strings.ToLower(submission.Competitors[0].AthleteName), strings.ToLower(submission.Competitors[1].AthleteName)}
	sort.Strings(names)
	return strings.Join([]string{submission.Event.Slug, submission.Arm, strings.Join(names, ":"), submission.Event.HeldOn.Format("2006-01-02")}, "|")
}
