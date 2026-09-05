---
linear_issue: MPI-31
status: proposed
---

# Contract MPI-31: Build The Evaluation Evidence Corpus

## Scope

Use MPI-16's existing `cmd/ingest-youtube` pipeline to turn the historical
canonical match corpus loaded by MPI-23 into a traceable evidence corpus for
MPI-28. This is an operational data-acquisition ticket: it changes no Go or
Python behavior and performs no schema migration.

Each video is ingested for its own canonical source match. Every
`claim_subjects.athlete_id` remains a participant of that source match;
style-based search, athlete-style profiles, and transitive retrieval are out
of scope. The paid OpenAI batch is a hard gate: no provider call may occur
until the operator explicitly approves the selected match/video set and cost.

## 1. Current-State Architecture

```text
MPI-23 results                         MPI-16 pipeline
events -> matches -> match_videos      ingest-youtube --match-natural-key
                    (known ID optional)              |
                                                      v
                                               yt-dlp -> ffmpeg -> OpenAI
                                                      |
                                                      v
sources -> source_extractions -> claims -> claim_subjects

No target corpus, coverage manifest, or repeatable batch operation exists.
```

The canonical audit tables `ingestion_runs`, `sources`,
`source_extractions`, `claims`, and `claim_subjects` already record the
ingestion result. This ticket neither changes nor bypasses them.

## 2. Target-State Architecture

```text
Versioned corpus manifest
  natural key, event, video IDs, discovery eligibility, terminal status,
  ingestion run ID, published_at presence, claim/subject counts, failure
                              |
                              v
read-only preflight --> explicit cost approval --> existing ingest-youtube
                                                        |
                                                        v
                                                existing evidence audit tables
                              |
                              v
incremental runbook for newly loaded source matches and videos
```

The corpus manifest has one row per selected canonical source match/video and
uses terminal statuses `completed`, `skipped_existing`, `failed`, or
`no_video_found`. It records failures without stopping later rows. It also
records whether `sources.published_at` is known; MPI-28's selector will
exclude unknown or too-late source dates rather than infer them.

The initial target is the historical source matches needed to give athletes
in the evaluation corpus prior-match evidence coverage—not solely the later
prediction-target matches. It remains bounded by the loaded canonical match
corpus. Wider third-party corpus acquisition for style-transitive features is
a future ticket.

### Batch Sequence

```text
operator -> preflight: enumerate canonical source-match/video coverage
operator -> approve: exact count and provider cost
operator -> existing ingest-youtube: one source match at a time
ingest-youtube -> PostgreSQL: existing audit, source, extraction, claim rows
operator -> reconciliation: manifest status/counts from PostgreSQL
MPI-28 -> reads only dated canonical claims through its own selector
```

## 3. Commit-by-Commit Breakdown

1. `docs(MPI-31): add evidence corpus contract`
   - Files: this contract and `docs/contracts/MPI-28-evidence-features-v1.md`.
   - Makes corpus acquisition an explicit MPI-28 prerequisite.
   - Reviewable alone: no runtime or provider behavior changes.
2. `docs(MPI-31): add evidence corpus manifest and runbook`
   - Files: `docs/evidence-corpora/README.md`, an initial manifest template,
     and `docs/runbooks/evidence-corpus-ingestion.md`.
   - Defines fields, read-only preflight/reconciliation queries, exact command
     shape, terminal statuses, and the incremental process.
   - Reviewable alone: operational documentation only; no provider call.
3. `docs(MPI-31): record approved initial evidence corpus batch`
   - Files: the named initial manifest and `docs/architecture/prediction.md`.
   - After separate cost approval, records selected rows, commands, run IDs,
     outcomes, coverage gaps, and claim counts.
   - Reviewable alone: auditable operation record using existing machinery.

## 4. Verification Plan

Preflight and reconciliation make no provider call:

```sh
psql "$DATABASE_URL" -c "
  select m.natural_key, e.slug,
         array_agg(mv.youtube_video_id) filter (where mv.youtube_video_id is not null) as video_ids,
         count(distinct s.id) as sources, count(distinct c.id) as claims
  from matches m
  join events e on e.id = m.event_id
  left join match_videos mv on mv.match_id = m.id
  left join sources s on s.source_type = 'youtube' and s.external_id = mv.youtube_video_id
  left join claims c on c.match_id = m.id
  group by m.id, e.slug order by e.held_on, m.natural_key;"

# Only after explicit approval, for every selected manifest row:
cd services/importer
go run ./cmd/ingest-youtube --match-natural-key '<natural-key>' --video-id '<youtube-id>'

psql "$DATABASE_URL" -c "
  select m.natural_key, s.external_id, s.published_at, count(c.id) as claims
  from matches m join claims c on c.match_id = m.id
  join sources s on s.id = c.source_id
  where s.source_type = 'youtube'
  group by m.natural_key, s.external_id, s.published_at
  order by m.natural_key, s.external_id;"
```

Before declaring the corpus ready for MPI-28, verify that every selected
manifest row has a terminal status; completed rows have the corresponding
existing audit/source/extraction/claim records; failed rows retain their
failure record; and publication-date coverage is reported, never assumed.
