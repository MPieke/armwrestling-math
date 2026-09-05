---
linear_issue: MPI-19
status: proposed
---

# Contract MPI-19: Match Outcome And Event Schema

## Scope

**Depends on MPI-20** (fresh PostgreSQL instance). This contract's migration
applies to that fresh database only, which has zero pre-existing rows. The new
columns described below are `NOT NULL` — no backfill value, no `unknown` enum
member, no legacy-row-preservation logic anywhere in this contract.

Add the canonical facts required to predict match outcomes: an `events` table
that groups matches, per-competitor scores and results, and a match status that
distinguishes a decided contest from a disqualification or a no-contest.

Add the provider-neutral `ResultSubmission` boundary and its transactional
persistence path, so a later results adapter maps provider JSON to a versioned
submission without owning schema or transaction concerns. Because MPI-16's
evidence path never writes to `matches` (it only reads an existing match by
natural key), `ResultSubmission` is the only writer of `matches` after this
contract lands — which is what allows `event_id` and `scheduled_at` to be
`NOT NULL` rather than merely enforced by convention.

Out of scope: the results adapter itself, Elo/Bradley-Terry rating computation,
evaluation protocol and fold tables, the experiment ledger, evidence features,
and athlete deduplication.

Athlete deduplication is deliberately deferred. Variant name spellings will
create separate `athletes` rows. Ratings are a derived, recomputable artifact,
so merging duplicates later requires a refit rather than a data repair.

## 1. Current-State Architecture

### Components

```text
+------------------------- services/importer -------------------------+
|                                                                      |
|  cmd/ingest-youtube                                                  |
|        |                                                             |
|        +--> internal/matchup ------> read existing match context     |
|        +--> internal/research -----> fixed queries, bounded select   |
|        +--> internal/youtube ------> YouTube + Gemini                |
|        |            `-------------> EvidenceSubmission v1            |
|        `--> internal/ingest -------> sqlc queries ------> PostgreSQL |
+----------------------------------------------------------------------+

internal/ingest owns exactly one submission type: EvidenceSubmission.
It may never create or modify matches, athletes, or competitor membership.
There is no path that registers a match or records who won.
```

### Current Data Model

```text
athletes <--- match_competitors ---> matches
   ^              (bare join)           ^
   |          no score, no result       |
claim_subjects ---> claims -------------+
                      |                 |
                      v                 |
              source_extractions -------+
                      |
                      v
                   sources

ingestion_runs records each database submission attempt.
```

```text
match_competitors            matches
+--------------+             +----------------+
| match_id  FK |             | id             |
| athlete_id FK|             | natural_key U  |
+--------------+             | label          |
   PK(match_id,              | arm            |
      athlete_id)            | scheduled_at   |
                             +----------------+
```

`match_competitors` records only that an athlete took part. Nothing records the
score, the winner, whether the match was decided at all, or which event it
belonged to. There is therefore no label to predict and no way to group matches
into the event-based folds the evaluation design requires.

## 2. Target-State Architecture

### Components

```text
+------------------------- services/importer -------------------------+
|                                                                      |
|  cmd/ingest-youtube ------> EvidenceSubmission v1 ---+                |
|                                                      |                |
|  (future) results adapter -> ResultSubmission v1 ----+                |
|                                                      |                |
|                                          internal/ingest              |
|                                            |    Submit()              |
|                                            |    SubmitResult()        |
|                                            v                          |
|                                    sqlc queries --> PostgreSQL        |
+----------------------------------------------------------------------+
```

### Ownership Boundary Change

This contract introduces a second, deliberately different submission type.
The distinction is the point:

```text
EvidenceSubmission   reads canonical identity, never creates it.
                     Requires the match to already exist.

ResultSubmission     OWNS canonical identity. Creates events, athletes,
                     matches, and competitor membership with outcomes.
```

Results are how matches enter the system; evidence attaches to matches that
already exist. Keeping both behind `internal/ingest` preserves the single
transactional writer while making the asymmetry explicit rather than incidental.

### Target Data Model

```text
events <--- matches <--- match_competitors ---> athletes
              ^                                    ^
              |                                    |
claim_subjects ---> claims ---------------------+  |
                      |                            |
                      v                            |
              source_extractions                   |
                      |                            |
                      v                            |
                   sources                         |
                                                   |
claim_subjects -----------------------------------+
```

```text
events                        matches (changed)
+----------------+            +----------------------+
| id             |            | id                   |
| slug         U |<-----------| event_id     FK  NN  |  (new, not null)
| promoter       |            | natural_key      U   |
| name           |            | label                |
| held_on        |            | arm                  |
| created_at     |            | scheduled_at     NN  |  (existing column,
+----------------+            | status           NN  |   nullable -> NOT NULL)
                              +----------------------+  (status is new)

match_competitors (changed)
+------------------+
| match_id      FK |
| athlete_id    FK |
| score            |  (new, nullable, >= 0)
| result           |  (new, nullable, enum)
+------------------+
```

