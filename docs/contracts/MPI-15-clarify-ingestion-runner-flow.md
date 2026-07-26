---
linear_issue: MPI-15
status: approved
---

# Contract MPI-15: Clarify Ingestion Runner Flow

## 1. Current-State Architecture

The ingestion runner uses short variable names for the database connection
pool, ordinary query set, transaction, and transaction-bound query set.
There is no repository-local guidance for choosing descriptive names or adding
comments at non-obvious control-flow boundaries.

```text
Run(ctx, pool, batch)
    |
    +-- queries := dbgen.New(pool)
    |       +-- ordinary queries through the connection pool
    |
    +-- tx := pool.Begin(ctx)
    |       +-- one atomic PostgreSQL transaction
    |
    +-- qtx := queries.WithTx(tx)
            +-- generated queries bound to that transaction
```

## 2. Target-State Architecture

The persistence ownership and transaction boundaries are unchanged. The
hand-written names and comments make them explicit.

```text
Run(ctx, databasePool, batch)
    |
    +-- databaseQueries := dbgen.New(databasePool)
    |       +-- creates and updates standalone run audit records
    |
    +-- transaction := databasePool.Begin(ctx)
    |       +-- atomically persists canonical evidence
    |
    +-- transactionQueries := databaseQueries.WithTx(transaction)
            +-- writes athletes, match, sources, claims, and links
```

```text
AGENTS.md
    +-- descriptive names for hand-written domain roles
    +-- established Go idioms: ctx, err, i, j
    +-- comments for non-obvious ownership and flow decisions
```

## 3. Commit-by-Commit Breakdown

1. `docs(MPI-15): add readability guidance and ingestion contract`
   - Add `AGENTS.md` with repository-wide rules for descriptive hand-written
     names and concise comments at non-obvious boundaries.
   - Add this contract at `docs/contracts/MPI-15-clarify-ingestion-runner-flow.md`.
   - The guidance and approved scope are reviewable independently from code.

2. `refactor(MPI-15): clarify ingestion runner database roles`
   - Update `services/importer/internal/ingest/run.go`.
   - Rename the ambiguous hand-written database-flow variables and add concise
     comments at the connection-pool, transaction, generated-query, rollback,
     and audit boundaries.
   - The SQL, generated code, public API, and persistence behavior remain
     unchanged, so this is reviewable as a behavior-preserving readability
     refactor.

## 4. Verification Plan

Run the standard importer checks:

```sh
cd services/importer
go vet ./...
go test -v -count=1 ./...
```

Review the final diff to verify that it changes only `AGENTS.md`, this contract,
and `services/importer/internal/ingest/run.go`; no SQL, migration, or generated
`internal/dbgen` code may change.
