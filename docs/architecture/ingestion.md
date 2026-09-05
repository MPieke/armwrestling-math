# Ingestion Architecture

## Purpose And Scope

`services/importer` contains a provider-independent PostgreSQL evidence core
and source-specific adapters. Match, athlete, and competitor identity is
created by result submissions (MPI-19) and read-only for evidence adapters:
an evidence adapter may read an existing match's competitors but cannot
create or modify match, athlete, or competitor-membership rows. See
"Result And Evidence Ownership" under Data Model for why the two submission
types are asymmetric.

The static React application and historical Python evidence scripts remain
separate. They do not read PostgreSQL.

## Components

```text
cmd/ingest-youtube (sequential coordinator)
        |
        +--> internal/matchup ------> read existing match context
        |
        +--> internal/research -----> fixed queries + bounded selection
        |
        +--> internal/youtube ------> YouTube metadata
        +--> internal/transcript ---> temporary audio + OpenAI transcript/claims
        |           |
        |           `--------------> EvidenceSubmission v1
        |
        `--> internal/ingest -------> sqlc queries -------> PostgreSQL
```

`internal/youtube` has no PostgreSQL, pgx, or generated-query dependency.
`EvidenceSubmission` is a versioned JSON-serializable boundary containing
stable source and match identities, never database-generated IDs. The command
passes it to `internal/ingest` in-process. A future authenticated API or queue
may transport the same submission without changing its semantics.

## Runtime

```text
operator  command  matchup  research  YouTube  audio/OpenAI  ingest/PostgreSQL
   |         |        |        |         |          |                |
   |-- key ->|-- read>|        |         |        |            |
   |         |< context        |         |        |            |
   |         |-- plan/select ->|         |        |            |
   |         |---------------- search -->|        |            |
   |         |<----------- candidates ---|        |            |
   |         |                            |        |            |
   |         | for each selected video, sequentially:          |
   |         |---------------- metadata ->|        |            |
   |         |-- completed extraction? ----------------------->|
   |         |<------------------------- yes: skip / no: run --|
   |         |--------------------------- video -->|            |
   |         |<--------- transcript segments ------|            |
   |         |---------------------- claims ------>|            |
   |         |-- EvidenceSubmission --------------------------->|
   |         |                                     BEGIN/source |
   |         |                              extraction/claims    |
   |         |                                      links/COMMIT|
```

Ten deterministic queries are built from the two canonical competitor names
and arm. YouTube relevance ordering supplies candidates; round-robin selection
prevents one broad query from consuming the whole budget. Metadata bounds and
diagnoses the work but never establishes relevance. Selected videos are
downloaded to a temporary directory,
transcribed by OpenAI, and then passed to structured claim extraction. The
audio source, transcription provider, and claim extractor are independent Go
interfaces; the current implementations use direct `yt-dlp` execution and
OpenAI HTTP calls. A future Python adapter can replace an implementation at
composition time without changing the coordinator or persistence boundary.

Repeated `--video-id` flags bypass search while retaining the same metadata,
analysis, validation, and persistence path.

## Boundaries And Validation

```text
OpenAI structured JSON
   |
   v
StructuredExtraction (schema derived from this Go type)
   |
   +--> structural parse
   +--> source validation: enum, timestamp, subject, required meaning
   |
   v
EvidenceSubmission v1
   |
   +--> generic structural/reference validation
   +--> read canonical match and competitor IDs
   |
   v
one PostgreSQL evidence transaction
```

The Go response type is the structured-output source of truth. The derived
schema is sent to OpenAI and the response is parsed back into that type.
Domain validation remains explicit because a JSON schema cannot prove that a
subject belongs to the selected match or that a timestamp fits the video.

## Data Model

```text
              events
                ^
                | event_id
athletes <--- match_competitors ---> matches
   ^                                   ^
   |                                   |
claim_subjects ---> claims ------------+
                      |                 |
                      v                 |
              source_extractions ------+
                      |
                      v
                   sources

ingestion_runs records each database submission attempt (evidence or result).
```

`events` groups matches by promoter event (slug, promoter, name, held-on
date). `matches.event_id` is `NOT NULL`, `matches.status` is one of
`scheduled`, `completed`, `dq`, `no_contest`, and `match_competitors.score`/
`.result` hold the outcome. These are populated only by `ingest.SubmitResult`
(MPI-19); `ingest.Submit` (evidence) never touches them.

### Result And Evidence Ownership

`internal/ingest` holds two submission types with deliberately opposite trust
directions:

```text
EvidenceSubmission   reads canonical identity, never creates it.
                     Requires the match to already exist. Untrusted content
                     (an LLM-extracted claim) can attach evidence to a match
                     but can never fabricate one.

ResultSubmission     OWNS canonical identity. Creates events, athletes,
                     matches, and competitor outcomes in one transaction.
                     Importing a result is how a match enters the system.
```

