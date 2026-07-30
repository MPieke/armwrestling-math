---
linear_issue: MPI-16
status: proposed
---

# Contract MPI-16: Deterministic YouTube Evidence Ingestion V1

## Scope

Given an existing PostgreSQL match, deterministically discover relevant public
YouTube videos, inspect their actual content with Gemini, validate structured
claims, and persist sources, extraction provenance, claims, and subject links.

MPI-17 owns future AI-generated research plans. V1 uses only fixed query
templates. Match registration, autonomous search, captions/transcripts,
polling, scheduling, concurrency, and multiple matches per run are out of
scope. Separately deployed source adapters and a network-facing generic-ingest
API are also deferred; V1 preserves that boundary in-process without taking on
distributed authentication, retries, or operations.

## 1. Current-State Architecture

### Components

```text
+----------------------+       +--------------------------------------+
| Python YouTube POC   |       | Go generic ingestion                 |
|                      |       |                                      |
| fixed search queries |       | caller supplies complete IngestBatch |
| metadata scoring     |       | Validate                              |
| Gemini video analysis|       | upsert athletes and match             |
| model evaluation     |       | upsert sources and claims             |
+----------+-----------+       +------------------+-------------------+
           |                                      |
           v                                      v
      JSON artifacts                         PostgreSQL

The Python and Go paths are not connected.
```

The POC issued 21 fixed queries, found 180 unique videos, retained 136 after
metadata filtering, analyzed the top 40, and accepted 8 sources with 44 claims.
This shows that metadata can bound cost but cannot establish content relevance.

### Current Runtime Sequence

```text
caller          IngestBatch          Validate/Run              PostgreSQL
  |                  |                    |                         |
  |-- full match --->|                    |                         |
  |-- athletes ----->|                    |                         |
  |-- evidence ----->|-- validate ------->|                         |
  |                  |                    |-- upsert match -------->|
  |                  |                    |-- upsert athletes ----->|
  |                  |                    |-- write evidence ------>|
```

The current path assumes every evidence adapter may create or update match and
athlete data. There is no match lookup, YouTube client, deterministic query
planner, Gemini client, or extraction-level provenance record.

### Current Data Model

```text
athletes <--- match_competitors ---> matches
   ^                                   ^
   |                                   |
claim_subjects ---> claims ------------+
                      |
                      v
                   sources

ingestion_runs records generic database attempts.
```

`claims.extraction_model` identifies a model name, but the full model response,
prompt version, usage, and extraction status have no durable owner.

## 2. Target-State Architecture

### Components

```text
+----------------------- cmd/ingest-youtube ------------------------+
| The command is the sequential coordinator; package placement does  |
| not imply concurrent execution.                                    |
+--------------------------------------------------------------------+
     | 1. Resolve(match natural key)
     v
internal/matchup ---------------------> MatchContext
     | 2. BuildPlan(MatchContext)
     v
internal/research --------------------> SearchPlan
     | 3. Search(SearchPlan), or use explicit video IDs
     v
internal/youtube ---------------------> candidate lists
     | 4. Select(candidate lists, max-videos)
     v
internal/research --------------------> ordered candidates
     | 5. Analyze(one candidate, MatchContext) [repeat in order]
     v
internal/youtube ---------------------> EvidenceSubmission v1
     | 6. Submit(EvidenceSubmission v1)
     v
internal/ingest ----------------------> PostgreSQL transaction
```

Ownership is explicit:

- PostgreSQL owns matches and athletes.
- `internal/matchup` resolves a read-only match context.
- `internal/research` owns provider-neutral deterministic planning, candidate
  deduplication, selection budgets, and stable ordering.
- `internal/youtube` owns YouTube API shapes, URL normalization, metadata, and
  Gemini video analysis.
- `internal/ingest` owns atomic evidence persistence and audit records.

`internal/youtube` must not import `internal/dbgen`, execute SQL, accept a
database pool, or expose PostgreSQL-specific types. It produces a
provider-neutral `EvidenceSubmission` that the command passes to
`internal/ingest` in-process.

### Durable Deployment Boundary

```text
V1: one deployable

  ingest-youtube command
          |
          +-- youtube.Collect(...) --> EvidenceSubmission v1
          |
          `-- ingest.Submit(...)   --> PostgreSQL

Future deployment split (not implemented by MPI-16)

  YouTube adapter service
          |
          | authenticated API or queue
          v
  EvidenceSubmission v1
          |
          v
  Generic ingest service --> PostgreSQL