`matches.event_id` is `NOT NULL`. `matches.scheduled_at` is an existing
nullable column; this migration changes it to `NOT NULL` (`alter column ...
set not null`), safe only because MPI-20 guarantees zero existing rows to
violate it. A match with no confirmed date does not exist as a row yet — it is
not created until the date is known. This is a genuine constraint tightening on
an existing column, not just an addition, and is called out explicitly per the
project's Contract Precision rule.

`matches.status` is one of `scheduled`, `completed`, `dq`, `no_contest` — no
`unknown` member exists, because every row is created by `ResultSubmission`
with a real status from the moment it exists. Rating fits select
`status = 'completed'` explicitly, so disqualifications and no-contests are
excluded by intent rather than by an accident of null handling.

`match_competitors.score` and `.result` are nullable: a `scheduled` match
genuinely has no outcome yet, which is a fact, not a gap. `result` is one of
`win`, `loss`, `no_contest` — `draw` is omitted; armwrestling supermatches
(best-of-N sets) do not produce draws, and an unused enum member is exactly
the kind of premature generality the project's abstraction guidance rules out.
Add it later if a rule set that permits draws is actually ingested.

### Validation Layer Split

Cross-row invariants cannot be expressed as PostgreSQL check constraints on a
single row, so the layers divide as follows:

```text
PostgreSQL constraints        single-row facts (NOT NULL and CHECK)
                              - result is a recognized enum value
                              - score is non-negative
                              - status is a recognized enum value
                              - event slug is unique
                              - matches.event_id is not null (FK to events)
                              - matches.scheduled_at is not null
                              - matches.natural_key is unique

Go validation gate            cross-row invariants, before any database work
                              - exactly two competitors per match
                              - a completed match has exactly one 'win'
                              - a completed match has a score for both sides
                              - competitor names are distinct and non-empty
                              - a ResultSubmission carries an event (slug,
                                promoter, name, held_on)
                              - arm and status are recognized values
```

This follows the existing pattern: invalid input is rejected by Go before the
transaction opens, so a rejected submission performs no database work at all.

### Natural Key Convention

`matches.natural_key` remains a free-text unique column; different writers may
use different conventions without conflict, since PostgreSQL only requires
uniqueness, not a specific shape, and MPI-16's `--match-natural-key` flag does
an exact string match against whatever key was stored. `ResultSubmission`
mints keys in its own convention:

```text
<event-slug>:<athlete-a-slug>:<athlete-b-slug>:<arm>[:<sequence>]
```

Two rules make this collision-resistant and deterministic:

- **Athlete slugs are sorted alphabetically** before the key is built,
  regardless of the order competitors appear in provider data. Without this,
  the same match ingested as "A vs B" and "B vs A" would mint two different
  keys for one match.
- **`sequence`** is appended only when the same pair meets on the same arm
  within the same event more than once (a bracket rematch); it is omitted for
  the common single-meeting case rather than always present as `:1`.

This is a convention enforced in the Go validation/construction code, not a
database constraint — `natural_key` stays a plain `text unique` column.

### Target Runtime Sequence

```text
adapter        ingest.SubmitResult          PostgreSQL
   |                    |                        |
   |-- ResultSubmission>|                        |
   |                    |-- ValidateResult       |
   |                    |   (pure, no DB)        |
   |                    |                        |
   |                    |----------------- BEGIN |
   |                    |-- upsert event ------->|
   |                    |-- upsert athletes ---->|
   |                    |-- upsert match ------->|
   |                    |   (event_id, status)   |
   |                    |-- link competitors --->|
   |                    |   (score, result)      |
   |                    |---------------- COMMIT |
   |<-- Result ---------|                        |
```

Validation failure returns before `BEGIN`. A persistence failure rolls the whole
submission back and records a failed `ingestion_runs` row, matching the evidence
path's existing audit behavior.

Replaying the same submission is idempotent: the event, athletes, and match
upsert by their natural identities, and competitor links update score and result
in place rather than duplicating membership.

## 3. Test Plan Defined Before Implementation

Tests are committed before the behavior they specify. Each red commit is run and
its expected failure recorded. The following implementation commit must turn it
green without weakening assertions.

### Unit Tests (pure validation gate)

Table-driven over `ValidateResult`, each case named by the behavior it proves:

- accepts a well-formed completed result with two competitors;
- rejects a completed match without exactly one winner (zero winners, two
  winners);
- rejects a competitor count other than two;
- rejects a negative score;
- rejects an unrecognized arm, status, or result value;
- rejects duplicate or empty competitor names;
- rejects a submission with no event (missing slug, promoter, name, or
  held_on);
- accepts a `no_contest` match with no winner, proving the winner rule applies
  only to completed matches;
- mints an identical natural key regardless of competitor order (`A, B` vs
  `B, A`), proving alphabetical slug sorting;
