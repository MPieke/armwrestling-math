---
linear_issue: MPI-24
status: proposed
---

# Contract MPI-24: Establish The Elo Baseline On The Real Dataset

## Scope

Makes the lockbox and rolling-origin protocols operational against real
data, and produces the first number the prediction track exists to
generate. Depends on MPI-23 (loaded matches to seed protocols from).

`seed_lockbox` (MPI-22) writes `train_match_ids = '{}'` by design — that
placeholder gets filled here, not fixed as a bug.

## 1. Current-State Architecture

```text
seed_lockbox(name, kind, event_ids)
   -> eval_folds row: train_match_ids='{}', test_match_ids=<lockbox matches>

get_or_create_rolling_origin_protocol(name, min_training_events)
   -> generates folds, no check that a lockbox exists first
   -> nothing records WHY these folds exist (no spec column)

report: none -- psql only
prospective lockbox: created once, never grows
```

## 2. Target-State Architecture

### Schema

```text
eval_protocols (changed)
+-------------------+
| ...               |
| spec  jsonb   NN   |  new -- records what generated the folds:
+-------------------+     {event_slugs, freeze_date} for a lockbox,
                          {min_training_events} for rolling-origin
```

### seed_lockbox (changed)

```text
train_match_ids = every completed match from events with
                  held_on < min(held_on of the given lockbox events)
test_match_ids  = every completed match in the given lockbox events
                  (unchanged from MPI-22)
```

This is a real model fit target now: whatever family evaluates against the
lockbox trains on genuine pre-lockbox history.

### Ordering Guard

`get_or_create_rolling_origin_protocol`, when actually creating (not
returning an existing protocol by name), requires at least one
`eval_protocols` row with `kind like 'lockbox%'` to exist. Refuses with a
named error otherwise — a rolling-origin protocol created before any
lockbox exists would silently include lockbox events.

### New Commands

```text
prediction/seed_lockbox.py       CLI: --name --kind --event-slug (repeatable)
                                  Resolves slugs to event ids, calls the
                                  (changed) folds.seed_lockbox, records spec.

prediction/prospective.py        add-prospective-event --protocol-name
                                  --event-slug: appends that event's
                                  completed matches to test_match_ids on
                                  the existing single fold. Idempotent
                                  (checks membership before appending).

prediction/report.py             report --run-id: git_sha/dirty,
                                  hyperparams, metrics, and a per-fold
                                  breakdown reconstructed by checking
                                  which eval_folds.test_match_ids array
                                  contains each predicted match_id (no
                                  fold_index stored on run_predictions --
                                  avoids the redundant-denormalization the
                                  MPI-21 design deliberately avoided).
```

## 3. Test Plan Defined Before Implementation

### Integration (real PostgreSQL)

- seeding a lockbox from events after some earlier events produces a fold
  whose `train_match_ids` are exactly the completed matches from the
  earlier events, and no others
- `get_or_create_rolling_origin_protocol` raises a named error when no
  lockbox protocol exists; succeeds and excludes lockbox events once one
  does (regression test for the existing exclusion behavior, now gated)
- `add-prospective-event` appends only the given event's matches;
  running it twice does not duplicate ids in `test_match_ids`
- `report` output (metrics, per-fold match counts) matches direct SQL for
  the same run

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-24): add Elo baseline contract`
2. `test(MPI-24): define eval_protocols.spec and populated lockbox training` — red
3. `feat(MPI-24): add spec column, populate lockbox training set`
4. `test(MPI-24): define ordering guard, report, prospective growth` — red
5. `feat(MPI-24): add ordering guard, report, add-prospective-event`
6. `docs(MPI-24): record the first Elo baseline and protocol definitions` —
   `docs/architecture/prediction.md`; this commit also runs the real
   baseline against the loaded dataset per the operator's chosen lockbox
   events and freeze date (human decision, not this contract's to make)

## 5. Verification Plan

```sh
cd services/prediction
uv run ruff check . && uv run pytest --collect-only -q
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v

DATABASE_URL=... uv run python -m prediction.seed_lockbox \
  --name lockbox_retrospective_v1 --kind lockbox_retrospective \
  --event-slug <last-N-event-slugs>
DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --min-training-events <N>
DATABASE_URL=... uv run python -m prediction.report --run-id <id>
```
