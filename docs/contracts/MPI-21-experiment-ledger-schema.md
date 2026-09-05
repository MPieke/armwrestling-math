---
linear_issue: MPI-21
status: proposed
---

# Contract MPI-21: Experiment Ledger Schema

## Scope

**Depends on MPI-19** (match outcome and event schema) and transitively MPI-20
(fresh PostgreSQL instance). Everything below is additive to the same fresh
database.

Add the tables that let competing prediction approaches be compared on an
identical, immutable benchmark, and that give an iterating agent or human a
durable record of what was already tried: `eval_protocols`, `eval_folds`,
`experiment_runs`, `run_predictions`, `run_models`.

This is a pure schema change — migration and `dbgen` regeneration only. No Go
business logic reads or writes these tables; the Go importer's domain is
`matches`/`athletes`/evidence, not experiments. `db/migrations` remains the
single schema authority for the whole database, but a non-Go component
(MPI-22) will read and write this part of it directly.

Out of scope: Elo/Bradley-Terry computation, the rolling-origin runner that
populates these tables (MPI-22), feature engineering, the agent loop.

## Design choices ruled out, and why

Applying the project's maintainability standard before writing the schema
eliminated two tables from an earlier sketch of this design:

- **No `datasets`/`feature_specs` tables with content hashes.** A dataset's
  *shape* varies per experiment, but its *code* lives in the repo and is
  already pinned by `experiment_runs.git_sha`. A separate content-addressing
  layer on top of that would duplicate what git already guarantees. Feature
  specs stay as `jsonb` directly on `experiment_runs`.
- **No stored model artifact.** The candidate model families (Elo,
  Bradley-Terry, logistic regression) are deterministic given `git_sha` +
  input data + `seed`. Storing a serialized model duplicates something
  cheaply recomputable — `run_models.params` (coefficients / feature
  importances) is kept for quick inspection without recomputation, but the
  fitted model object itself is not persisted.
- **No separate lockbox table.** A lockbox is not a different kind of thing
  from a rolling-origin fold — it is a fold whose test set is rarely queried.
  Both are `eval_protocols`/`eval_folds` rows distinguished only by `kind`,
  rather than two parallel mechanisms for the same underlying concept
  (materialized train/test match membership).

## 1. Current-State Architecture

### Current Data Model

```text
events <--- matches <--- match_competitors ---> athletes
                                                    (MPI-19: outcomes exist,
                                                     but nothing records how
                                                     matches group into folds,
                                                     or what was predicted)
```

There is no way to freeze a benchmark, no record of what a candidate approach
was scored against, and no durable list of prior attempts — the "did we
already try this" question defined earlier has no schema to answer it from.

## 2. Target-State Architecture

### Target Data Model

```text
eval_protocols                    eval_folds
+------------------+              +---------------------------+
| id               |<-------------| protocol_id           FK  |
| name           U |              | fold_index                |
| kind             |              | train_match_ids  bigint[] |
| created_at       |              | test_match_ids   bigint[] |
+------------------+              +---------------------------+
                                     PK(protocol_id, fold_index)

experiment_runs
+---------------------+
| id                  |
| git_sha             |
| git_dirty           |
| protocol_id     FK  |----> eval_protocols
| feature_spec  jsonb |
| model_family        |
| hyperparams   jsonb |
| seed                |
| parent_run_id   FK  |----> experiment_runs (self, nullable)
| hypothesis          |
| status              |
| metrics       jsonb |
| error_message       |
| started_at          |
| finished_at         |
+---------------------+
        |                          |
        v                          v
run_predictions              run_models
+------------------+         +------------------+
| run_id        FK |         | run_id    FK  PK |
| match_id      FK |         | params  jsonb    |
| athlete_id    FK |         +------------------+
| p_win  float8    |
+------------------+
  PK(run_id, match_id, athlete_id)
```

`eval_protocols.kind` is one of `rolling_origin`, `lockbox_retrospective`,
`lockbox_prospective`. All three are represented identically as materialized
`train_match_ids`/`test_match_ids` arrays — a `lockbox_*` protocol typically
has a single fold (`fold_index = 0`).

