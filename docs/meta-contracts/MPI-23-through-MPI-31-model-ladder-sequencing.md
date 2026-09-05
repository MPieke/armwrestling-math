---
linear_issues: [MPI-23, MPI-24, MPI-25, MPI-26, MPI-27, MPI-28, MPI-29, MPI-30, MPI-31]
status: proposed
---

# Meta-Contract: Model Ladder And Evidence-Corpus Sequencing

Sequences nine tickets that take the prediction track from "runner exists"
to an inspectable ladder of approaches compared honestly against each other.
MPI-30 makes model inputs reproducible and explainable; MPI-31 acquires the
dated evidence corpus that MPI-28 needs. Each ticket remains the authority on
its own scope, tests, and verification; its per-ticket contract
(`docs/contracts/MPI-<n>-*.md`) is that ticket's first commit. This document
only fixes order, gates, and parallelism.

## Guiding Rule

Every model ticket delivers **one baseline and a ledger entry**, not a set of
variants. Iteration happens afterward through hypotheses recorded in the
ledger (`experiment_runs.hypothesis`, `parent_run_id`) — human-driven now,
MPI-17's agent later. MPI-30 adds the other required separation: canonical
facts, a versioned feature schema, and a model family are independent axes.
An experiment can therefore test a model change, a representation change, or
both, with persisted inputs proving which occurred.

## The Ladder

```text
P  input provenance                 named feature schema + immutable inputs
A  results-only rating systems      Elo (done) · Glicko-2 · Bradley-Terry
B  point-in-time feature models     LogReg · TabPFN · rating priors
C  evidence corpus + features v1    match-centric corpus, then one encoding
D  LLM direct predictor             prospective lockbox ONLY
```

## Dependency Graph

```text
MPI-23 loader ──> MPI-30 input provenance ──> MPI-24 Elo ──> MPI-25 families ──┬──> MPI-26 features ──┐
                                                                                 │                      ├──> MPI-28 evidence v1 ──> MPI-29 LLM
                                                                                 └──> MPI-27 compare ───┘
    |
    `──> MPI-31 evidence corpus ────────────────────────────────────────────────> MPI-28

Migration sequence: MPI-23 -> MPI-30 -> MPI-24 -> MPI-26 -> MPI-28 -> MPI-29
```

## Gate Conditions

Each gate is the single condition that must hold, restated from the
predecessor's verification plan.

**MPI-23 → MPI-30**: migrations for `weight_class` and `match_videos`
merged; the hand-crafted CSV loads idempotently into the fresh instance;
`v_completed_matches` exposes `weight_class`.

**MPI-30 → MPI-24**: a named/versioned feature schema, immutable per-fold
model inputs, `report`, and `explain-prediction` exist. The inspection
commands reproduce persisted inputs without refitting, writing, or contacting
a provider.

**MPI-24 → MPI-25**: a lockbox protocol is seeded with a non-empty training
set; a rolling-origin protocol exists that excludes it; one real Elo run is
in the ledger with `git_dirty = false`; `report` prints it.

**MPI-25 → MPI-26, MPI-27**: the model interface is merged with Elo behind
it producing identical predictions to before; Glicko-2 reproduces Glickman's
worked example.

**MPI-23 → MPI-31**: the target source-match corpus and known video IDs are
loaded. The read-only coverage preflight completes before the operator
approves the exact OpenAI batch cost.

**MPI-26 + MPI-27 + MPI-31 → MPI-28**: point-in-time feature builder's
leakage test is green; `compare` supports subset mode; and MPI-31 has a
reconciled corpus manifest with terminal status for every selected source
match/video, including publication-date coverage and retained failures.

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
this order: **23 → 30 → 24 → 26 → 28 → 29**. MPI-30 adds the tier-2
feature-schema/input-manifest tables. MPI-29's contract resolved its
rationale-storage question to a dedicated `run_match_rationale` table, so it
is migration-touching after all. Migration-free: **25, 27, 31**.

Concretely: **31 may prepare its corpus manifest in parallel with 30** after
MPI-23 is merged, but its paid batch still requires the separate cost gate.
**27 may run in parallel with 26** once 25 is merged. No other implementation
parallelism is permitted in this batch.

## Human Decisions Embedded In The Batch

Not the tickets' to make; the CLIs take them as inputs.

1. Which events form the retrospective lockbox and the freeze date (MPI-24).
2. The selected source-match/video coverage target and approval of its API
   cost (MPI-31).
3. The ~20-concept vocabulary for claim annotation (MPI-28).
4. Which LLM and whether to include evidence in its packet (MPI-29).

## Execution Model

Each ticket: contract first (four parts, per repository guidance), test-first
commits, real-PostgreSQL verification, the thermo-nuclear-code-quality-review
skill applied to the diff with blocking findings fixed, then merge and move
on. No check-in between tickets unless a gate above fails or a human
decision is needed.
