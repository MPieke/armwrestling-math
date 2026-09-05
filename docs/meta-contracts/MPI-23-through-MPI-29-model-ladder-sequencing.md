---
linear_issues: [MPI-23, MPI-24, MPI-25, MPI-26, MPI-27, MPI-28, MPI-29]
status: proposed
---

# Meta-Contract: Model Ladder Sequencing

Sequences seven tickets that take the prediction track from "runner exists"
to "a ladder of approaches compared honestly against each other." Each
ticket remains the authority on its own scope, tests, and verification; its
per-ticket contract (`docs/contracts/MPI-<n>-*.md`) is that ticket's first
commit. This document only fixes order, gates, and parallelism.

## Guiding Rule

Every ticket delivers **one baseline and a ledger entry**, not a set of
variants. Iteration happens afterward through hypotheses recorded in the
ledger (`experiment_runs.hypothesis`, `parent_run_id`) — human-driven now,
MPI-17's agent later. The one structural separation kept throughout is
*data/selection* apart from *encoding/model*, so the latter can change
without touching the former.

## The Ladder

```text
A  results-only rating systems      Elo (done) · Glicko-2 · Bradley-Terry
B  point-in-time feature models     LogReg · TabPFN · rating priors
C  evidence features v1             one encoding, evidence-covered subset
D  LLM direct predictor             prospective lockbox ONLY
```

## Dependency Graph

```text
MPI-23 loader ──> MPI-24 Elo baseline ──> MPI-25 families ──┬──> MPI-26 features ──┐
                                                            │                      ├──> MPI-28 evidence v1 ──> MPI-29 LLM predictor
                                                            └──> MPI-27 compare ───┘
MPI-23 ─────────────────────────────────────────────────────────────────────────> MPI-28 (migration order)
                                                                                     MPI-28 ──> MPI-29 (migration order, see below)
```

## Gate Conditions

Each gate is the single condition that must hold, restated from the
predecessor's verification plan.

**MPI-23 → MPI-24**: migrations for `weight_class` and `match_videos`
merged; the hand-crafted CSV loads idempotently into the fresh instance;
`v_completed_matches` exposes `weight_class`.

**MPI-24 → MPI-25**: a lockbox protocol is seeded with a non-empty training
set; a rolling-origin protocol exists that excludes it; one real Elo run is
in the ledger with `git_dirty = false`; `report` prints it.

**MPI-25 → MPI-26, MPI-27**: the model interface is merged with Elo behind
it producing identical predictions to before; Glicko-2 reproduces Glickman's
worked example.

**MPI-26 + MPI-27 (+ MPI-23) → MPI-28**: point-in-time feature builder's
leakage test is green; `compare` supports subset mode; and the operational
prerequisite has been done — evidence ingested for the loaded matches
(`ingest-youtube`, using `match_videos` IDs), cost approved first.

**MPI-25 + MPI-27 + MPI-28 (migration order) → MPI-29**: `compare` and the
lockbox-evaluation gate exist; a `lockbox_prospective` protocol exists
(MPI-24). MPI-28 is a logical soft-dependency (its selection layer is used
for the evidence packet if merged, a results-only packet is a valid v1
otherwise) but a **hard migration-order dependency**: MPI-29's contract
resolved rationale storage to its own `run_match_rationale` table, placing
it after MPI-28 in the shared migration sequence regardless of whether its
evidence packet is wired in.

## Parallelism

Rule (unchanged): a ticket may start if it depends on nothing unmerged
**and** touches neither `db/migrations` nor `internal/dbgen`.

Migration-touching tickets, which therefore serialize among themselves in
this order: **23 → 24 → 26 → 28 → 29**. MPI-29's contract resolved its
rationale-storage question to a dedicated `run_match_rationale` table, so
it is migration-touching after all — the earlier hedge in this document
("only if it chooses a details column") is settled: yes, it needs one.
Migration-free: **25, 27**.

Concretely: **27 may run in parallel with 26** once 25 is merged. That is
the only parallel pair in this batch — MPI-29 no longer qualifies, since it
now sits in the same migration sequence as 28.

## Human Decisions Embedded In The Batch

Not the tickets' to make; the CLIs take them as inputs.

1. Which events form the retrospective lockbox and the freeze date (MPI-24).
2. The ~20-concept vocabulary for claim annotation (MPI-28).
3. Approval of API cost for the evidence-ingestion prerequisite (MPI-28).
4. Which LLM and whether to include evidence in its packet (MPI-29).

## Execution Model

Each ticket: contract first (four parts, per repository guidance), test-first
commits, real-PostgreSQL verification, the thermo-nuclear-code-quality-review
skill applied to the diff with blocking findings fixed, then merge and move
on. No check-in between tickets unless a gate above fails or a human
decision is needed.