```

`EvidenceSubmission` must be JSON-serializable, carry an explicit schema
version, and contain stable identities rather than database-generated IDs.
The generic ingest boundary revalidates it before any database mutation. This
keeps transport replaceable: moving the submission across an authenticated
API or queue later must not change its evidence semantics.

MPI-16 deliberately excludes HTTP endpoints, queues, service authentication,
adapter-specific containers, distributed retry policy, and independent
deployment configuration.

The command requires `--match-natural-key`. A missing match, a match without
competitors, or an ambiguous match fails before any YouTube or Gemini request.
Evidence ingestion never updates match metadata or competitor membership.

### Deterministic Search Plan

For competitors `A` and `B` and arm `R`, V1 generates these ten queries:

```text
A B
A B R arm
A B prediction
A B analysis
A interview R arm
B interview R arm
A training R arm
B training R arm
A injury recovery
B injury recovery
```

Each query uses YouTube relevance ordering and one bounded result page.
Candidates are deduplicated by video ID and selected round-robin across query
result lists until `--max-videos` is reached. This avoids a bespoke keyword
score and guarantees representation from each query family.

Titles, descriptions, channels, views, and publication dates are metadata and
diagnostics only. They cannot make a candidate acceptable. Gemini must inspect
the actual public video before it can contribute a claim.

Repeated `--video-id` arguments bypass search and use the same metadata,
analysis, validation, and persistence path.

### Target Runtime Sequence

```text
command       matchup       research       YouTube       Gemini       ingest/DB
   |              |              |              |             |             |
   |-- resolve -->|              |              |             |             |
   |<-- context --|              |              |             |             |
   |-- plan ------------------->|              |             |             |
   |<-- queries ----------------|              |             |             |
   |-- search -------------------------------->|             |             |
   |<-- candidate lists ------------------------|             |             |
   |-- select ----------------->|              |             |             |
   |<-- ordered candidates -----|              |             |             |
   |              |              |              |             |             |
   |  for each ordered candidate, sequentially: |             |             |
   |-- analyze -------------------------------->|             |             |
   |              |              |              |-- video --->|             |
   |              |              |              |<-- JSON ----|             |
   |<-- EvidenceSubmission v1 ------------------|             |             |
   |-- submit ---------------------------------------------------------->|
   |              |              |              |             |       BEGIN |
   |              |              |              |             | source      |
   |              |              |              |             | extraction  |
   |              |              |              |             | claims/links|
   |              |              |              |             |      COMMIT |
```

Videos are persisted independently. One unavailable or invalid video does not
discard successful evidence from other candidates. A failed Gemini attempt may
persist source metadata and a failed extraction record, but never claims.

Before a Gemini call, the command checks for a completed extraction with the
same source, match, provider, explicit model, and prompt version. If one exists,
the candidate is skipped. V1 has no force/reprocess mode.

### Structured Gemini Output

The command requires `GEMINI_MODEL`; it does not use a moving `latest` alias.
The prompt version is a source constant. Gemini structured output uses this
logical schema:

```json
{
  "schema_version": "youtube-claims-v1",
  "claims": [
    {
      "text": "Paraphrased, independently understandable claim",
      "timestamp_seconds": 123,
      "subject_names": ["Canonical Athlete Name"],
      "speaker": "Speaker name or null",
      "confidence": "low|medium|high",
      "relevance": "Why this matters for the requested match",
      "claim_type": "form|tactic|injury|endurance|setup|opponent_comparison|other"
    }
  ],
  "limitations": []
}
```

Go performs semantic validation after JSON-schema validation:

- timestamps are non-negative and do not exceed video duration;
- subjects are members of the resolved match;
- enum values are recognized;
- claim text and relevance are nonempty;
- zero claims require at least one limitation;
- the model cannot create or modify matches or athletes.

### Target Data Model

```text
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
```

```text
source_extractions
+----------------------+
| id                   |
| source_id FK         |
| match_id FK          |
| provider             |
| model                |
| prompt_version       |
| status               |
| extracted_at         |
| raw_response jsonb   |
| usage jsonb          |
| error_message        |
+----------------------+
          ^
          |
