---
linear_issue: MPI-14
status: approved
---

# Contract MPI-14: Generic Ingestion Test Expansion

Strengthen the generic ingestion core's tests and make CI enumerate the tests
it discovers. This contract changes tests, CI observability, and architecture
documentation only. It does not introduce a source adapter, CLI, HTTP API,
schema migration, or production behavior change.

## 1. Current-State Architecture

### Components

```text
+--------------------------------------------------------------------+
| services/importer                                                  |
|                                                                    |
| internal/ingest                                                    |
|   Validate(batch)                                                  |
|     - validates required fields and batch-local references         |
|     - one unit test: unresolved claim source                       |
|                                                                    |
|   Run(ctx, pool, batch)                                            |
|     - invokes Validate before database work                        |
|     - writes canonical evidence transactionally                    |
|     - one PostgreSQL integration test                              |
|                                                                    |
| internal/dbgen                                                     |
|   - sqlc-generated pgx queries; no direct tests                    |
+-------------------------------+------------------------------------+
                                |
                                v
                     PostgreSQL 17 test service
                     - applies 0001_init.sql
                     - armwrestling_math_test only
```

### Current Test And CI Flow

```text
quality job
  gofmt -> go vet -> go test -v ./... -> sqlc generate + Git diff
                          |
                          +-> one in-memory validation test

integration job
  PostgreSQL -> migrate -> go test -v -tags integration ./internal/ingest
                                      |
                                      +-> one test: replay and malformed JSON
```

The current integration test sends a complete fixture through `Run()` into a
fresh, migrated PostgreSQL database. It proves source and claim idempotency,
completed-run auditing, malformed-JSON failure, and failed-run auditing. It
does not assert the complete persisted relationship graph or all canonical
row counts. CI output does not list discovered tests before running them.

### Current Ingestion Sequence

```text
test fixture       Validate             Run                  PostgreSQL
     |                |                   |                       |
     |-- batch ------>|                   |                       |
     |                |-- valid -------->|                       |
     |                |                   |-- create run ------->|
     |                |                   |-- BEGIN ------------>|
     |                |                   |-- upserts + links --->|
     |                |                   |-- complete + COMMIT ->|
     |<-- assertions from SQL queries ----|-----------------------|

invalid batch: Validate returns before Run can use the pool
persistence error: transaction rolls back, then the run is marked failed
```

## 2. Target-State Architecture

### Components

```text
+--------------------------------------------------------------------+
| services/importer                                                  |
|                                                                    |
| internal/ingest                                                    |
|   validation unit suite                                            |
|     - valid batch accepted                                         |
|     - representative structural and reference failures             |
|     - Run rejects invalid input before pool access                 |
|                                                                    |
|   PostgreSQL integration suite                                     |
|     - exact canonical graph and persisted values                   |
|     - idempotent replay and audit records                          |
|     - persistence rollback and failed-run record                   |
|                                                                    |
| internal/dbgen                                                     |
|   - remains generated; exercised through real PostgreSQL queries   |
+-------------------------------+------------------------------------+
                                |
                                v
                     PostgreSQL 17 test service
                     - fresh migration
                     - dedicated destructive test database
```

### Target Test And CI Flow

```text
quality job
  discover unit tests -> gofmt -> go vet -> go test -v -count=1 ./...
                                                |
                                                +-> validation behavior suite
  sqlc generate -> fail with generated-code diff when output is stale

integration job
  verify dedicated DB -> migrate -> list integration tests
    -> go test -v -count=1 -tags integration ./internal/ingest
       |
       +-> complete graph + idempotent replay
       +-> persistence rollback + failed-run audit
```

### Target Failure Boundaries

```text
invalid structural/reference batch
  -> Validate rejects it
  -> Run returns before accessing PostgreSQL

valid batch, persistence error
  -> ingestion transaction rolls back all canonical tables
  -> separate failed ingestion_runs record is written
```

The test suite will use no mocks for PostgreSQL behavior. Unit tests will
exercise only deterministic Go validation rules; integration tests will use a
real migrated PostgreSQL service for transactions, JSONB serialization,
constraints, generated queries, and audit persistence.

## 3. Commit-by-Commit Breakdown

1. `docs(MPI-14): add ingestion test expansion contract`
   - Add this contract at `docs/contracts/generic-ingestion-test-expansion.md`.
   - Add a Linear comment linking MPI-14 to the contract path.
   - Reviewable alone because it changes no executable behavior.

