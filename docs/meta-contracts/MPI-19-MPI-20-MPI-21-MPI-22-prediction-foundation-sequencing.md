---
linear_issues: [MPI-20, MPI-19, MPI-21, MPI-22]
status: proposed
---

# Meta-Contract: Prediction Track Foundation Sequencing

This is not a software-change contract on its own — it adds no behavior and
defines no tests. It sequences four already-written contracts (MPI-20, MPI-19,
MPI-21, MPI-22), each of which remains the authority on its own scope, tests,
and verification. This document only answers two questions: in what order,
and under what conditions may the next one begin.

Deviates intentionally from the single-ticket contract-naming convention
(multiple ticket codes, no single `linear_issue`) because its subject is the
relationship between four tickets, not the implementation of one.

## Dependency Graph

```text
MPI-20 --> MPI-19 --> MPI-21 --> MPI-22
(fresh DB)  (outcomes/  (ledger    (Elo baseline +
             events)     schema)    rolling-origin runner)
```

Fully linear — no pair in this batch may run in parallel.

## Why It's Linear, Not Just "Because Blocked-By Says So"

Two independent forcing reasons, not one:

1. **Logical**: each ticket's schema or code reads something the previous
   one creates (MPI-19 needs a running fresh instance; MPI-21's fold rows are
   meaningless without matches/events; MPI-22 computes ratings from MPI-19's
   outcome columns via MPI-21's ledger).
2. **Mechanical**: MPI-19, MPI-21, and MPI-22 (via its own migration) all add
   the next numbered file under `db/migrations` and regenerate the same
   `internal/dbgen` package. Two of these developed on divergent branches at
   once would collide on migration numbering and produce a generated-code
   diff neither branch actually tested against. This forces serialization
   even where the logical dependency alone might have been looser.

## Gate Conditions

Each gate is a subset of its predecessor's own verification plan — restated
here only as the single condition that must hold, not the full procedure.

**MPI-20 → MPI-19**
The fresh `postgres` service is up, empty (no relations), and migrations
`0001`–`0002` apply to it cleanly. The legacy instance is confirmed to still
hold its original data under `postgres-legacy` before the cutover is treated
as complete.

**MPI-19 → MPI-21**
Migration `0003` is merged to `main`, `dbgen` regenerated and committed, and
MPI-19's integration suite (result persistence, replay, natural-key
determinism) is green against the fresh instance. `eval_folds` rows would be
meaningless without real `matches`/`events` to reference.

**MPI-21 → MPI-22**
Migration `0004` is merged to `main`, `dbgen` regenerated and committed, and
MPI-21's constraint/cascade tests are green. `run_baseline.py` has nowhere to
write until `experiment_runs`/`run_predictions`/`run_models` exist.

## Parallelism Policy

General rule, for this batch and any future addition to it: a ticket may
start immediately, without waiting, if it depends on nothing not yet merged
**and** touches neither `db/migrations` nor `internal/dbgen`. Two such
tickets may run concurrently.

None of the four in this batch qualify — the chain above is exhaustive. An
example of what would qualify, for calibration: the ArmSport API feasibility
spike (deferred, not part of this batch) touches no schema and depends on
nothing here, so it could run before, during, or after any of these four with
no coordination required.

## Execution Model

Once all four contracts are approved, each proceeds through its own
commit-by-commit breakdown and verification plan in full — including running
the thermo-nuclear-code-quality-review skill on its diff and fixing blocking
findings — before merging and starting the next. No check-in between tickets
unless a verification step fails or a gate condition above does not hold.
