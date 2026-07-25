---
linear_issue: MPI-5
status: proposed
---

# Contract: V1 Legacy Ingestion Pipeline

Import the existing Morozov–Ermes pre-match legacy JSON evidence into
PostgreSQL, safely and idempotently, via a Go importer: legacy adapter →
generic ingestion pipeline → sqlc-generated queries → Postgres.

Out of scope for this slice: predictions, results, evaluation, athlete
aliases table, mechanism atoms/dimensions/clusters, live YouTube ingestion,
new LLM calls, Kubernetes, HTTP APIs, Dockerfile (next planned commit).

## 1. Current-state architecture (C4 container)

```
+----------------------------------------------------------------+
|                     Armwrestling Math (current)                |
|                                                                  |
|  +----------------+      +------------------+                  |
|  | Python pipeline|----->| data/*.json      |                  |
|  | (scripts/)     |      | (legacy evidence)|                  |
|  +----------------+      +------------------+                  |
|                                    |                             |
|                                    v                             |
|                          +------------------+                  |
|                          | build_app_bundle |                  |
|                          +------------------+                  |
|                                    |                             |
|                                    v                             |
|                       +----------------------+                 |
|                       | app/public/          |                 |
|                       | match_dossier.json   |                 |
|                       +----------------------+                 |
|                                    |                             |
|                                    v                             |
|                       +----------------------+                 |
|                       | React app (app/)     |                 |
|                       +----------------------+                 |
|                                                                  |
|  +------------------------------------------------+            |
|  | Postgres (docker-compose) -- provisioned, unused|            |
|  +------------------------------------------------+            |
+----------------------------------------------------------------+
```

No Go code exists. Nothing writes to Postgres. `evidence_v1.json` and
`expanded_evidence_v1.json` are two independently-shaped exports (different
top-level key: `videos[]` vs `sources[]`) sharing 71 + 44 = 115 claims
total, with zero true cross-file duplicates today.

## 2. Target-state architecture (C4 container)

```
+---------------------------------------------------------------------+
|                     Armwrestling Math (target, v1)                  |
|                                                                       |
|  +----------------+      +------------------+                        |
|  | Python pipeline|----->| data/*.json      |  (existing, unchanged) |
|  +----------------+      +------------------+                        |
|                                    |                                  |
|                                    v                                  |
|                       +----------------------+                       |
|                       | app/public/          | --> React app (app/)  |
|                       | match_dossier.json   |     (unchanged)       |
|                       +----------------------+                       |
|                                    |                                  |
|                        (NEW, read-only, same files)                  |
|                                    v                                  |
|                        +-----------------------+                     |
|                        | services/importer/    |  NEW                |
|                        | cmd/import-legacy     |                     |
|                        +-----------+-----------+                     |
|                                    |                                  |
|                       internal/legacy (adapter)                      |
|                                    v                                  |
|                       internal/ingest (generic pipeline)             |
|                                    v                                  |
|                          internal/dbgen (sqlc-generated)              |
|                                    v                                  |
|                       +----------------------+                       |
|                       | Postgres (compose)   |  NOW POPULATED        |
|                       | armwrestling-math db |                       |
|                       +----------------------+                       |
+---------------------------------------------------------------------+
```

Named `services/importer/` (not bare `importer/`) to leave room for
`services/api/` in a later slice, without a restructure.

## 3. Target-state component diagram (services/importer internals)

```
+---------------------------------------------------------------+
| services/importer                                             |
|                                                                  |
|  cmd/import-legacy/main.go                                      |
|      | reads env: DATABASE_URL, LEGACY_EVIDENCE_PATHS           |
|      v                                                          |
|  internal/legacy                          internal/ingest       |
|  +----------------------+            +------------------------+ |
|  | model.go             |            | batch.go (canonical     | |
|  | evidence_v1.go       |   ------>  |   types: IngestBatch,   | |
|  | evidence_expanded.go |   Batch    |   AthleteInput,         | |
|  | normalize.go         |            |   MatchInput,           | |
|  |   (alias map,        |            |   SourceInput,          | |
|  |    timestamp parse,  |            |   ClaimInput)           | |
|  |    subject inference)|            | validate.go              | |
|  | adapter.go           |            | run.go (tx, upserts,     | |
|  +----------------------+            |   run lifecycle)         | |
|                                       +-----------+-------------+ |
|                                                     |               |
|                                                     v               |
|                                          internal/dbgen (sqlc)      |
|                                                     |               |
+-----------------------------------------------------|---------------+
                                                        v
                                                 PostgreSQL
```

