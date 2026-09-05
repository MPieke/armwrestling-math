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
                      |     |            |
                      |     v            |
                      | claim_annotations
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

### Manual Result Loading

`cmd/load-results` reads a hand-copied CSV, validates every row before opening
a PostgreSQL connection, then submits rows in file order through
`ingest.SubmitResult`. A malformed row therefore reaches no database work; a
later persistence failure is reported for its row while later rows are still
attempted.

```text
event_slug,event_name,promoter,event_date,arm,weight_class,athlete_a,
athlete_b,score_a,score_b,status,video_id,bout
```

`video_id` and `bout` are optional. A known video becomes a
`match_videos(match_id, youtube_video_id)` row for deterministic evidence
ingestion. Repeated same-day matches with the same event, arm, and athlete
pair require distinct positive `bout` values; their minute offsets make a
genuine rematch distinct from a replay during natural-key resolution.

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

### Claim Annotation (MPI-28)

`claim_annotations` adds a structured interpretation layer on top of an
already-persisted claim, one row per `(claim_id, model, prompt_version)`.
`internal/annotate` follows MPI-16's structured-output pattern exactly (a Go
type derives the OpenAI schema, the response decodes back into that type,
semantic validation runs before persistence) but never creates or modifies a
claim itself -- only annotates one that already exists. `cmd/annotate-claims`
(`internal/annotateclaims`) lists every claim missing an annotation for a
given `(model, prompt_version)`, calls the annotator, validates, and persists;
one claim's failure doesn't stop the batch, mirroring
`internal/youtubeingest`'s per-candidate error handling.

`claim_type` reuses `transcript.Claim`'s existing extraction-time vocabulary
(`form | tactic | injury | endurance | setup | opponent_comparison | other`)
rather than inventing a second, overlapping one. `concepts` (a 20-item
controlled vocabulary: `top_roll`, `hook`, `press`, `side_pressure`,
`back_pressure`, `wrist_control`, `supination`, `grip_strength`,
`arm_length`, `hand_size`, `frame_and_leverage`, `reserve_strength`,
`explosive_strength`, `start_position`, `shoulder_engagement`,
`elbow_discipline`, `injury_or_recovery_status`, `training_regimen`,
`mental_focus`, `matchup_specific_history`) and `temporality`/`certainty`
(the latter two reusing `scripts/evidence_dimension_models.py`'s dimensions
from early discovery work) are this layer's own vocabulary. The model
resolves `subject_athlete_name` as free text against the match's two
competitor names rather than being asked to output a foreign key directly;
`annotateclaims.resolveSubjectID` maps a name that doesn't exactly match
either competitor (including the deliberate empty string for "general/both")
to no subject, not an error.

`internal/structured`'s schema derivation gained one capability for this:
an `enum` tag on a `[]string` field now constrains each array *element*
(`Items.Enum`), not the array itself -- OpenAI's structured-output schema
has no way to express "one of these values" for a whole list, only for each
item in it.

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

`./scripts/run-ingest-batch.sh <pairs-file> [parallelism=4] [max-videos=1]`
runs `cmd/ingest-youtube` across many matches at once (`pairs-file`: one
"`<match-natural-key> <video-id>`" per line, space-separated -- natural
keys use `:` internally, never spaces). Each invocation is an independent
process with its own database pool and temp directory, so running several
concurrently is safe; `parallelism` bounds how many run at once to stay
under provider rate limits. Pass `max-videos` above 1 to also search for
additional videos about the same match beyond the known one (MPI-32) --
`selectCandidates` always includes every explicit `--video-id` and fills
any remaining slots via search, rather than treating an explicit ID as
exclusive of it.

### Self-Hosted Transcription (MPI-33)

`TRANSCRIPTION_PROVIDER=whisper_cpp` (default: `openai`) switches
`cmd/ingest-youtube` to `transcript.WhisperCPPTranscriber` instead of the
OpenAI Whisper API, pointed at `WHISPER_SERVER_BASE_URL` (default
`http://127.0.0.1:8080`). One 48-video batch (MPI-28) cost $6.53, ~99% of it
Whisper-1 API minutes on full-length match broadcasts; self-hosting removes
essentially all of that going forward. whisper.cpp's `/inference` endpoint is
deliberately OpenAI-response-compatible, so `WhisperCPPTranscriber` shares
`decodeVerboseJSONTranscript` with `OpenAITranscriber` rather than
duplicating segment parsing -- only the request side (no API key, no
`model` field) differs.

Two ways to run the server, same client code either way:

```sh
# Local dev: native binary, Metal-accelerated on Apple Silicon (Docker
# Desktop cannot pass Metal through to a Linux container, so the image
# below is meaningfully slower here). Requires `brew install whisper-cpp`.
cd services/importer
./scripts/run-whisper-server.sh   # downloads the model to ~/.cache/whisper.cpp on first run

# The portable, CPU-only path CI will eventually use:
docker compose --profile whisper up -d whisper
```

Real numbers on an M4 (native, Metal, `large-v3-turbo`): an 18m48s video
transcribed in 87s self-hosted vs. 52s via the OpenAI API -- close, not an
order of magnitude apart. The Docker CPU-only path is slower than this,
not yet measured for real; local dev should use the native script.

`run-whisper-server.sh` downloads its model to a temp file and renames it
atomically only on success: a truncated model file loads without error but
produces silently hallucinated, plausible-looking garbage in every
language except the right one. This happened once during development (a
background download was interrupted) and looked like a transcription
*quality* problem before the real cause -- a ~120MB short file -- was
found by comparing the downloaded size against the source's real
`Content-Length`.

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

The result loader needs only `DATABASE_URL` and does not load `.env` itself:

```sh
cd services/importer
DATABASE_URL=... go run ./cmd/load-results --file testdata/sample_results.csv
psql "$DATABASE_URL" -c "
  select e.slug, m.weight_class, mv.youtube_video_id
  from matches m
  join events e on e.id = m.event_id
  left join match_videos mv on mv.match_id = m.id
  order by e.slug, mv.youtube_video_id;"
```

`cmd/annotate-claims` (`./scripts/run-annotate-claims.sh --prompt-version v1`) uses
the same required variables. It reads an optional `OPENAI_ANNOTATION_MODEL`,
falling back to `OPENAI_EXTRACTION_MODEL` when absent, since annotation is a
distinct prompt/schema from extraction but there's no reason to require a
second model choice by default.

Optional provider endpoint overrides are also supported:

```text
YOUTUBE_API_BASE_URL
OPENAI_API_BASE_URL
TRANSCRIPTION_PROVIDER    openai (default) or whisper_cpp
WHISPER_SERVER_BASE_URL   default http://127.0.0.1:8080, used only when
                          TRANSCRIPTION_PROVIDER=whisper_cpp
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
