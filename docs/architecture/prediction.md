# Prediction Architecture

## Purpose And Scope

The prediction track answers "how well can we predict match outcomes, and
what data makes that better." It is a separate concern from ingestion (which
gets matches, athletes, and evidence into PostgreSQL) that happens to read
from the same database.

## Ownership Boundary

```text
services/importer (Go)          owns canonical writes: events, athletes,
                                 matches, outcomes, evidence

experiment ledger (tier 2)      eval_protocols, eval_folds, experiment_runs,
                                 run_predictions, run_models -- written
                                 directly by whatever computes and evaluates
                                 a prediction approach, not through Go's
                                 sqlc-generated query layer
```

No `db/queries/*.sql` entry or Go business logic references the tier-2
tables (MPI-21). This is deliberate: trying a new feature set or model
should never require a schema migration or an `sqlc` regeneration, which is
what a canonical-layer round trip would otherwise force on every experiment
iteration. `db/migrations` remains the single schema authority for the whole
database regardless of which component writes to a given table.

## Experiment Ledger Data Model

```text
eval_protocols                    eval_folds
+------------------+              +---------------------------+
| id               |<-------------| protocol_id           FK  |
| name           U |              | fold_index                |
| kind             |              | train_match_ids  bigint[] |
| created_at       |              | test_match_ids   bigint[] |
+------------------+              +---------------------------+
                                     PK(protocol_id, fold_index)

experiment_runs
+---------------------+
| id                  |
| git_sha, git_dirty  |
| protocol_id     FK  |----> eval_protocols
| feature_spec  jsonb |
| model_family        |
| hyperparams   jsonb |
| seed                |
| parent_run_id   FK  |----> experiment_runs (self, nullable)
| hypothesis          |
| status, metrics     |
+---------------------+
        |                          |
        v                          v
run_predictions              run_models
  (run_id, match_id,           (run_id, params jsonb)
   athlete_id, p_win)
```

Three deliberate omissions, and why:

- **No `datasets`/`feature_specs` table with content hashes.** A dataset's
  shape varies per experiment, but its *code* is already pinned by
  `experiment_runs.git_sha`; a separate hashing layer would duplicate that.
- **No stored model artifact.** The candidate model families (Elo,
  Bradley-Terry, logistic regression) are deterministic given `git_sha` +
  input data + `seed`; `run_models.params` keeps coefficients/importances
  for inspection, but the fitted model object itself is recomputable rather
  than stored.
- **No separate lockbox table.** A lockbox is an `eval_protocols`/
  `eval_folds` row like any other, distinguished only by `kind`
  (`lockbox_retrospective` / `lockbox_prospective`), not a parallel
  mechanism for the same underlying concept: materialized train/test match
  membership.

`eval_folds` membership is materialized at creation time, never re-derived
from a rule such as "matches after date X" — a rule-based definition would
silently grow as ingestion adds matches, breaking comparability between runs
scored against "the same" protocol months apart.

## services/prediction (MPI-22)

The first component to write to the ledger. Python, sibling to
`services/importer`, with its own `pyproject.toml`/`uv.lock`.

```text
db.py            reads events and v_completed_matches only -- never
                 matches/match_competitors directly. This is the boundary:
                 Go can change how outcomes are stored underneath without
                 breaking this service, and "what counts as a usable
                 completed match" has exactly one definition.

elo.py           pure fit/predict, no database dependency

folds.py         generate_rolling_origin (pure, over db.py's lists) and
                 seed_lockbox (writes -- which events go in a lockbox is a
                 deliberate human decision made at seeding time)

metrics.py       pure: accuracy, log-loss, Brier score, Wilson interval

run_baseline.py  composition root; the only module that opens a
                 connection and commits
```

### v_completed_matches

```sql
create view v_completed_matches as
select m.id as match_id, m.event_id, m.scheduled_at, m.arm,
       mc_a.athlete_id as athlete_a_id, mc_b.athlete_id as athlete_b_id,
       mc_a.result as result_a
from matches m
join match_competitors mc_a on mc_a.match_id = m.id
join match_competitors mc_b on mc_b.match_id = m.id and mc_b.athlete_id > mc_a.athlete_id
where m.status = 'completed';
```

One row per completed match, `athlete_a_id < athlete_b_id` (a strict
ordering from the self-join condition, not source-data order), excludes
`scheduled`/`dq`/`no_contest`.

### The non-negotiable rule: refit per fold, never reused

`run_baseline.py` calls `elo.fit` fresh for every fold, using only that
fold's `train_match_ids`. Ratings from one fold are never carried into the
next. This is the leakage guardrail the whole rolling-origin design exists
to enforce: a rating fit once over the entire match history would let every
athlete's ability be influenced by matches that happen after any given match
being evaluated against it, silently invalidating every fold's result.
`get_or_create_rolling_origin_protocol` additionally excludes any event
already referenced by a lockbox protocol's folds, so a lockbox can never
leak into a dev protocol's training set either.

## Related Contracts

- `docs/contracts/MPI-19-match-outcome-and-event-schema.md` — outcome data
  this track reads.
- `docs/contracts/MPI-21-experiment-ledger-schema.md` — this schema.
- `docs/contracts/MPI-22-elo-baseline-rolling-origin-runner.md` — the first
  component to write to it.