## 4. Sequence diagram — import run lifecycle

```
main.go        legacy.Adapter    ingest.Validate    ingest.Run          Postgres
  |                  |                  |                 |                  |
  |--BuildBatch()--->|                  |                 |                  |
  |<--IngestBatch-----|                  |                 |                  |
  |                                      |                 |                  |
  |--Validate(batch)-------------------->|                 |                  |
  |<--ok / []error-----------------------|                 |                  |
  |   (abort here, no DB touched, if any reference fails to resolve)          |
  |                                                        |                  |
  |--Run(ctx, batch)-------------------------------------->|                  |
  |                                                        |--INSERT ingestion_runs (status=running)-->|
  |                                                        |<--run_id------------------------------------|
  |                                                        |--BEGIN--------------------------------------->|
  |                                                        |--UPSERT athletes (loop)------------------------>|
  |                                                        |--UPSERT match (by natural_key)------------------>|
  |                                                        |--LINK match_competitors--------------------------->|
  |                                                        |--UPSERT sources (loop)------------------------------>|
  |                                                        |--UPSERT claims + LINK claim_subjects (loop)------------>|
  |                                                        |--UPDATE ingestion_runs (status=completed, summary)-------->|
  |                                                        |--COMMIT------------------------------------------------------>|
  |<--Result{runID, counts}--------------------------------|                  |
  |                                                        |                  |
  |          == on any error inside the BEGIN..COMMIT span ==                |
  |                                                        |--ROLLBACK---------------------------------------------------->|
  |                                                        |--UPDATE ingestion_runs (status=failed, error_message)         |
  |                                                        |    [new statement, issued after rollback, tx is dead]-------->|
  |<--error-------------------------------------------------|                  |
```

Success is recorded transactionally (last statement before COMMIT).
Failure cannot be — rollback undoes it — so it's a compensating statement
issued afterward against a live connection. This asymmetry is intentional,
not an oversight.

## 5. ER diagram — target schema

```
athletes                        matches                          sources
+----+----------------+         +----+----------------+          +----+--------------------------+
| id | canonical_name |         | id | natural_key     |          | id | source_type, external_id |
+----+----------------+         |    | label, arm      |          |    | url, title, published_at |
      ^   ^                     |    | scheduled_at     |          |    | raw_payload jsonb         |
      |   |                     +----+----------------+          +----+--------------------------+
      |   |                           ^                                  ^
      |   +---- match_competitors ----+                                  |
      |         (match_id, athlete_id)                                   |
      |                                                                   |
      +---- claim_subjects                                                |
            (claim_id, athlete_id)                                        |
                  ^                                                       |
                  |                                                       |
                claims  ------------------------------------- source_id --+
                +----+-----------------------+
                | id | source_id (FK)        |
                |    | match_id (FK)         |
                |    | claim_text            |
                |    | timestamp_seconds     |
                |    | speaker, confidence   |
                |    | relevance             |
                |    | observed_at           |
                |    | extracted_at          |
                |    | extraction_model      |
                |    | raw_payload jsonb     |
                +----+-----------------------+
                UNIQUE (source_id, coalesce(timestamp_seconds, -1), claim_text)

ingestion_runs (standalone in v1 -- no FK from claims/sources; see decision G)
+----+-----------+--------+------------+---------------+
| id | batch_key | status | started_at | summary jsonb |
+----+-----------+--------+------------+---------------+
```

`created_by_run_id` deliberately omitted from `sources`/`claims` (decision
G): a source can be encountered by many runs, so "created by" would only
ever capture the first one, which is misleading. `ingestion_runs.summary`
(populated on completion, e.g. `{"athletes":2,"sources":16,"claims":115}`)
gives run-level visibility without per-row lineage. Per-row lineage
(`ingestion_run_sources`/`ingestion_run_claims` join tables) is the correct
design if/when exact lineage becomes necessary — explicitly deferred, not
forgotten.

## 6. Migration DDL