- appends a sequence suffix only on the second and later meeting of the same
  pair, same arm, same event.

### PostgreSQL Integration Tests

- apply every migration to a fresh database and assert the `events` table, the
  new columns, `NOT NULL` constraints (`event_id`, `scheduled_at`, `status`),
  check constraints, unique constraints, and foreign keys;
- prove MPI-16's evidence path still resolves and reads a match created via
  `ResultSubmission` by natural key, without modifying it;
- persist a completed result and read back per-side scores, reconstructing the
  winner from `result`;
- persist a `no_contest` match and prove it is distinguishable from a completed
  3-0 when filtering on `status`;
- select matches by event, proving the grouping needed for fold construction;
- prove an invalid submission performs no database work (canonical counts
  unchanged, no partial event or athlete rows);
- prove a persistence failure rolls back the entire submission and records a
  failed ingestion run;
- prove replaying an identical submission leaves every canonical relationship
  count stable and updates rather than duplicates competitor rows.

Destructive integration setup continues to reject any database not named
`armwrestling_math_test`.

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-19): add match outcome and event schema contract`
   - Add this contract and link it from MPI-19.
   - Reviewable alone because it changes no executable behavior.

2. `test(MPI-19): define event and outcome schema constraints`
   - Add red PostgreSQL tests for the `events` table, the new match and
     competitor columns, and constraints (including `event_id` and
     `scheduled_at` `NOT NULL`).
   - Expected failure: the tables and columns do not exist.

3. `feat(MPI-19): add event and outcome schema`
   - Add `db/migrations/0003_match_outcomes.sql`, the supporting queries in
     `db/queries/ingestion.sql`, and regenerated `dbgen`.
   - Reviewable alone because it makes commit 2 green with no Go behavior change.

4. `test(MPI-19): define result submission validation`
   - Add red table-driven unit tests for `ValidateResult`.
   - Expected failure: `ResultSubmission` and `ValidateResult` do not exist.

5. `feat(MPI-19): add result submission validation`
   - Add the versioned `ResultSubmission` types and the pure validation gate.
   - Reviewable alone because it makes commit 4 green without touching the
     database.

6. `test(MPI-19): define result persistence and replay`
   - Add red PostgreSQL tests for `SubmitResult`: persistence, event grouping,
     no-database-work-on-invalid-input, rollback with failed run, and replay
     idempotency.
   - Expected failure: `SubmitResult` does not exist.

7. `feat(MPI-19): add result persistence`
   - Implement `SubmitResult` as one transaction over event, athletes, match,
     and competitor outcomes.
   - Reviewable alone because it makes commit 6 green.

8. `docs(MPI-19): document result ingestion boundary`
   - Update `docs/architecture/ingestion.md` with the events/outcome data model
     and the ownership asymmetry between evidence and result submissions.
   - Reviewable alone because it records the implemented architecture.

## 5. Verification Plan

1. Formatting, static analysis, test discovery, and unit tests:

   ```sh
   cd services/importer
   gofmt -l .
   go vet ./...
   go test -list . ./...
   go test -v -count=1 ./...
   ```

2. Regenerate sqlc and prove the committed output is current:

   ```sh
   go install github.com/sqlc-dev/sqlc/cmd/sqlc@v1.30.0
   "$(go env GOPATH)/bin/sqlc" generate -f sqlc.yaml
   git diff --exit-code -- internal/dbgen
   ```

3. Create a fresh `armwrestling_math_test`, apply migrations `0001` through
   `0003` in lexical order, and run the tagged suites:

   ```sh
   INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
     go test -v -count=1 -tags integration ./...
   ```

   Assertions must prove:

   - `event_id` and `scheduled_at` reject a null value at the database level;
   - MPI-16 evidence ingestion resolves and reads a `ResultSubmission`-created
     match unchanged;
   - per-side scores round-trip and reconstruct the winner;
   - a `no_contest` match is distinguishable from a completed 3-0;
   - matches are selectable by event;
   - natural keys are order-independent and rematches get a sequence suffix;
   - invalid submissions perform no database work;
   - a failed submission rolls back fully and records a failed ingestion run;
   - replay leaves canonical counts stable.

4. Prove the database-name guard still refuses any target not named
   `armwrestling_math_test` before destructive setup.

5. Direct SQL inspection of a seeded completed match, verifying the event row,
   match status, and both competitor score/result rows:

   ```sh
   psql "$INGEST_TEST_DATABASE_URL" -c "
     select e.slug, m.natural_key, m.status,
            a.canonical_name, mc.score, mc.result
     from matches m
     join events e on e.id = m.event_id
     join match_competitors mc on mc.match_id = m.id
     join athletes a on a.id = mc.athlete_id
     order by a.canonical_name;"
   ```

6. Validate CI syntax and run the workflow, inspecting verbose migration,
   generated-code, unit, and integration logs:

   ```sh
   actionlint .github/workflows/generic-ingestion-ci.yml
   ```