claims.source_extraction_id (nullable for pre-MPI-16 legacy rows)
```

Each actual Gemini attempt creates an extraction record. Successful zero-claim
responses remain durable. New claims reference the extraction that produced
them. Existing claims remain valid through a nullable migration.

`sources.raw_payload` stores the original YouTube metadata response plus
deterministic discovery ranks. `source_extractions.raw_response` stores the
complete Gemini response. `claims.raw_payload` stores the validated individual
claim object.

## 3. Test Plan Defined Before Implementation

Tests are committed before the production behavior they specify. Each red
commit is run and its expected failure recorded in the commit message or Linear
comment. The immediately following implementation commit must turn it green
without weakening the assertions.

### Unit Tests

`internal/research`:

- generates the exact ten queries for arbitrary competitor names and either
  arm;
- produces identical output for identical match context;
- round-robins candidates across query families;
- deduplicates repeated video IDs while retaining matched-query provenance;
- applies a stable tie-break and hard candidate budget;
- accepts explicit video IDs without invoking search planning.

`internal/youtube`:

- emits exact YouTube `search.list` and `videos.list` requests;
- maps metadata, duration, raw responses, and discovery ranks;
- rejects missing or malformed YouTube resources;
- emits a Gemini request with an explicit model, prompt version, video URL,
  match context, and structured schema;
- rejects malformed JSON, unknown subjects, invalid enums, negative or
  out-of-range timestamps, empty claim fields, and unexplained zero claims;
- maps valid output into canonical source, extraction, claim, and subject
  inputs without losing raw payloads;
- round-trips `EvidenceSubmission` through JSON without semantic or raw-payload
  loss;
- enforces that `internal/youtube` does not import generated database or
  PostgreSQL implementation packages.

Command/orchestration:

- resolves the match before invoking any external client;
- fails on a missing match or invalid competitor set;
- skips search when explicit video IDs are provided;
- skips Gemini when the same completed model/prompt extraction exists;
- continues to the next video after an independent provider failure.

### PostgreSQL Integration Tests

- apply every migration to a fresh database and assert the extraction table,
  indexes, checks, and foreign keys;
- preserve pre-MPI-16 claims with a nullable extraction reference;
- resolve a match and its competitors by natural key;
- reject a missing match before evidence persistence;
- persist completed and failed extraction attempts with raw response, usage,
  model, provider, prompt version, and error state;
- link claims to the exact extraction, match, source, and allowed subjects;
- prove evidence writes never update match, athlete, or competitor data;
- prove transaction rollback leaves no partial source, extraction, claim, or
  subject graph;
- prove replay/skip behavior keeps every canonical relationship count stable.

### End-to-End CI Integration Test

A tagged test runs the real orchestration against:

- a fresh PostgreSQL service with all migrations;
- local `httptest` YouTube search/metadata endpoints;
- a local `httptest` Gemini endpoint;
- an existing seeded match.

It asserts exact HTTP request order and counts, deterministic candidate order,
persisted values, per-video failure isolation, and second-run Gemini skipping.
No external API key, network call, or paid model invocation is used in CI.

CI must:

- apply all ordered `db/migrations/*.sql`, not only `0001_init.sql`;
- list non-tagged and integration-tagged tests before execution;
- run `go test -v -count=1 ./...`;
- run `go test -v -count=1 -tags integration ./...`;
- retain formatting, vet, sqlc drift, database-name guard, and verbose
  PostgreSQL setup evidence.

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-16): add deterministic YouTube ingestion contract`
   - Add this contract and link it from MPI-16.
   - Reviewable alone because it changes no executable behavior.

2. `build(MPI-16): prepare CI for importer integration suites`
   - Make CI apply every ordered migration and discover/run tagged tests across
     the full importer module.
   - Reviewable alone because it broadens existing CI without adding behavior.

3. `test(MPI-16): define extraction provenance schema`
   - Add red PostgreSQL tests for the new table, constraints, legacy
     compatibility, and generated query boundary.
   - Expected failure: migration/table/query contract does not exist.

4. `feat(MPI-16): add extraction provenance schema`
   - Add `0002_source_extractions.sql`, SQL queries, and regenerated `dbgen`.
   - Reviewable alone because it makes commit 3 green.

5. `test(MPI-16): define existing-match evidence persistence`
   - Add red unit and PostgreSQL tests for match resolution, immutable match
     data, extraction/claim relationships, rollback, and replay.
   - Expected failure: the active ingestion path still owns match mutations and
     lacks extraction persistence.

6. `refactor(MPI-16): require existing matches for evidence ingestion`
   - Implement read-only match context and atomic evidence persistence.
   - Reviewable alone because it makes commit 5 green without external APIs.

7. `test(MPI-16): define deterministic research planning`
   - Add red table-driven tests for exact queries, round-robin selection,
     deduplication, provenance, stable ordering, direct IDs, and budgets.
   - Expected failure: `internal/research` does not exist.

8. `feat(MPI-16): add deterministic evidence research planning`
   - Implement only the generic deterministic behavior defined by commit 7.
   - Reviewable alone because it makes commit 7 green without provider calls.

9. `test(MPI-16): define YouTube and Gemini boundaries`
   - Add red HTTP fixture, semantic validation/mapping, submission JSON
     round-trip, and package-boundary tests.
   - Expected failure: YouTube and Gemini clients do not exist.

10. `feat(MPI-16): add YouTube search and Gemini analysis`
    - Implement the source boundary and versioned `EvidenceSubmission` defined
      by commit 9, without database or generated-query dependencies.
    - Reviewable alone because it makes commit 9 green without a CLI.

11. `test(MPI-16): define YouTube ingestion orchestration`
    - Add red orchestration unit tests and the tagged fake-API/real-PostgreSQL
      end-to-end test.
    - Expected failure: the command workflow does not exist.

12. `feat(MPI-16): add YouTube ingestion command`
    - Add `cmd/ingest-youtube` and implement the workflow defined by commit 11.
    - Compose YouTube collection and generic submission in-process; do not add a
      network ingest API.
    - Require `DATABASE_URL`, `YOUTUBE_API_KEY`, `GEMINI_API_KEY`,
      `GEMINI_MODEL`, and `--match-natural-key`.
    - Support deterministic discovery, repeated explicit `--video-id`, and
      bounded `--max-videos`.
    - Reviewable alone because it makes commit 11 and the CI end-to-end suite
      green.

13. `docs(MPI-16): document deterministic YouTube ingestion`
    - Update architecture and operations documentation with ownership,
      extension points, limitations, and commands.
    - Reviewable alone because it records the implemented architecture.

## 5. Verification Plan

1. Run formatting, static analysis, unit tests, and test discovery:

   ```sh
   cd services/importer
   gofmt -l .
   go vet ./...
   go test -list . ./...
   go test -v -count=1 ./...
   ```

2. Regenerate sqlc and prove committed output is current:

   ```sh
   go install github.com/sqlc-dev/sqlc/cmd/sqlc@v1.30.0
   "$(go env GOPATH)/bin/sqlc" generate -f sqlc.yaml
   git diff --exit-code -- internal/dbgen
   ```

3. Create a fresh `armwrestling_math_test`, apply migrations `0001` and `0002`,
   and run all tagged PostgreSQL tests:

   ```sh
   INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
     go test -v -count=1 -tags integration ./...
   ```

   Assertions must prove:

   - a missing match fails before any external client is called;
   - evidence ingestion does not change match or athlete fields;
   - full YouTube metadata and Gemini provenance are stored;
   - claims link to the correct extraction, match, source, and subjects;
   - malformed or semantically invalid model output creates no claims;
   - rerunning the same model and prompt skips Gemini and adds no duplicates;
   - independent video failure does not roll back another video's evidence.

4. Run an end-to-end orchestration test with real PostgreSQL and local fake
   YouTube/Gemini HTTP servers. Verify exact query order, round-robin candidate
   order, request counts, persisted values, and skip behavior.

5. Prove database safety by targeting any database not named
   `armwrestling_math_test`; destructive integration setup must fail before
   truncation.

6. Validate CI syntax:

   ```sh
   actionlint .github/workflows/generic-ingestion-ci.yml
   ```

7. With explicit developer credentials, run one manual live smoke test against
   a disposable migrated test database and an existing seeded match:

   ```sh
   DATABASE_URL='postgres://.../armwrestling_math_test?sslmode=disable' \
   YOUTUBE_API_KEY='...' \
   GEMINI_API_KEY='...' \
   GEMINI_MODEL='explicit-model-id' \
     go run ./cmd/ingest-youtube \
       --match-natural-key 'known-natural-key' \
       --video-id 'known-public-video-id'
   ```

   Query PostgreSQL directly to verify the source, completed extraction,
   claims, subjects, model, prompt version, raw response, and run audit.
   Repeat the command and verify Gemini is skipped and canonical counts remain
   unchanged.

8. Run the existing GitHub Actions workflow and inspect its verbose unit,
   generated-code, migration, and integration logs. No API secrets or paid
   model calls are permitted in CI.