```sql
create table athletes (
    id             bigserial primary key,
    canonical_name text not null,
    created_at     timestamptz not null default now(),
    constraint athletes_canonical_name_key unique (canonical_name)
);

create table ingestion_runs (
    id            bigserial primary key,
    batch_key     text not null,
    status        text not null default 'running'
                    constraint ingestion_runs_status_check
                    check (status in ('running','completed','failed')),
    started_at    timestamptz not null default now(),
    finished_at   timestamptz,
    error_message text,
    summary       jsonb
);

create table matches (
    id           bigserial primary key,
    natural_key  text not null,
    label        text,
    arm          text not null,
    scheduled_at timestamptz,
    created_at   timestamptz not null default now(),
    constraint matches_natural_key_key unique (natural_key)
);

create table match_competitors (
    match_id   bigint not null references matches(id) on delete cascade,
    athlete_id bigint not null references athletes(id) on delete restrict,
    primary key (match_id, athlete_id)
);

create table sources (
    id            bigserial primary key,
    source_type   text not null,
    external_id   text not null,
    url           text not null,
    title         text,
    published_at  timestamptz,
    raw_payload   jsonb not null default '{}',
    created_at    timestamptz not null default now(),
    constraint sources_source_type_external_id_key unique (source_type, external_id)
);

create table claims (
    id                bigserial primary key,
    source_id         bigint not null references sources(id) on delete restrict,
    match_id          bigint not null references matches(id) on delete restrict,
    claim_text        text not null,
    timestamp_seconds integer,
    speaker           text,
    confidence        text,
    relevance         text,
    observed_at       timestamptz,
    extracted_at      timestamptz not null,
    extraction_model  text,
    raw_payload       jsonb not null default '{}',
    created_at        timestamptz not null default now()
);

create unique index claims_dedupe_key
    on claims (source_id, coalesce(timestamp_seconds, -1), claim_text);

create table claim_subjects (
    claim_id   bigint not null references claims(id) on delete cascade,
    athlete_id bigint not null references athletes(id) on delete restrict,
    primary key (claim_id, athlete_id)
);
```

## 7. Canonical ingest models

```go
type IngestBatch struct {
    BatchKey string

    Athletes []AthleteInput
    Match    MatchInput
    Sources  []SourceInput
    Claims   []ClaimInput
}

type AthleteInput struct {
    Key           string
    CanonicalName string
}

type MatchInput struct {
    Key         string     // batch-local reference key, e.g. "ermes-vs-morozov-2026"
    NaturalKey  string     // DB unique key, adapter-computed -- see below
    Label       string
    Arm         string
    ScheduledAt *time.Time
    Competitors []string
}

type SourceInput struct {
    Key         string
    SourceType  string
    ExternalID  string
    URL         string
    Title       *string
    PublishedAt *time.Time
    RawPayload  json.RawMessage
}

type ClaimInput struct {
    SourceKey        string
    MatchKey         string
    SubjectKeys      []string   // 0, 1, or 2 -- never defaulted to "both"
    Text             string
    TimestampSeconds *int
    Speaker          *string
    Confidence       *string
    Relevance        *string    // added: present on 100% of real claims
    ObservedAt       *time.Time
    ExtractedAt      time.Time
    ExtractionModel  *string
    RawPayload       json.RawMessage
}
```

Changes from the original sketch: `MatchInput.NaturalKey` added (the
generic pipeline trusts it verbatim as the DB unique key; it has no idea
how to construct a good one — that's adapter domain knowledge).
`ClaimInput.Relevance` added. No `SourceURL` field on `ClaimInput` — fully
derivable from `source.url` + `timestamp_seconds`, and the original value
is preserved in `RawPayload` regardless, so nothing is lost by not storing
it a second time.

### Match natural key (decision B)

Rematch-safe: `{scheduled_period}:{athlete_a_slug}:{athlete_b_slug}:{arm}`,
athlete slugs sorted alphabetically (order-independent), e.g.:

```
2026-06:artyom-morozov:ermes-gasparini:right
```

`scheduled_period` uses the coarsest granularity actually known — the
legacy data only says "June 2026," not a specific day, so `2026-06` is
used rather than fabricating a false-precision date like `2026-06-15`. If
`MatchInput.ScheduledAt` is later populated with an exact date, the
natural key should use the full date instead. Known limitation: `matches.
scheduled_at` will be `NULL` for the v1 import (see verification step 6) —
the "claims whose source was published before match time" query returns
zero rows until a real date is entered, which is expected, not a bug.

### Claim-subject inference (decision F)

Nothing in the legacy claim JSON has a structured "this claim is about
Ermes" field. Rather than tagging every claim with both athletes (which
would make "claims by athlete" meaningless), the adapter does a small
hardcoded text match against claim text, speaker, and relevance:

