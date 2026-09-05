---
linear_issue: MPI-28
status: proposed
---

# Contract MPI-28: Evidence Features V1

## Scope Change From The Linear Ticket

The ticket's scope included a dyad + "style-transitive" evidence option
(retrieving claims about *other* athletes who share a technique with the
opponent). Writing this contract surfaced that style-transitive retrieval
needs an athlete-level style/technique tag that doesn't exist anywhere yet
— the claim vocabulary tags individual *claims*, not athlete profiles. That
is real, valuable future work, but it is not this ticket's to invent as a
side effect. **v1 is dyad-only** (claims about either of the two athletes in
the match itself). Style-transitive retrieval is a follow-up once an
athlete-style table exists.

## Scope

One evidence encoding, evaluated honestly, not a set of variants. Depends
on MPI-23 (loaded matches), MPI-26 (a Tier B run to compare against), MPI-27
(subset-restricted `compare`).

### Prerequisite (operational, has API cost)

The fresh database has zero claims — the MPI-19-22 audit's second
by-design gap. Before this ticket produces anything: run `ingest-youtube`
for the loaded matches, using `match_videos` (MPI-23) as known video IDs
where available and the existing fixed-query search otherwise. Approve the
OpenAI/`yt-dlp` cost for the batch before running it; record what was
ingested in `docs/architecture/prediction.md`.

## 1. Current-State Architecture

```text
claims, sources, claim_subjects    exist (MPI-16), zero rows in the fresh DB
                                    no annotation, no vocabulary

services/prediction                reads only v_completed_matches;
                                    no path to claims at all
```

## 2. Target-State Architecture

### Claim Annotation (Go — claims are Go-owned canonical data)

```text
claim_annotations
+--------------------+
| id                 |
| claim_id       FK  |
| model              |
| prompt_version     |
| claim_type         |
| concepts    text[] |
| subject_athlete_id FK (nullable)
| arm                |
| temporality        |  current_form | recent_context | historical_event |
|                     |  durable_style | future_prediction |
|                     |  general_principle | unclear
| certainty          |  observed | self_reported | analyst_interpretation |
|                     |  community_narrative | unclear
+--------------------+
  unique (claim_id, model, prompt_version)
```

`temporality`/`certainty` reuse the vocabulary already sketched in
`scripts/evidence_dimension_models.py` during early discovery work, rather
than inventing a fresh one. `cmd/annotate-claims` (new Go command) follows
MPI-16's structured-output pattern exactly: Go type derives the schema sent
to OpenAI, response parsed back into that type, semantic validation before
persistence, idempotent per `(claim_id, model, prompt_version)`.

### Point-In-Time Selection (Python)

```python
def select_eligible_claims(connection, match: CompletedMatch) -> list[AnnotatedClaim]:
    """Claims about either athlete in `match`, from a source published
    strictly before match.scheduled_at. A null published_at is NEVER
    eligible -- the conservative default when a source's date is unknown."""
```

No new view: unlike `v_completed_matches` this is inherently parametrized
per match (needs the target's `scheduled_at` and both athlete ids), so it's
a direct parametrized query, not a flat view.

### Encoding V1 (fixed, not a menu)

```python
def encode_evidence(claims: list[AnnotatedClaim]) -> dict:
    return {
        "evidence_count": len(claims),
        "recent_injury_flag": ...,       # claim_type == 'injury' within 30d
        "technique_advantage_flag": ...,  # a matchup-favoring claim exists
    }
```

Pure function of the eligible set. Iteration beyond this is a ledger
hypothesis + a new run, not a v1 deliverable.

### Evaluation

`compare` (MPI-27) restricted to `match_ids` = matches with
`evidence_count > 0`, against the best Tier B run. Comparing on the full
set would dilute the signal with matches where C is mechanically identical
to B.

## 3. Test Plan Defined Before Implementation

### Go: Unit + Integration

- structured-output schema for annotation derives correctly and round-trips
  (MPI-16 pattern)
- semantic validation rejects an unrecognized `temporality`/`certainty`
- annotating the same claim with the same `(model, prompt_version)` twice
  does not duplicate rows

### Python: Unit

- **selection leakage test**: a claim from a source published at or after
  the match's `scheduled_at` is never eligible; a claim with null
  `published_at` is never eligible, even if every other field looks safe
- `encode_evidence` is a pure function: fixed input list -> fixed output,
  verified on hand-built fixtures including the empty-list case (matches
  MPI-22's "no evidence" majority)

### Integration

- a full evidence-v1 run against real (ingested) data produces a ledger
  entry; `compare` in subset mode reports the correct n (evidence-covered
  count) and a distinguishable/not verdict

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-28): add evidence features v1 contract`
2. `test(MPI-28): define claim_annotations schema` — red (Go)
3. `feat(MPI-28): add claim_annotations schema`
4. `test(MPI-28): define annotate-claims command` — red (Go)
5. `feat(MPI-28): add annotate-claims command`
6. `test(MPI-28): define point-in-time evidence selection` — red (Python)
7. `feat(MPI-28): add evidence selection`
8. `test(MPI-28): define evidence encoding v1` — red (Python)
9. `feat(MPI-28): add evidence encoding v1 and subset evaluation`
10. `docs(MPI-28): document the annotation layer, selection boundary, and
    the dyad-only v1 scope narrowing`

## 5. Verification Plan

```sh
# Operational prerequisite, cost-approved first:
cd services/importer
go run ./cmd/ingest-youtube --match-natural-key <key> [--video-id <id>]  # per loaded match

gofmt -l . && go vet ./... && go test -v -count=1 ./...
INGEST_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  go test -v -count=1 -tags integration ./...
go run ./cmd/annotate-claims

cd ../prediction
uv run pytest -v -m "not integration"
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration
DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --model-family evidence_v1
DATABASE_URL=... uv run python -m prediction.compare \
  --run-a <best-tier-b-run> --run-b <evidence-v1-run> --evidence-covered-only
```