Both submission types remain behind `internal/ingest` as the single
transactional writer; the asymmetry is in what each is allowed to create, not
in where the write happens.

`matches.natural_key` stays a plain, writer-agnostic `text unique` column.
`ResultSubmission` mints its own keys deterministically:
`<event-slug>:<athlete-a-slug>:<athlete-b-slug>:<arm>[:<sequence>]`, with
athlete slugs sorted so competitor order in source data never changes the
key, and a sequence suffix only when the same pair meets again on the same
arm within the same event (a genuine rematch, disambiguated from a replay of
the same submission by comparing `scheduled_at`).

Each actual OpenAI extraction attempt produces a `source_extractions` row. Completed
zero-claim results are durable. Failed attempts store their error and no
claims. New claims reference the exact completed extraction. The completed
extraction identity is `(source, match, provider, model, prompt version)`, so
reruns skip transcription and extraction and do not duplicate evidence.

Sources, extractions, claims, and subject links for one video are atomic. A
failure rolls back that video's evidence and records a failed ingestion run.
Other videos are independent.

## Adding A Source Adapter

1. Add a provider package below `services/importer/internal`.
2. Keep provider request/response types, HTTP behavior, and semantic validation
   inside that package.
3. Map validated output to `ingest.EvidenceSubmission`; preserve original
   provider payloads.
4. Do not import `internal/dbgen`, pgx, or accept a database pool.
5. Add HTTP fixture tests and a real-PostgreSQL orchestration test.
6. Add a command that resolves an existing match and composes the adapter with
   `ingest.Submit`.

## Operations

Local development uses `docker-compose.yaml`'s `postgres` service (started by
default). A prior instance (service `postgres-legacy`, port 5433) is kept
alongside it, unmodified, holding dev-stage rows from before MPI-20's cutover
to a fresh database. It is deprecated and excluded from the default
`docker-compose up`; start it explicitly only to inspect old data:

```sh
docker compose --profile legacy up -d postgres-legacy
```

Apply all migrations in lexical order before running an importer command.
The Go command reads configuration from its process environment. It does not
load `.env`, select a database based on an environment name, or run database
migrations. Local development may use the repository wrapper, which loads the
ignored `.env` before executing the same command:

```sh
cd services/importer
./scripts/run-ingest-youtube.sh --help
```

CI, staging, and production should inject the variables through their native
configuration and secret mechanisms. Every deployment supplies its own
`DATABASE_URL`; environments use separate databases with the same ordered
migration set.

Copy `.env.example` to `.env` for local setup. The command requires:

```text
DATABASE_URL
YOUTUBE_API_KEY
OPENAI_API_KEY
OPENAI_EXTRACTION_MODEL
```

Optional provider endpoint overrides are also supported:

```text
YOUTUBE_API_BASE_URL
OPENAI_API_BASE_URL
```

The default provider endpoints are used when the optional values are absent.

Operational settings are optional:

```text
INGEST_HTTP_TIMEOUT   request timeout duration, default 60s
INGEST_AUDIO_TIMEOUT  audio download timeout, default 15m
INGEST_LOG_FORMAT     text (default) or json
INGEST_LOG_LEVEL      debug, info (default), warn, or error
```

The command emits structured progress events for match resolution, provider
requests, candidate selection, extraction, persistence, skips, failures, and
the final summary. Logs go to standard error, so the local wrapper and CI pass
them through without owning logging behavior. JSON output is suitable for CI
collection; text output is intended for local operation. API keys, prompts, and
raw provider payloads are not logged.

Example:

```sh
cd services/importer
go run ./cmd/ingest-youtube \
  --match-natural-key '2026-06:artyom-morozov:ermes-gasparini:right' \
  --max-videos 10
```

For direct videos:

```sh
go run ./cmd/ingest-youtube \
  --match-natural-key '2026-06:artyom-morozov:ermes-gasparini:right' \
  --video-id bWmtNWQM_Ro
```

The local command also requires `yt-dlp` and `ffmpeg` on `PATH`. The same
runtime dependencies must be installed in the CI or cloud worker image.

Verification:

```sh
cd services/importer
gofmt -l .
go vet ./...
go test -list . ./...
go test -v -count=1 ./...
INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  go test -v -count=1 -tags integration ./...
```

Integration tests reject any database not named
`armwrestling_math_test` before destructive setup.

## Review Guide

The ingestion command has one active runtime path: YouTube metadata, temporary
audio, OpenAI transcription, OpenAI claim extraction, and atomic evidence
persistence. `internal/transcript` holds replaceable processing ports and their
current adapters; `internal/youtube` owns source metadata and direct evidence
mapping; `internal/youtubeingest` coordinates the workflow. Generated sqlc
files and historical contracts are committed for reproducibility and audit,
but are not hand-written runtime behavior.