```go
var athleteAliases = map[string]string{
    "ermes gasparini": "ermes",
    "ermes":            "ermes",
    "artyom morozov":   "morozov",
    "artem morozov":    "morozov", // observed typo variant in real data
    "morozov":          "morozov",
    "steelmorozov":     "morozov", // observed handle in real data
}

func inferSubjects(text, speaker, relevance string) []string {
    haystack := strings.ToLower(text + " " + speaker + " " + relevance)
    found := map[string]bool{}
    for alias, key := range athleteAliases {
        if strings.Contains(haystack, alias) {
            found[key] = true
        }
    }
    keys := make([]string, 0, len(found))
    for k := range found {
        keys = append(keys, k)
    }
    sort.Strings(keys)
    return keys // may be empty, one, or both
}
```

Known limitation: pronoun-only claims ("He was very happy about his win")
won't match any name and get zero subjects. Acceptable — the instruction
was explicitly to allow zero when uncertain, not to force a guess.

## 8. Commit-by-commit breakdown

| # | Commit | Files | Linear |
|---|---|---|---|
| 1 | `db: add init migration for ingestion v1 schema` | `db/migrations/0001_init.sql` | MPI-6 |
| 2 | `ingest: add sqlc config and generated query code` | `services/importer/sqlc.yaml`, `db/queries/*.sql`, `services/importer/internal/dbgen/**` (generated, committed) | MPI-7 |
| 3 | `ingest: add canonical IngestBatch types and validation` | `services/importer/internal/ingest/batch.go`, `validate.go` + tests | MPI-8 |
| 4 | `ingest: add generic ingestion pipeline` | `services/importer/internal/ingest/run.go` + tests against compose Postgres with a fixture batch | MPI-9 |
| 5 | `legacy: add Ermes-Morozov JSON adapter` | `services/importer/internal/legacy/*.go` + tests against the real committed JSON, no DB | MPI-10 |
| 6 | `cmd: add import-legacy entry point` | `services/importer/cmd/import-legacy/main.go`, `go.mod`/`go.sum` | MPI-11 |
| 7 | *(next slice)* `deploy: add importer Dockerfile` | `services/importer/Dockerfile` | not filed yet |

Each commit is independently reviewable: 1–2 are pure SQL/generated code,
3 has no DB or JSON dependency, 4 has no legacy-JSON dependency, 5 has no
DB dependency, 6 is the first point everything is wired together.

## 9. Verification plan

No UI in this slice, so no Playwright — verification is CLI + direct SQL.

1. `docker compose up -d postgres`, wait for healthy.
2. Apply `db/migrations/0001_init.sql`; confirm via `\d claims` that the
   expression unique index exists.
3. `go run ./cmd/import-legacy` (first run), exit code 0, then:
   - `select count(*) from athletes;` → `2`
   - `select count(*) from matches;` → `1`
   - `select count(*) from match_competitors;` → `2`
   - `select count(*) from sources;` → `16` (distinct video_ids across both files)
   - `select count(*) from claims;` → `115` (71 + 44; zero true cross-file
     duplicates confirmed during repo audit)
   - `select count(*) from claim_subjects;` → report actual count (not
     asserted in advance — depends on text-match results)
4. Run `go run ./cmd/import-legacy` a **second time**: all counts above
   identical (no growth); `select count(*) from ingestion_runs;` → `2`,
   both rows `status='completed'`.
5. Failure-path check: point `DATABASE_URL` at an unreachable host, run
   again — process exits non-zero, latest `ingestion_runs` row has
   `status='failed'` with a non-null `error_message`, and claim/source
   counts are unchanged from step 4 (nothing partially written).
6. Spot-check expected queries:
   - `select claim_text from claims c join claim_subjects cs on cs.claim_id=c.id join athletes a on a.id=cs.athlete_id where a.canonical_name='Ermes Gasparini' limit 5;`
   - `select c.claim_text from claims c join sources s on s.id=c.source_id where s.published_at < (select scheduled_at from matches limit 1);`
     → expected `0` rows in v1, since `matches.scheduled_at` is `NULL`
     (known limitation, see §7).

## 10. Summary of resolved open decisions

| # | Decision |
|---|---|
| A | `services/importer/` (leaves room for `services/api/` later) |
| B | Rematch-safe `natural_key`, adapter-constructed, month-granularity for now |
| C | Expression unique index for claims dedupe, as proposed |
| D | `Relevance` added to `ClaimInput` |
| E | No per-claim `source_url` column; preserved in `raw_payload` |
| F | Claim subjects via small hardcoded text-match heuristic; 0/1/2 allowed |
| G | No `created_by_run_id` on `sources`/`claims`; `ingestion_runs.summary jsonb` instead; per-row lineage join tables deferred |
| H | Generated sqlc package committed to git |
| I | docker-compose volume mount fixed (MPI-12, done, outside this contract) |
