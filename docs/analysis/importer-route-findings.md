# Route analysis findings: services/importer

Snapshot of what the redundant-route analysis found in `services/importer`
(Go). Produced by `tools/callgraph` at commit `3399476` (CI run 43622965619 on
PR #17). Method and definitions: `tools/callgraph/README.md` and
`docs/contracts/go-route-analysis.md`. Findings below were checked by reading the
source, not only the tool output; judgements are marked as such.

## Size

114 functions, 147 call sites, 15 packages, 12 entry points (3 `main`, 1 `init`,
8 exported-uncalled), 0 dead-code candidates, 41 terminals, 5 flagged.
430 external calls, of which the noise filter suppressed 277 (mostly `fmt` 128,
`log/slog` 38, `strings` 36, `time` 27).

## Findings

"Independent routes" (K) means routes from entry points that share no function.
Gateways are the last functions where the routes are still separate, so they are
the merge candidates.

### 1. `dbgen.Queries.ListMatchCompetitors`: queried from three layers

- K=2 globally, 2 entries, 4 paths.
- Gateways: `annotateclaims.annotateOne` (`annotateclaims/run.go:56`) and
  `youtubeingest.Run`.
- Nested under `cmd/ingest-youtube.main`: below `Run` the query is reached by
  `matchup.Resolve` (`matchup/matchup.go:22`) and by `ingest.Submit`
  (`ingest/submit.go:28`).
- Judgement: three layers run the same query. A real consolidation candidate;
  check whether `Submit` can reuse what `Resolve` already loaded.

### 2. `transcript.Redact`: shared helper, duplicated callers

- K=2, 2 entries, 3 paths. Gateways: `annotate.OpenAIAnnotator.Annotate`
  (`annotate/openai.go:76`) and `youtubeingest.ingestCandidate`.
- Nested under `cmd/ingest-youtube.main`: `transcript.OpenAIClaimExtractor.Extract`
  (`transcript/openai.go:70`) and `transcript.OpenAITranscriber.Transcribe`
  (`transcript/adapters.go:96`).
- `Transcribe` is reached through the `TranscriptionProvider` interface, which has
  two implementers (OpenAI, whisper.cpp), so that route exists only when the OpenAI
  provider is configured.

### 3. `structured.Decode`: same pair of callers

- K=2, 2 entries, 2 paths. Gateways: `Annotate` (`annotate/openai.go:100`) and
  `Extract` (`transcript/openai.go:94`).
- Judgement for 2 and 3 together: `Redact` and `Decode` are fine as shared
  helpers. The duplication is in their callers. `OpenAIAnnotator.Annotate` and
  `OpenAIClaimExtractor.Extract` repeat the same pipeline (marshal request, HTTP
  call, read body, unmarshal envelope, `structured.Decode`). The same gateway pair
  appearing in two findings is the strongest signal in this run. Candidate: one
  shared chat-completion client.

### 4. `ingest.runIngestion`: designed reuse

- K=2, 2 entries, 3 paths. Gateways: `ingest.Submit` (`ingest/submit.go:44`) and
  `ingest.SubmitResult` (`ingest/result_submit.go:28`).
- Judgement: not a problem. `run.go:19` documents it as the shared ingestion-run
  lifecycle for both. Flagged because the rule is structural.

### 5. `dbgen.Queries.CreateIngestionRun`: flagged only through a nested split

- Global K=1: every route passes `runIngestion`, its only caller (`ingest/run.go:26`).
- Nested under `cmd/ingest-youtube.main`: `ingestCandidate` reaches `ingest.Submit`
  directly (`youtubeingest/run.go:152`, success) and through `auditFailure`
  (`run.go:206`, failure audit).
- Judgement: intentional. Two routes with different meaning (success versus failure
  record). The tool cannot tell this apart from duplication.

## Other observations

- 4 sqlc methods have no callers outside `dbgen`: `CountClaimAnnotations`,
  `GetCompletedSourceExtraction`, `LinkMatchCompetitor`, `UpsertMatch`. They are
  unused code, but the analysis counts them as entry points because they are
  exported.
- `annotate.set` is only used by package-level `var` initializers
  (`annotate/validate.go`). It is `init`, not dead.

## What this analysis cannot say

- Whether several routes are a mistake or intended. Findings 4 and 5 are intended;
  1 to 3 look like real duplication. That call needs evidence the tool does not
  yet collect (different arguments at the terminal, step shape, change history).
- Calls through reflection or function values stored in maps or struct fields are
  not followed.

## How it was verified

All 147 call lines, 430 external call lines and 114 declarations match the source.
Independent greps of non-test call sites matched the graph exactly for
`ListMatchCompetitors` (3), `runIngestion` (2), `Redact` (3) and `Decode` (2).
Details and the defects found along the way are in the contract's verification
results.
