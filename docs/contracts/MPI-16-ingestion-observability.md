---
linear_issue: MPI-16
status: approved
---

# Contract MPI-16: Ingestion Observability and Request Timeouts

## 1. Current-state architecture

```text
local wrapper / CI -> cmd/ingest-youtube
                         |
                         +--> YouTube request (no timeout)
                         +--> Gemini request (no timeout)
                         `--> final summary only
```

Provider and per-video failures are not consistently visible to the operator.

## 2. Target-state architecture

```text
local wrapper / CI -> cmd/ingest-youtube
                         |
                         +--> Go structured logs -> terminal or CI output
                         +--> YouTube request with timeout
                         +--> Gemini request with timeout
                         `--> final summary
```

Logs include stage, safe query/video identifiers, outcome, duration, and
sanitized errors. Human-readable text is the local default; JSON is available
for CI. Secrets, prompts, and raw provider payloads are excluded.

## 3. Commit-by-commit breakdown

1. `test(MPI-16): define ingestion logging and timeout behavior`
   - Test timeout configuration, structured event fields, and provider failure
     visibility.

2. `feat(MPI-16): add ingestion logging and request timeouts`
   - Add standard-library `log/slog` instrumentation and configurable HTTP
     timeout.
   - Log every workflow stage and preserve sequential processing.

3. `docs(MPI-16): document ingestion logs and diagnostics`
   - Document log format, levels, timeout settings, and troubleshooting.

## 4. Verification plan

```sh
cd services/importer
go test -v -count=1 ./...
go test -v -count=1 -tags integration ./...
go vet ./...
test -z "$(gofmt -l .)"
sqlc generate -f sqlc.yaml
git diff --quiet -- internal/dbgen
INGEST_LOG_FORMAT=json ./scripts/run-ingest-youtube.sh --help
```

Run a bounded live direct-video pilot and verify that a provider failure names
the stage and duration without exposing credentials or raw payloads.
