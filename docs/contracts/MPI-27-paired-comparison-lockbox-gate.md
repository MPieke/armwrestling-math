---
linear_issue: MPI-27
status: proposed
---

# Contract MPI-27: Paired Comparison And Lockbox Gate

## Scope

Two commands: `compare` (dev-fold statistical comparison between two runs)
and `evaluate-lockbox` (the rare, gated, one-shot check). No migrations —
every fact `evaluate-lockbox` needs to report "how many times has this
lockbox been consulted" already exists as `experiment_runs` rows against
that protocol; no new tracking table is needed.
Depends on MPI-30 so comparisons can report whether runs differ by model
family, feature schema, or both.

## 1. Current-State Architecture

```text
Two runs on the same protocol each have a point-estimate metrics jsonb.
Nothing compares them. Nothing prevents evaluating a lockbox protocol
via the ordinary run_baseline path, and nothing counts how many times
it has been.
```

At n≈300, per the project's own earlier analysis, two independent point
estimates ~5pp apart are not distinguishable from noise — comparing them by
eye is the mistake this ticket exists to prevent.

## 2. Target-State Architecture

### `compare(connection, run_id_a, run_id_b, match_ids=None)`

```text
1. refuse if the two runs' protocol_id differ
2. join run_predictions for both runs on match_id, restricted to the
   canonical athlete_a side (v_completed_matches ordering) so "correct"
   is well-defined without an arbitrary per-run choice
3. optionally restrict to `match_ids` (MPI-28 needs this: evidence-
   covered matches only -- on uncovered matches C reduces to B exactly,
   so an unrestricted comparison would say nothing)
4. McNemar's exact test (binomial on discordant pairs) on accuracy
5. paired bootstrap CI (resample matches with replacement) on the
   log-loss difference -- the primary verdict, since it uses the full
   probability, not just the thresholded pick
6. verdict: "distinguishable" iff the bootstrap CI on the log-loss
   difference excludes zero; McNemar reported alongside as a
   corroborating, accuracy-specific view, not the primary criterion
```

`compare` must print the exact evaluated subset: both run ids, shared
protocol id/name, whether all predictions or an explicit `match_ids` subset
was used, the resulting match ids/count, and each run's promotability. Its
JSON output contains the same data and the paired statistics. This prevents
a statistically valid-looking comparison from being manually interpreted as
covering a different population than it actually did.

Exact binomial McNemar rather than the chi-square approximation: sample
sizes here are small enough (dozens of discordant pairs, not hundreds) that
the continuity-corrected approximation is unreliable.

### `evaluate-lockbox(connection, protocol_id, model_family, ...)`

```text
1. refuse outright if the working tree is dirty -- stricter than the
   ordinary dev path, which records git_dirty and lets a human judge
   later. The lockbox is a scarce, non-renewable-within-a-session
   resource; spending it on an unreproducible run is a worse mistake
   than merely flagging one after the fact.
2. print "this protocol has been evaluated N times" where
   N = count(experiment_runs where protocol_id = this)  -- before running
3. run the ordinary run_baseline machinery against this protocol_id
4. print the count again, now N+1
```

`evaluate-lockbox` must print the protocol identity, its materialized
train/test membership counts, and the consultation count before and after
the run. It supports `--dry-run` to perform every guard and display what it
would evaluate without inserting a run or consuming a lockbox consultation.

### Promotability

`is_promotable` (MPI-22) is enforced here, not just defined: `compare`
labels a `git_dirty=true` run "not a promotion candidate" in its output;
`evaluate-lockbox` refuses one outright (above).

## 3. Test Plan Defined Before Implementation

### Unit (statistics, synthetic data — no database)

- two identical prediction sets: McNemar reports no discordant pairs,
  bootstrap CI on the log-loss difference includes zero, verdict "not
  distinguishable"
- a deliberately large, consistent gap (one predictor always right, the
  other always wrong): verdict "distinguishable"
- bootstrap CI width shrinks as n grows, at fixed effect size (sanity check
  on the resampling implementation itself)

### Integration

- `compare` refuses two runs on different protocols
- `compare` with `match_ids` restricts correctly and reports the resulting n
- `evaluate-lockbox` refuses when the working tree is dirty (simulated via
  an uncommitted test file) without touching the ledger
- `evaluate-lockbox`'s reported count increments by exactly one per call
- `compare` reports the exact restricted match-id set/count and both runs'
  promotability; `evaluate-lockbox --dry-run` performs no ledger write

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-27): add paired comparison and lockbox gate contract`
2. `test(MPI-27): define paired comparison statistics` — red
3. `feat(MPI-27): add compare`
4. `test(MPI-27): define the lockbox evaluation gate` — red
5. `feat(MPI-27): add evaluate-lockbox`
6. `docs(MPI-27): document the comparison and lockbox discipline`

## 5. Verification Plan

```sh
cd services/prediction
uv run pytest -v -m "not integration"
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration

DATABASE_URL=... uv run python -m prediction.compare --run-a <elo-run> --run-b <glicko2-run>
DATABASE_URL=... uv run python -m prediction.evaluate-lockbox \
  --protocol-name lockbox_retrospective_v1 --model-family elo
DATABASE_URL=... uv run python -m prediction.evaluate-lockbox \
  --protocol-name lockbox_retrospective_v1 --model-family elo --dry-run
# confirm the printed look-count and that a dirty tree refuses before any query
```
