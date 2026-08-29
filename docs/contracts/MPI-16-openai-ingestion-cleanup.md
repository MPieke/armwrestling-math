---
linear_issue: MPI-16
status: implemented
---

# Contract MPI-16: OpenAI Ingestion Cleanup

## Scope

Remove the obsolete Gemini ingestion implementation introduced earlier in
MPI-16 and make the transcript-first OpenAI path the sole YouTube ingestion
workflow. This refactor does not change the database schema, delete persisted
evidence, or alter the completed OpenAI extraction already stored for
`bWmtNWQM_Ro`.

## 1. Current-state architecture

```text
cmd/ingest-youtube
    |
    `--> youtubeingest.RunTranscript
            |
            +--> YouTube metadata
            +--> AudioSource -> yt-dlp
            +--> TranscriptionProvider -> OpenAI
            +--> ClaimExtractor -> OpenAI
            |
            `--> TranscriptSubmission
                    -> Gemini-shaped conversion
                    -> provider rewrite to OpenAI
                    -> ingest.Submit -> PostgreSQL

Unused parallel path:

youtubeingest.Run -> GeminiClient -> Gemini submission -> PostgreSQL
```

Runtime sequence:

```text
video -> temporary audio -> transcript -> claims -> Gemini conversion/rewrite
      -> validation -> PostgreSQL
```

## 2. Target-state architecture

```text
cmd/ingest-youtube
    |
    `--> youtubeingest.Run
            |
            +--> YouTube metadata
            +--> AudioSource -> yt-dlp
            +--> TranscriptionProvider -> OpenAI
            +--> ClaimExtractor -> OpenAI
            +--> native transcript validation
            +--> native EvidenceSubmission mapping
            `--> ingest.Submit -> PostgreSQL
```

Runtime sequence:

```text
video -> temporary audio -> timestamped transcript -> structured claims
      -> semantic validation -> atomic PostgreSQL persistence
```

The sole runner depends on provider-neutral transcript ports. `internal/youtube`
retains YouTube metadata and source-to-evidence mapping, but maps
`transcript.StructuredExtraction` directly. Gemini configuration, HTTP client,
response types, validation types, submission rewriting, runner, and tests are
removed.

No ER diagram is required: this refactor makes no schema or relationship
change.

## 3. Commit-by-commit breakdown

1. `docs(MPI-16): define OpenAI ingestion cleanup`
   - Add this contract.
   - Reviewable alone because it records the agreed deletion and consolidation
     boundary before implementation.

2. `test(MPI-16): define native transcript evidence mapping`
   - Update adapter and validation tests to define direct OpenAI provenance,
     native claim validation, and failed-attempt auditing.
   - The tests fail while the adapter still converts through Gemini types.

3. `refactor(MPI-16): remove Gemini evidence bridge`
   - Map transcript claims directly to `EvidenceSubmission` and remove Gemini
     request/response/model/validation/rewrite code.
   - Remove Gemini configuration and its tests.
   - Reviewable because the behavior remains evidence mapping and validation,
     but the obsolete provider dependency disappears.

4. `test(MPI-16): define unified transcript ingestion flow`
   - Replace the Gemini integration test with fake audio, transcription, and
     extraction ports.
   - Assert cleanup, replay skip, failure isolation, provenance, and transcript
     timestamp validation against real PostgreSQL.

5. `refactor(MPI-16): consolidate OpenAI ingestion runner`
   - Rename `RunTranscript` to `Run`, remove the Gemini runner, and update the
     command composition root.
   - Reviewable because one public orchestration path replaces two.

6. `docs(MPI-16): align architecture with OpenAI ingestion`
   - Remove active Gemini references from environment and architecture docs.
   - Preserve older contracts as historical records and add a short PR review
     guide identifying runtime, test, generated, and contract changes.

## 4. Verification plan

Run from `services/importer`:

```sh
test -z "$(gofmt -l .)"
go vet ./...
go test -list . ./...
go test -v -count=1 ./...
go build ./cmd/ingest-youtube
INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  go test -v -count=1 -tags integration ./...
sqlc generate -f sqlc.yaml
git diff --quiet -- internal/dbgen
```

Confirm no active Gemini runtime or configuration remains:

```sh
rg -n 'Gemini|gemini' services/importer .env.example docs/architecture/ingestion.md
```

Historical contract references are allowed. Run the completed public video
without another provider call:

```sh
./scripts/run-ingest-youtube.sh \
  --match-natural-key '2026-06:artyom-morozov:ermes-gasparini:right' \
  --video-id bWmtNWQM_Ro
```

It must return `selected=1 completed=0 failed=0 skipped=1`. Query PostgreSQL
to verify the completed OpenAI extraction and its seven claims remain intact.