`eval_folds` membership is materialized at creation time, not a query rule
(e.g. "matches after date X"). A rule-based definition would silently change
membership as new matches are ingested, breaking comparability between runs
scored months apart against "the same" protocol. Once a fold row exists, its
match-id arrays are never updated in place — a changed benchmark is a new
protocol, not a mutated one. This is enforced by the accompanying test suite,
not a database trigger.

`experiment_runs.protocol_id` is `NOT NULL`: every run is scored against an
explicit, named protocol, never an ad-hoc query. `git_dirty` records whether
the working tree was clean at run time; a harness that writes `git_dirty =
true` for a `completed` run is a contract violation the tests must catch (a
result whose code wasn't actually committed is not reproducible).

`run_predictions` stores `p_win` per athlete per match rather than picking one
canonical "side," since `match_competitors` has no inherent ordering — this
avoids inventing an arbitrary designation of "athlete A" purely to store a
prediction.

## 3. Test Plan Defined Before Implementation

### PostgreSQL Integration Tests

- apply every migration and assert all five tables, their constraints, and
  foreign keys, including the `eval_folds` composite primary key and
  `experiment_runs.protocol_id NOT NULL`;
- prove `eval_folds.train_match_ids`/`test_match_ids` accept and return
  `bigint[]` correctly, including an empty array (a lockbox protocol may have
  no training matches of its own if it borrows ratings computed elsewhere);
- prove two `experiment_runs` rows can reference the same `protocol_id` and
  each carries independent `feature_spec`/`hyperparams`/`metrics`;
- prove `parent_run_id` self-references correctly and a run can have no
  parent (the first run in a lineage);
- prove `run_predictions` rejects a duplicate `(run_id, match_id, athlete_id)`
  and accepts one row per competitor per match;
- prove deleting an `experiment_run` cascades to its `run_predictions` and
  `run_models` rows but leaves `eval_protocols`/`eval_folds` untouched (a run
  is disposable; a benchmark definition is not);
- prove a `completed` status combined with `error_message` set is never
  produced by the schema's intended write pattern (documented via a test that
  exercises the actual query, not a bare check constraint, since "intended
  write pattern" is an application-level guarantee once MPI-22 exists — this
  contract records the schema-level half: `error_message` is nullable and
  `status` is a checked enum).

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-21): add experiment ledger schema contract`
   - Add this contract and link it from MPI-21.

2. `test(MPI-21): define experiment ledger schema`
   - Add red PostgreSQL tests per the plan above.
   - Expected failure: the tables do not exist.

3. `feat(MPI-21): add experiment ledger schema`
   - Add `db/migrations/0004_experiment_ledger.sql` and regenerate `dbgen`
     (no new `db/queries/*.sql` entries are required, since no Go path reads
     or writes these tables; `dbgen`'s regenerated `models.go` picking up the
     new table structs is the only expected diff).
   - Reviewable alone because it makes commit 2 green.

4. `docs(MPI-21): document the experiment ledger boundary`
   - Update `docs/architecture/ingestion.md` (or add a sibling document if the
     prediction track's architecture doesn't belong in the ingestion doc) to
     record that this part of the schema is written by a non-Go component,
     and why.

## 5. Verification Plan

1. Regenerate sqlc and prove the committed output is current:

   ```sh
   cd services/importer
   go install github.com/sqlc-dev/sqlc/cmd/sqlc@v1.30.0
   "$(go env GOPATH)/bin/sqlc" generate -f sqlc.yaml
   git diff --exit-code -- internal/dbgen
   ```

2. Create a fresh `armwrestling_math_test`, apply migrations `0001` through
   `0004`, and run the tagged suite:

   ```sh
   INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
     go test -v -count=1 -tags integration ./...
   ```

3. Direct SQL inspection proving a protocol, its folds, a run, and its
   predictions round-trip:

   ```sh
   psql "$INGEST_TEST_DATABASE_URL" -c "
     select p.name, p.kind, f.fold_index, array_length(f.test_match_ids, 1)
     from eval_protocols p join eval_folds f on f.protocol_id = p.id
     order by p.name, f.fold_index;"
   ```

4. Validate CI syntax and run the workflow:

   ```sh
   actionlint .github/workflows/generic-ingestion-ci.yml
   ```