2. `docs(MPI-14): document ingestion verification strategy`
   - Update `docs/architecture/ingestion.md` with the test-layer ownership,
     database-safety boundary, and CI test-discovery behavior introduced here.
   - Reviewable alone because it documents the intended verification contract
     before the tests enforce it.

3. `test(MPI-14): expand ingestion validation coverage`
   - Replace the single narrow validation case in
     `services/importer/internal/ingest/validate_test.go` with named,
     table-driven cases for a valid batch and representative equivalence
     classes: required fields, duplicate local keys, and unresolved local
     athlete/source/match/subject references.
   - Add a focused `Run()` test that passes an invalid batch with a nil pool,
     proving validation returns before any database access is attempted.
   - Keep fixtures in test-only code and assert exact expected errors or
     stable error fragments for each rule.
   - Reviewable alone because it changes only in-memory test coverage.

4. `test(MPI-14): verify ingestion persistence invariants`
   - Restructure `services/importer/internal/ingest/run_integration_test.go`
     into focused integration tests and test helpers.
   - Assert the full persisted fixture graph: athlete, match, competitor,
     source, claim, and claim-subject counts and relevant persisted values.
   - Replay the fixture and assert canonical relationship counts remain stable
     while completed run audits increase as designed.
   - Retain and strengthen malformed-JSON coverage: assert every canonical
     relation remains unchanged after rollback and exactly one failed run has
     an error message.
   - Keep the explicit `armwrestling_math_test` guard before destructive setup.
   - Reviewable alone because it exercises the existing public `Run()` contract
     against real PostgreSQL without modifying production code or schema.

5. `build(MPI-14): expose ingestion test discovery in CI`
   - Update `.github/workflows/generic-ingestion-ci.yml` to list discovered
     unit and tagged integration tests before executing them.
   - Run Go tests with `-v -count=1` so output names each test and cannot be
     satisfied by a cached prior result.
   - Preserve existing formatting, vet, sqlc-drift, database verification, and
     migration checks.
   - Reviewable alone because it changes only CI observability and test-cache
     behavior.

## 4. Verification Plan

Run from `services/importer` unless a command states otherwise.

1. Confirm discovery is explicit:

   ```sh
   go test -list . ./...
   go test -tags integration -list . ./internal/ingest
   ```

   Expected: named validation tests appear in the first command; named
   PostgreSQL tests appear in the second. `internal/dbgen` remains explicitly
   reported as generated code with no direct hand-written tests.

2. Verify the deterministic Go gate with fresh execution:

   ```sh
   gofmt -w internal/ingest/*_test.go
   go vet ./...
   go test -v -count=1 ./...
   ```

   Expected: every structural/reference validation case passes, and the
   invalid `Run()` case proves no pool access is needed to reject the batch.

3. Verify generated query code remains reproducible:

   ```sh
   go install github.com/sqlc-dev/sqlc/cmd/sqlc@v1.30.0
   "$(go env GOPATH)/bin/sqlc" generate -f sqlc.yaml
   git diff --exit-code -- internal/dbgen
   ```

4. Verify the full PostgreSQL flow from an empty dedicated database:

   ```sh
   docker compose up -d postgres
   PGPASSWORD=admin psql -h 127.0.0.1 -U admin -d postgres \
     -c 'drop database if exists armwrestling_math_test;'
   PGPASSWORD=admin psql -h 127.0.0.1 -U admin -d postgres \
     -c 'create database armwrestling_math_test;'
   PGPASSWORD=admin psql -h 127.0.0.1 -U admin -d armwrestling_math_test \
     -v ON_ERROR_STOP=1 -f ../../db/migrations/0001_init.sql
   INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
     go test -v -count=1 -tags integration ./internal/ingest
   ```

   Expected: exact persisted graph assertions pass; replay is idempotent for
   canonical rows; malformed JSON leaves canonical rows unchanged and produces
   one failed audit row.

5. Verify destructive-test safety:

   ```sh
   INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling-math?sslmode=disable' \
     go test -v -count=1 -tags integration ./internal/ingest
   ```

   Expected: the test fails before truncating or otherwise modifying the
   primary database.

6. Validate the workflow itself:

   ```sh
   actionlint .github/workflows/generic-ingestion-ci.yml
   ```

   After pushing the branch, inspect the GitHub Actions job logs. Expected:
   each job prints its discovered test names, test purpose, database target,
   migration evidence, and the verbose assertions from the integration suite.
