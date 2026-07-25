---
linear_issue: MPI-14
status: proposed
---

# Contract: Generic Ingestion CI

Add a dedicated CI workflow for the reusable Go ingestion core, PostgreSQL
schema, and sqlc-generated package. The existing Pages workflow and all static
application checks are explicitly out of scope.

## 1. Current-State Architecture

```
+-----------------------+      +-----------------------------+
| GitHub Actions        |      | Local Docker Compose        |
| deploy-pages.yml      |      |                             |
|                       |      | golang:1.24 (unused)        |
| Python + Node +       |      | node:22 (unused)            |
| Pages deployment only |      | postgres:17                 |
+-----------------------+      +-----------------------------+

services/importer and db/
  - no CI coverage
  - Go 1.26 module
  - integration test requires a dedicated database URL
```

Current deployment sequence:

```
push to dev -> deploy-pages -> Python app bundle -> Node checks -> Pages deploy
```

The PostgreSQL schema is unchanged by this ticket:

```
athletes <- match_competitors -> matches <- claims -> sources
   ^                                  ^
   +--------- claim_subjects ---------+
             ingestion_runs
```

## 2. Target-State Architecture

```
pull request or push to main
  (only db/**, services/importer/**, ingestion workflow changes)
                   |
                   v
+-------------------------------------------------------------------+
| generic-ingestion-ci.yml                                          |
|                                                                   |
| checkout -> Go 1.26 -> gofmt -> go vet -> unit tests              |
|                        |                                          |
|                        +-> pinned sqlc generate -> no Git diff    |
|                                                                   |
| PostgreSQL 17 service -> apply migration -> guarded integration   |
+-------------------------------------------------------------------+

push to dev -> deploy-pages.yml -> existing Pages deployment
             (unchanged and independent)
```

The integration job uses only `INGEST_TEST_DATABASE_URL`, targeting the fresh
`armwrestling_math_test` service database. No primary-database connection string
is available to the workflow.

Docker Compose becomes a local PostgreSQL definition only:

```
docker compose
  postgres:17 -> named local volume -> port 5432
```

The unused Go and Node Compose services are removed because CI installs its
declared Go toolchain directly and Pages CI already installs Node directly.

CI sequence:

```
runner                 PostgreSQL service                 Go integration test
  |-- start service ---------->|                                   |
  |-- apply 0001_init.sql ---->|                                   |
  |-- INGEST_TEST_DATABASE_URL ----------------------------------->|
  |                                                           BEGIN |
  |<-- pass/fail ---------------------------------------------------|
```

## 3. Commit-by-Commit Breakdown

1. `docs(MPI-14): add generic ingestion CI contract`
   - Add this contract and link it to MPI-14.
   - Reviewable alone because it changes no runtime behavior.

2. `build(MPI-14): add generic ingestion CI workflow`
   - Add `.github/workflows/generic-ingestion-ci.yml` with path filters,
     Go quality checks, sqlc drift detection, PostgreSQL migration, and the
     guarded integration test.
   - Reviewable alone because it changes only CI behavior.

3. `chore(MPI-14): remove unused Compose language services`
   - Remove the unused Go and Node services from `docker-compose.yaml`, leaving
     the local PostgreSQL dependency untouched.
   - Reviewable alone because it removes unused configuration only.

## 4. Verification Plan

1. `cd services/importer && gofmt -d . && go vet ./... && go test ./...`
2. Install sqlc `v1.30.0`, run `sqlc generate -f services/importer/sqlc.yaml`,
   then `git diff --exit-code -- services/importer/internal/dbgen`.
3. Start PostgreSQL, create and migrate `armwrestling_math_test`, then run:

   ```sh
   INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
     go test -tags integration ./services/importer/internal/ingest
   ```

4. Verify `INGEST_TEST_DATABASE_URL` pointed at `armwrestling-math` causes the
   integration test to fail before opening a destructive transaction.
5. Push the branch and manually dispatch the new workflow; confirm the
   generic-ingestion CI job passes without invoking the Pages deployment job.
