---
linear_issue: MPI-16
status: approved
---

# Contract MPI-16: Environment-Aware Ingestion Configuration

## Scope

Make the Go YouTube ingestion command ready for local development, CI,
staging, and production without putting dotenv loading or environment
selection into the binary. Local development gets an explicit wrapper that
loads the ignored repository `.env`; every deployed environment injects the
same variables through its native configuration and secret mechanisms.

The application validates its received configuration and connects to the
database named by `DATABASE_URL`. Database migrations remain a separate,
ordered deployment operation.

## 1. Current-state architecture

```text
Operator shell / CI
        |
        | exported variables only
        v
cmd/ingest-youtube
        |
        | os.Getenv + inline required checks
        +--> YouTube client
        +--> Gemini client
        `--> PostgreSQL at DATABASE_URL
```

There is no shared configuration type, no committed environment template, and
no documented local wrapper. The Go binary does not read `.env`.

## 2. Target-state architecture

```text
Local wrapper --------------------+
  source ignored .env              |
                                   v
CI / staging / production ------> process environment
                                   |
                                   v
                         internal/config.Load
                         validate required values
                         apply safe optional defaults
                                   |
                                   v
                         cmd/ingest-youtube
                            |      |      |
                            v      v      v
                        YouTube Gemini PostgreSQL
```

The wrapper is the only dotenv-aware component. The binary receives ordinary
environment variables in every environment and never selects a database from
an environment name.

Required variables:

```text
DATABASE_URL
YOUTUBE_API_KEY
GEMINI_API_KEY
GEMINI_MODEL
```

Optional variables retain the existing provider defaults:

```text
YOUTUBE_API_BASE_URL
GEMINI_API_BASE_URL
```

## 3. Commit-by-commit breakdown

1. `test(MPI-16): define ingestion configuration behavior`
   - Add unit tests for required values, optional defaults, and explicit
     configuration loading behavior.
   - Establishes the observable configuration contract before implementation.

2. `feat(MPI-16): centralize ingestion configuration`
   - Add the configuration package and update the command to use it.
   - Keep dotenv loading outside the binary.
   - Add an explicit local wrapper that sources `.env` and executes the Go
     command without changing CI or production invocation.

3. `docs(MPI-16): document environment and migration operations`
   - Add `.env.example` with placeholders only.
   - Document local, CI, staging, and production configuration plus the
     separate migration step and canonical database ownership.

## 4. Verification plan

Run from `services/importer`:

```sh
go test -v -count=1 ./...
go vet ./...
test -z "$(gofmt -l .)"
```

Verify the local wrapper without printing secrets:

```sh
./scripts/run-ingest-youtube.sh --help
```

Verify the binary remains environment-only in a clean process:

```sh
env -i PATH="$PATH" HOME="$HOME" \
  DATABASE_URL='postgres://example' \
  YOUTUBE_API_KEY='example' \
  GEMINI_API_KEY='example' \
  GEMINI_MODEL='explicit-model-id' \
  go run ./cmd/ingest-youtube --help
```

Verify the canonical database after migrations:

```sh
psql "$DATABASE_URL" -c '\dt'
psql "$DATABASE_URL" -c 'select count(*) from source_extractions;'
```

Run the existing fresh-database integration workflow, including ordered
migrations, verbose tagged tests, sqlc generation, and CI workflow checks.
