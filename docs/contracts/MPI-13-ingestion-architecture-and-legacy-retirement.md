---
linear_issue: MPI-13
status: approved
---

# Contract MPI-13: Document Generic Ingestion Architecture And Retire Legacy Backfill

## 1. Current-State Architecture

The static frontend still uses the existing Python evidence pipeline. The Go
legacy backfill has completed and is an isolated consumer of the same JSON.

```
+--------------------+       +--------------------------+       +------------+
| Python scripts     |-----> | data/app/*evidence*.json |-----> | React app  |
| (active, unchanged)|       | (active, unchanged)      |       | (unchanged)|
+--------------------+       +--------------------------+       +------------+
                                        |
                                        v
+--------------------------------------------------------------------------+
| services/importer                                                        |
| cmd/import-legacy -> internal/legacy -> internal/ingest -> dbgen/sqlc   |
+--------------------------------------------------------------------------+
                                        |
                                        v
                                 PostgreSQL
```

```
legacy adapter -> IngestBatch -> Validate -> Run transaction -> PostgreSQL
                                            |                   |
                                            |                   +-- sources/claims
                                            +-- abort on bad references
```

```
athletes <- match_competitors -> matches <- claims -> sources
   ^                                  ^
   +--------- claim_subjects ---------+
             ingestion_runs (standalone audit records)
```

## 2. Target-State Architecture

The generic ingestion core remains. The completed legacy adapter and command
are removed. A durable architecture document explains how a future adapter
constructs and submits a canonical batch.

```
+--------------------+       +--------------------------+       +------------+
| Python scripts     |-----> | data/app/*evidence*.json |-----> | React app  |
| (active, unchanged)|       | (active, unchanged)      |       | (unchanged)|
+--------------------+       +--------------------------+       +------------+

future adapter/command -> internal/ingest -> dbgen/sqlc -> PostgreSQL
                          ^
                          |
                    docs/architecture/ingestion.md
```

```
future adapter -> IngestBatch -> Validate -> Run transaction -> PostgreSQL
                                  |             |
                                  |             +-- completed/failed run audit
                                  +-- no database work on invalid references
```

The schema and ER relationships are unchanged.

## 3. Commit Breakdown

1. `docs: add ingestion architecture and retirement contract`
   - Add this contract with the MPI-13 reference.
   - Reviewable alone because it changes no runtime behavior.

2. `docs: document generic ingestion architecture`
   - Add `docs/architecture/ingestion.md` with C4/component/sequence/ER
     diagrams, durable decisions, operations, and a future-adapter recipe.
   - Reviewable alone because it changes no runtime behavior.

3. `cleanup: retire completed legacy backfill adapter`
   - Remove `cmd/import-legacy` and `internal/legacy`, while retaining the
     generic ingestion core, SQL, migrations, and integration tests.
   - Reviewable alone because it removes only the one-off completed backfill.

## 4. Verification Plan

1. `cd services/importer && go vet ./... && go test ./...`
2. Create a dedicated `armwrestling_math_test` database, apply
   `db/migrations/0001_init.sql`, then run:
   `INGEST_TEST_DATABASE_URL='...' go test -tags integration ./internal/ingest`.
3. `rg -n 'internal/legacy|import-legacy|LEGACY_EVIDENCE_PATHS' services/importer`
   returns no matches.
4. `python3 scripts/build_app_bundle.py` succeeds, proving that the unchanged
   Python/static-app evidence pipeline still works.
