# Ingestion Architecture

## Purpose And Scope

This document defines the reusable PostgreSQL ingestion core in
`services/importer`. It is independent of any particular evidence format,
source provider, or command. A future source adapter owns its input parsing and
normalization; the core owns validation, idempotent persistence, and run audit
records.

The Python scripts and static React application are separate systems. They
continue to use committed JSON evidence files and do not read PostgreSQL.

## System Context

```
+-------------------------+                    +-------------------------+
| Python evidence pipeline|                    | Future source adapter   |
| scripts -> data/app     |                    | provider input -> batch |
+------------+------------+                    +------------+------------+
             |                                              |
             v                                              v
      Static app bundle                         services/importer/internal/ingest
             |                                              |
             v                                              v
        React application                         PostgreSQL evidence store
```

The two paths intentionally coexist. Importing evidence into PostgreSQL does
not change the static application's source of data.

## Importer Components

```
+-----------------------------------------------------------------------+
| services/importer                                                     |
|                                                                       |
| future adapter / command                                              |
|   - parse provider-specific input                                     |
|   - preserve original JSON                                            |
|   - construct IngestBatch                                             |
|                |                                                      |
|                v                                                      |
| internal/ingest                                                       |
|   batch.go       canonical input contract                             |
|   validate.go    reference and invariant checks                       |
|   run.go         transaction, idempotent writes, run audit lifecycle |
|                |                                                      |
|                v                                                      |
| internal/dbgen                                                        |
|   sqlc-generated pgx query package                                    |
+------------------------------|----------------------------------------+
                               v
                           PostgreSQL
```

## Canonical Batch Boundary

An adapter produces one `IngestBatch`:

```text
IngestBatch
  athletes: stable adapter keys + canonical display names
  match: batch-local key + database natural key + competitors
  sources: provider type/external ID + metadata + original payload
  claims: source/match references + optional subjects + evidence fields
```

The adapter may use any provider-specific models internally, but it must not
push those models into `internal/ingest`. This keeps future formats from adding
branches to shared persistence code.

`Validate` runs before a database connection is mutated. It rejects duplicate
keys and unresolved athlete, source, match, or subject references.

## Run Lifecycle

```
adapter             Validate              Run                     PostgreSQL
  |                    |                    |                           |
  |-- IngestBatch ---->|                    |                           |
  |<-- valid/error ----|                    |                           |
  |                    |                    |                           |
  |-- Run(batch) -------------------------->|-- create running run ---->|
  |                    |                    |-- BEGIN ----------------->|
  |                    |                    |-- upsert athletes -------->|
  |                    |                    |-- upsert match + links --->|
  |                    |                    |-- upsert sources --------->|
  |                    |                    |-- upsert claims + links -->|
  |                    |                    |-- complete run ---------->|
  |                    |                    |-- COMMIT ---------------->|
  |<-- run ID/counts -----------------------|                           |

  transaction error: ROLLBACK, then mark the already-created run failed
```

Success is written in the transaction immediately before commit. Failure is a
compensating write after rollback because a rollback cannot retain a failed
status. A connection failure before a run is created cannot be audited in that
database; callers receive the connection error instead.

## Data Model

```
athletes                    matches                       sources
+----------------+          +----------------+            +-------------------------+
| id             |          | id             |            | id                      |
| canonical_name |          | natural_key    |            | source_type/external_id |
+----------------+          | arm            |            | url, title              |
      ^    ^                 | scheduled_at   |            | published_at            |
      |    |                 +----------------+            | raw_payload             |
      |    +-- match_competitors ---^                       +-------------------------+
      |                                                             ^
      +-------- claim_subjects                                       |
                    ^                                                |
                    |                                                |
                  claims -------------------------------- source_id -+
                  +-----------------------+
                  | source_id, match_id   |
                  | claim_text, timestamp |
                  | evidence metadata     |
                  | raw_payload           |
                  +-----------------------+

ingestion_runs: standalone run-level audit records
```

## Durable Decisions

| Decision | Rationale |
|---|---|
| Generic batch, provider-specific adapters | Parsing changes most often; transactional persistence must remain stable and simple. |
| Adapter-owned natural keys | A generic persistence layer cannot infer domain-specific rematch identity safely. |
| PostgreSQL unique constraints and upserts | Idempotency is enforced by the database, not process-local state. |
| Claim dedupe expression | `source_id + coalesced timestamp + claim text` handles claims with no timestamp while retaining a meaningful natural identity. |
| Raw JSON payloads | Preserve provenance and future reprocessing inputs without polluting canonical columns. |
| sqlc-generated pgx package committed to Git | Query signatures are reviewable and consumers do not require sqlc at build time. Change SQL then regenerate; never hand-edit `internal/dbgen`. |
| One transaction for evidence writes | A completed run corresponds to an atomic set of athletes, match links, sources, claims, and subject links. |
| Standalone `ingestion_runs` | Run audit records describe an import attempt; sources and claims are reused across runs and therefore do not have misleading `created_by_run_id` columns. |
| Optional subjects | An adapter records subjects only when it has reliable evidence; it must not default ambiguous claims to every match competitor. |
| Dedicated integration database | Integration tests truncate state and must use `INGEST_TEST_DATABASE_URL` targeting `armwrestling_math_test`, never a primary database. |

## Adding A Source Adapter

1. Create a focused package beneath `services/importer/internal/` for the new
   provider or format. Keep parsing models, normalization rules, and provider
   identifiers there.
2. Transform input into `ingest.IngestBatch`. Give every batch-local reference
   a stable key and compute a domain-appropriate `MatchInput.NaturalKey`.
3. Preserve original source and claim payloads in `RawPayload`.
4. Add adapter tests using representative provider fixtures. Assert meaningful
   output counts, references, and domain invariants rather than parser coverage
   alone.
5. Add a provider command that reads its own input configuration, builds the
   batch, opens a pgx pool, and calls `ingest.Run`.
6. Add a schema migration only when the canonical model needs a new durable
   concept. Do not add provider-specific columns for data that belongs in raw
   payloads.

## Operations And Verification

Apply migrations before running an adapter command:

```sh
docker compose up -d postgres
docker compose exec -T postgres psql -U admin -d armwrestling-math \
  < db/migrations/0001_init.sql
```

Run the normal checks from `services/importer`:

```sh
go vet ./...
go test ./...
```

For the destructive integration test, create and migrate only the dedicated
test database, then run:

```sh
INGEST_TEST_DATABASE_URL='postgres://.../armwrestling_math_test?sslmode=disable' \
  go test -tags integration ./internal/ingest
```

Regenerate query code after changing migration or query SQL:

```sh
sqlc generate -f sqlc.yaml
```
