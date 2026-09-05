---
linear_issue: MPI-23
status: proposed
---

# Contract MPI-23: Manual Results Loader

## Scope

A CSV-driven command that turns hand-copied competition results into
`ResultSubmission`s. Extends the schema with `weight_class` (every source
has it; not capturing it now means re-copying every row later) and
`match_videos` (ArmSport lists a video per match; capturing the ID now
saves a future evidence-discovery search).

Out of scope: any automated fetch (`docs/discovery/armsport_api_feasibility.md`
is the reference once the data-use reply arrives), athlete deduplication.

## 1. Current-State Architecture

```text
CSV file (hand-copied)          ResultSubmission / SubmitResult (MPI-19)
   |                                        ^
   `---- nothing connects these ------------'

matches            has no weight_class
(no video table)   ArmSport's video_id has nowhere to go
```

`resolveNaturalKey` (MPI-19) disambiguates a genuine rematch from a replay
by comparing `scheduled_at`. A CSV only carries an event *date* — two
distinct bouts on the same day, same pair, same arm would collide.

## 2. Target-State Architecture

### Schema

```text
matches (changed)              match_videos (new)
+----------------------+       +------------------------+
| ...                  |       | match_id  FK           |
| weight_class    NN   |  new  | youtube_video_id       |
+----------------------+       +------------------------+
                                 PK(match_id, youtube_video_id)
```

`weight_class text not null` — safe as `NOT NULL` with no backfill: no
matches exist yet in the fresh instance (this ticket loads the first ones).

### CSV Format

```text
event_slug,event_name,promoter,event_date,arm,weight_class,athlete_a,
athlete_b,score_a,score_b,status,video_id,bout
```

`status` one of `completed`/`no_contest`/`dq`; `score_a`/`score_b` blank
unless `completed`. `video_id` and `bout` optional.

### Bout Disambiguation

The pure parse stage groups rows by `(event_slug, arm, sorted(athlete_a,
athlete_b), event_date)`. A group with more than one row and no `bout`
values is a parse-time error — the loader never guesses. A group with
distinct `bout` values maps to distinct `scheduled_at` timestamps
(`event_date` + `bout` minutes), which makes `resolveNaturalKey` treat them
as genuinely different matches rather than a replay.

### Components

```text
cmd/load-results
   | 1. read CSV, parse every row (pure)
   | 2. group + validate bout disambiguation (pure)
   | 3. any parse error -> print all errors, exit nonzero, NO db work
   | 4. else: for each row, ingest.SubmitResult (sequential)
   | 5. print per-row outcome; exit nonzero if any row failed at the DB
```

Mirrors `cmd/ingest-youtube`'s split: a pure validation/construction stage
before any external call, per-item isolation after.

## 3. Test Plan Defined Before Implementation

### Unit (pure CSV parsing, no database)

- parses a well-formed row into a `ResultSubmission`
- rejects a non-numeric score, an unrecognized status/arm, a missing
  required field — each names the row number
- two rows with identical (event, arm, pair, date) and no `bout` is a
  parse-time error naming both row numbers
- the same two rows with distinct `bout` values parse into two
  `ResultSubmission`s with distinct `ScheduledAt`

### PostgreSQL Integration Tests

- assert `matches.weight_class NOT NULL` and the `match_videos` table/PK
- loading a fixture CSV creates the expected events/matches/competitors/
  weight_class/match_videos rows
- loading the same file twice leaves every canonical count unchanged
  (replay idempotency, inherited from `SubmitResult`)
- a file with one malformed row performs zero database work
- `v_completed_matches` exposes `weight_class`

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-23): add manual results loader contract`
2. `test(MPI-23): define weight_class and match_videos schema` — red
3. `feat(MPI-23): add weight_class and match_videos schema` — migration,
   `results.sql` queries, `dbgen`, `ResultSubmission.WeightClass`/
   `VideoIDs`, `v_completed_matches` updated
4. `test(MPI-23): define CSV parsing and bout disambiguation` — red
5. `feat(MPI-23): add CSV parsing and bout disambiguation` — pure
6. `test(MPI-23): define load-results persistence` — red integration test
7. `feat(MPI-23): add load-results command`
8. `docs(MPI-23): document the loader` — `docs/architecture/ingestion.md`

## 5. Verification Plan

```sh
cd services/importer
gofmt -l . && go vet ./... && go test -v -count=1 ./...
sqlc generate -f sqlc.yaml && git diff --exit-code -- internal/dbgen
INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  go test -v -count=1 -tags integration ./...

go run ./cmd/load-results --file testdata/sample_results.csv
psql "$DATABASE_URL" -c "select slug, weight_class from matches m join events e on e.id=m.event_id;"
go run ./cmd/load-results --file testdata/sample_results.csv   # replay: counts unchanged
```
