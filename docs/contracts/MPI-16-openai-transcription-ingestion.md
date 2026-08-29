---
linear_issue: MPI-16
status: proposed
---

# Contract MPI-16: OpenAI Transcription Ingestion

## Scope

Replace Gemini video analysis with a transcript-first workflow. The existing
deterministic YouTube discovery, candidate selection, match lookup, evidence
validation, provenance, and atomic persistence remain in scope. A selected
video is downloaded as temporary audio with `yt-dlp`, transcribed through the
OpenAI file transcription API, and passed as timestamped text to an OpenAI
structured claim-extraction step.

The transcript is an intermediate artifact by default. The database continues
to store claims, source metadata, extraction provenance, and audit records; it
does not permanently store full transcripts unless a later data-policy ticket
explicitly adds that requirement.

## 1. Current-state architecture

```text
cmd/ingest-youtube
    |
    +--> YouTube metadata
    +--> Gemini video URL analysis
    `--> EvidenceSubmission -> PostgreSQL

Gemini currently receives the video URL directly. No audio acquisition or
transcript provider boundary exists.
```

Runtime sequence:

```text
operator -> YouTube metadata -> Gemini video analysis -> claims -> PostgreSQL
```

## 2. Target-state architecture

```text
cmd/ingest-youtube
    |
    +--> YouTube metadata
    +--> audio.Acquire(video URL)
    |       `--> temporary audio file
    +--> transcription.Transcribe(audio file)
    |       `--> timestamped transcript segments
    +--> extraction.Extract(transcript, match context)
    |       `--> validated structured claims
    `--> ingest.Submit(EvidenceSubmission) -> PostgreSQL

Temporary audio and transcript data are deleted after the video attempt.
Provider credentials and raw media are never logged.
```

Runtime sequence:

```text
operator
  -> YouTube metadata
  -> yt-dlp temporary audio
  -> OpenAI file transcription
  -> OpenAI structured text extraction
  -> atomic PostgreSQL persistence
```

Configuration is injected consistently across environments:

```text
OPENAI_API_KEY
OPENAI_TRANSCRIPTION_MODEL   default: gpt-transcribe
OPENAI_EXTRACTION_MODEL      explicit text model
INGEST_AUDIO_TIMEOUT         bounded download timeout
INGEST_HTTP_TIMEOUT          bounded API timeout
```

The local wrapper may load `.env`; CI, staging, and production inject these
values directly. No dotenv loading is added to the Go binary.

## 3. Commit-by-commit breakdown

1. `test(MPI-16): define audio acquisition and transcription behavior`
   - Add tests for deterministic `yt-dlp` invocation, temporary-file cleanup,
     OpenAI multipart transcription requests, timestamped response parsing,
     timeout handling, and provider failure classification.
   - Tests use local fixtures and fake HTTP/process boundaries.

2. `feat(MPI-16): add OpenAI transcript pipeline`
   - Add audio acquisition and OpenAI transcription adapters.
   - Replace Gemini video analysis with transcript-based structured extraction.
   - Add bounded timeouts, cancellation, and safe per-video failure auditing.

3. `test(MPI-16): cover transcript claim extraction integration`
   - Verify transcript timestamps map to persisted claim timestamps and claims
     retain source extraction provenance.
   - Verify failed acquisition/transcription does not create partial claims.

4. `feat(MPI-16): persist transcript-derived evidence`
   - Wire transcript segments through validation and atomic submission.
   - Preserve replay/skip behavior and canonical match immutability.

5. `docs(MPI-16): document OpenAI transcription operations`
   - Add environment variables, required `yt-dlp`/`ffmpeg` dependencies,
     local/cloud execution, cleanup policy, and troubleshooting.

## 4. Verification plan

Run from `services/importer`:

```sh
go test -v -count=1 ./...
go test -v -count=1 -tags integration ./...
go vet ./...
test -z "$(gofmt -l .)"
sqlc generate -f sqlc.yaml
git diff --quiet -- internal/dbgen
```

Boundary tests must prove:

- `yt-dlp` receives the expected video URL and writes only within a temporary
  directory;
- temporary audio is removed on success, failure, and cancellation;
- OpenAI receives an accepted audio format and the configured transcription
  model;
- transcript segments retain timestamps and text;
- a provider timeout is logged with stage and duration but without secrets;
- one failed video does not affect another video or leave partial evidence;
- replay skips completed extraction without repeating transcription or claim
  extraction.

Manual pilot:

```sh
./scripts/run-ingest-youtube.sh \
  --match-natural-key '2026-06:artyom-morozov:ermes-gasparini:right' \
  --video-id 'bWmtNWQM_Ro'
```

The pilot must verify the OpenAI model, transcript-derived claims, timestamps,
source extraction provenance, cleanup of temporary media, and replay behavior.
No real provider calls are made by ordinary CI.
