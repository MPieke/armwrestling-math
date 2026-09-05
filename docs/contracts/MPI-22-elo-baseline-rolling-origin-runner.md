---
linear_issue: MPI-22
status: proposed
---

# Contract MPI-22: Elo Baseline And Rolling-Origin Runner

## Scope

**Depends on MPI-21** (experiment ledger schema) and transitively MPI-19/MPI-20.

Add the first prediction approach and the harness that scores it: an Elo
rating computed from canonical match outcomes, refit independently per
rolling-origin fold, evaluated against a frozen benchmark, with results
recorded in the MPI-21 ledger. This produces the first number the project has
asked for since the beginning of the prediction track: a baseline accuracy to
beat.

This is a new Python component, `services/prediction/`, sibling to
`services/importer`. It reads canonical match/event/outcome data through a
read-only SQL view and writes only to the tier-2 ledger tables — it never
writes to `matches`, `athletes`, or `events`. This split (Go owns canonical
writes; Python computes and writes experiment results) was decided during
architecture discussion specifically so that trying a new approach never
requires a schema migration or an `sqlc` regeneration.

Out of scope, deliberately narrowed:

- **Bradley-Terry.** Elo and Bradley-Terry are close enough in practice that
  building both in the first ticket would be redundant work before either has
  proven useful. Bradley-Terry becomes a second `model_family` value in the
  same ledger later — that comparison is exactly what MPI-21's schema exists
  to make cheap.
- **Fold/lockbox definitions beyond what this ticket needs to produce one
  real run.** Rolling-origin fold generation from `events` is mechanical and
  in scope. Lockbox membership is a deliberate, rarely-changed human decision
  (which events are withheld) — this ticket adds the capability to seed a
  lockbox protocol from an explicit, operator-supplied event list, but does
  not itself decide which real events go in it. That decision is the
  operator's, made at seeding time, not hardcoded into this contract.
- Evidence-based features, the agent loop, any promotion/PR automation.

## 1. Current-State Architecture

```text
matches, events, match_competitors    (MPI-19: outcomes exist)
eval_protocols, eval_folds,           (MPI-21: schema exists, empty)
experiment_runs, run_predictions,
run_models

No process populates a protocol, computes a rating, or records a prediction.
"How well can we predict matches?" has no answer because nothing has ever
been run.
```

## 2. Target-State Architecture

### Components

```text
+------------------------------ services/prediction ------------------------+
|                                                                            |
|  db.py           read-only queries against v_completed_matches           |
|                                                                            |
|  folds.py         generate_rolling_origin(events) -> [Fold]              |
|                    seed_lockbox(event_ids, kind) -> Fold                 |
|                                                                            |
|  elo.py           fit(matches, k_factor) -> {athlete_id: rating}  (pure)  |
|                    predict(rating_a, rating_b) -> p_win_a         (pure)  |
|                                                                            |
|  run_baseline.py  CLI: for each fold, fit on train, predict test,        |
|                    write experiment_runs / run_predictions / run_models  |
+----------------------------------------------------------------------------+
```

`elo.py` takes no database dependency at all — it is pure functions over
in-memory match lists, unit-tested without PostgreSQL. `db.py` is the only
module that opens a connection. `run_baseline.py` is the composition root,
mirroring the separation `cmd/ingest-youtube` keeps between orchestration and
pure logic on the Go side.

### New Read Boundary

```sql
-- db/migrations/0005_prediction_read_views.sql
create view v_completed_matches as
select
    m.id as match_id,
    m.event_id,
    m.scheduled_at,
    m.arm,
    mc_a.athlete_id as athlete_a_id,
    mc_b.athlete_id as athlete_b_id,
    mc_a.result as result_a
from matches m
join match_competitors mc_a on mc_a.match_id = m.id
join match_competitors mc_b on mc_b.match_id = m.id and mc_b.athlete_id > mc_a.athlete_id
where m.status = 'completed';
```

`services/prediction` queries only this view, never the base tables directly.
This is the versioned interface described during architecture discussion: Go
can change how outcomes are stored underneath without breaking the prediction
service, and there is exactly one place where "what counts as a usable
completed match" is defined.

### Rolling-Origin Fold Generation

```text
events, ordered by held_on, excluding any event already in a lockbox fold
   |
   for each event E from the Nth onward:
     train_match_ids = matches from all events strictly before E
     test_match_ids  = matches in E
     -> one eval_folds row, fold_index = position in this sequence
```

`N` (minimum training events before the first fold) is a CLI parameter, not
hardcoded — too few training matches produces meaningless ratings, and the
right minimum depends on how many events exist when this actually runs.

### Per-Fold Refit (the non-negotiable rule)

```text
for each fold in protocol:
    ratings = elo.fit(fold.train_match_ids)     # fresh fit, no carryover
    for each match in fold.test_match_ids:
        p_win_a = elo.predict(ratings[a], ratings[b])
        record run_prediction(run_id, match_id, athlete_id=a, p_win=p_win_a)
        record run_prediction(run_id, match_id, athlete_id=b, p_win=1-p_win_a)
```

Ratings are never computed once and reused across folds. An athlete with no
prior matches in a fold's training set gets a defined default rating
(constant, not learned) — `elo.fit` must specify this explicitly rather than
raising, since a rolling-origin fold's early test matches will routinely
include athletes debuting in the dataset.

