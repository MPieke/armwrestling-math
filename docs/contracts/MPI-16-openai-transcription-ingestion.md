---
linear_issue: MPI-16
status: approved
---

# Contract MPI-16: OpenAI Transcription Ingestion

## Scope

Replace Gemini video analysis with a transcript-first workflow. The existing
deterministic YouTube discovery, candidate selection, match lookup, evidence
validation, provenance, and atomic persistence remain in scope. A selected
video is downloaded as temporary audio with `yt-dlp`, transcribed through the
OpenAI file transcription API, and passed as timestamped text to an OpenAI
structured claim-extraction step.

Transcript persistence and long-term media storage are out of scope. This
contract concerns the processing architecture and the existing evidence
persistence boundary only.

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
    +--> AudioSource.Acquire(video URL)
    |       `--> temporary audio file
    +--> TranscriptionProvider.Transcribe(audio file)
    |       `--> timestamped transcript segments
    +--> ClaimExtractor.Extract(transcript, match context)
    |       `--> validated structured claims
    `--> ingest.Submit(EvidenceSubmission) -> PostgreSQL

Temporary audio and transcript data are deleted after the video attempt.
Provider credentials and raw media are never logged.
```

The Go coordinator depends on these provider-neutral ports:

```text
AudioSource
  Acquire(ctx, video URL) -> AudioArtifact

TranscriptionProvider
  Transcribe(ctx, AudioArtifact, hints) -> Transcript

ClaimExtractor
  Extract(ctx, Transcript, MatchContext) -> StructuredExtraction
```

The initial adapters are `yt-dlp` for `AudioSource`, OpenAI file
transcription for `TranscriptionProvider`, and OpenAI structured text
extraction for `ClaimExtractor`. These concrete providers are selected at the
composition root. The workflow, validation, persistence, and replay behavior
must not import provider-specific packages or types.

```text
Go coordinator
    |
    +--> AudioSource interface
    |       `--> YTDLPAudioSource
    |              `--> exec.CommandContext("yt-dlp", ...)
    |
    +--> TranscriptionProvider interface
    |       `--> OpenAITranscriptionProvider
    |              `--> OpenAI HTTP API
    |
    `--> ClaimExtractor interface
            `--> OpenAIClaimExtractor
                   `--> OpenAI HTTP API
```

The initial audio adapter executes `yt-dlp` directly without invoking a shell.
Subprocess arguments are passed as an argument vector, execution is bounded by
the request context, and stdout/stderr are captured through explicit process
streams.

The interfaces do not expose subprocess, HTTP, OpenAI, or Python concepts.
Their request and response structures are versioned, JSON-serializable domain
types. A future implementation may satisfy the same interface by invoking a
Python process, calling a Python HTTP/gRPC worker, or using another provider.
That future replacement changes composition-root wiring and its adapter only;
the coordinator, retries, validation, and persistence remain unchanged.

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
OPENAI_TRANSCRIPTION_MODEL   default: whisper-1 (timestamped segments)
OPENAI_EXTRACTION_MODEL      explicit text model
INGEST_AUDIO_TIMEOUT         bounded download timeout
INGEST_HTTP_TIMEOUT          bounded API timeout
```

The local wrapper may load `.env`; CI, staging, and production inject these
values directly. No dotenv loading is added to the Go binary.

## 3. Commit-by-commit breakdown

1. `test(MPI-16): define audio acquisition and transcription behavior`
   - Define versioned, JSON-serializable port types and contract tests.
   - Add tests for deterministic `yt-dlp` invocation, temporary-file cleanup,
     OpenAI multipart transcription requests, timestamped response parsing,
     timeout handling, and provider failure classification.
   - Tests use local fixtures and fake HTTP/process boundaries.

2. `feat(MPI-16): add OpenAI transcript pipeline`
   - Add provider-neutral audio, transcription, and claim-extraction ports.
   - Add a direct-exec `yt-dlp` adapter and OpenAI HTTP adapters at the
     composition root.
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

- the coordinator tests use fake interfaces without subprocess or HTTP access;
- port request and response types round-trip through JSON without loss;
- `yt-dlp` receives the expected argument vector without shell interpretation
  and writes only within a temporary directory;
- temporary audio is removed on success, failure, and cancellation;
- OpenAI receives an accepted audio format and the configured transcription
  model;
- transcript segments retain timestamps and text;
- a provider timeout is logged with stage and duration but without secrets;
- one failed video does not affect another video or leave partial evidence;
- replay skips completed extraction without repeating transcription or claim
  extraction.

The adapter design must also be reviewable against this future substitution:

```text
Current: Go coordinator -> in-process OpenAI adapter -> OpenAI API
Future:  Go coordinator -> Python adapter/service  -> processing implementation
```

No Python runtime, Python service, generic plugin framework, HTTP server, gRPC
schema, or queue is implemented by this contract.

Manual pilot:

```sh
./scripts/run-ingest-youtube.sh \
  --match-natural-key '2026-06:artyom-morozov:ermes-gasparini:right' \
  --video-id 'bWmtNWQM_Ro'
```

The pilot must verify the OpenAI model, transcript-derived claims, timestamps,
source extraction provenance, cleanup of temporary media, and replay behavior.
No real provider calls are made by ordinary CI.