### Metrics

Per fold: accuracy, log-loss, Brier score. Aggregate: the same three metrics
across all fold predictions pooled, plus a Wilson confidence interval on
pooled accuracy — the number this baseline exists to be compared against
later, with the interval attached so a future comparison can ask whether a
difference is distinguishable from noise rather than reading the point
estimate alone.

## 3. Test Plan Defined Before Implementation

### Unit Tests (`elo.py`, no database)

Table-driven (`pytest.mark.parametrize`), each case named by the behavior it
proves:

- equal ratings predict 0.5 win probability for either side;
- a higher rating predicts a higher win probability than the lower-rated
  side, monotonically as the gap widens;
- a large rating gap produces a probability strictly between the configured
  floor and ceiling, never 0 or 1 (an Elo model must never claim certainty);
- fitting on an empty match list returns the configured default rating for
  every athlete queried;
- fitting is order-independent only for `k_factor = 0`, and order-dependent
  otherwise — proves ratings evolve match-by-match rather than as a
  simultaneous fit (deliberately not Bradley-Terry);
- a debuting athlete (no prior matches in the training set) receives the
  documented default rating rather than raising.

### Fold Generation Tests (`folds.py`, real PostgreSQL)

- generates one fold per event from the Nth event onward, in event-date
  order;
- a fold's `train_match_ids` never includes a match from its own or a later
  event (the leakage check this whole design exists to enforce);
- events already assigned to a lockbox protocol are excluded from
  rolling-origin fold generation;
- seeding a lockbox from an explicit event-id list produces exactly one fold
  whose `test_match_ids` are drawn only from those events.

### Integration Test (`run_baseline.py`, real PostgreSQL, seeded matches)

- running the baseline against a seeded rolling-origin protocol produces
  exactly one `experiment_runs` row per invocation, `status = 'completed'`,
  `git_dirty` reflecting the actual working-tree state;
- every test match in every fold has exactly two `run_predictions` rows
  (one per competitor) whose `p_win` values sum to 1.0 within floating-point
  tolerance;
- `run_models.params` contains a rating for every athlete who appeared in
  training data for at least one fold;
- re-running with a dirty working tree writes `git_dirty = true` and the run
  is asserted as non-promotable by a check the test calls directly (not yet
  wired into any promotion process, but the fact must be recorded correctly
  now rather than retrofitted later).

### CI Transparency

New workflow `prediction-ci.yml`: installs `uv`, prints discovered pytest
node IDs before running (`pytest --collect-only -q`), runs `pytest -v`
against a real Postgres service with all migrations applied, and runs `ruff
check`. Named steps describe the behavior under test, matching the existing
Go workflow's transparency standard.

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-22): add Elo baseline and rolling-origin runner contract`

2. `test(MPI-22): define read-only completed-match view`
   - Red PostgreSQL test asserting `v_completed_matches` shape and that it
     excludes non-completed matches.

3. `feat(MPI-22): add completed-match read view`
   - Add `db/migrations/0005_prediction_read_views.sql`.

4. `test(MPI-22): define Elo rating functions`
   - Red unit tests per the table above.
   - Expected failure: `services/prediction/elo.py` does not exist.

5. `feat(MPI-22): add Elo rating functions`
   - Pure `fit`/`predict`, no database dependency.

6. `test(MPI-22): define rolling-origin fold generation`
   - Red PostgreSQL tests for `folds.py`, including the leakage-boundary
     assertion.

7. `feat(MPI-22): add fold generation and lockbox seeding`
   - Implement `folds.py` against `v_completed_matches` and `events`.

8. `test(MPI-22): define baseline run orchestration`
   - Red integration test for `run_baseline.py`.

9. `feat(MPI-22): add baseline runner CLI`
   - Compose fold generation, per-fold Elo fit/predict, and ledger writes.

10. `build(MPI-22): add Python CI for services/prediction`
    - Add `prediction-ci.yml` with discovery, verbose pytest, ruff, and a
      real Postgres service.

11. `docs(MPI-22): document the prediction service boundary`
    - Record the read-view boundary and the per-fold-refit rule in
      `docs/architecture/`.

## 5. Verification Plan

1. Lint and unit tests, no database:

   ```sh
   cd services/prediction
   uv run ruff check .
   uv run pytest --collect-only -q
   uv run pytest -v
   ```

2. Real-PostgreSQL fold and orchestration tests:

   ```sh
   PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
     uv run pytest -v -m integration
   ```

3. Run the actual baseline against seeded fixture matches and inspect the
   ledger directly:

   ```sh
   uv run python -m services.prediction.run_baseline \
     --protocol-name rolling_origin_v1 --min-training-events 5

   psql "$PREDICTION_TEST_DATABASE_URL" -c "
     select model_family, metrics from experiment_runs order by started_at desc limit 1;"
   ```

4. Prove the leakage boundary directly: assert via SQL that no
   `train_match_ids` entry in any fold has a `scheduled_at` at or after the
   corresponding `test_match_ids`' minimum `scheduled_at`.

5. Validate and run the new CI workflow, inspecting verbose discovery and
   test output:

   ```sh
   actionlint .github/workflows/prediction-ci.yml
   ```
