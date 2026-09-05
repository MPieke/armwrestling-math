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

experiment ledger (tier 2)      feature_specs, eval_protocols, eval_folds,
                                 experiment_runs, run_input_manifests,
                                 run_feature_rows, run_predictions, run_models -- written
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
| spec       jsonb |              | test_match_ids   bigint[] |
| created_at       |              |                           |
+------------------+              +---------------------------+
                                     PK(protocol_id, fold_index)

feature_specs                         experiment_runs
+-----------------------+             +---------------------+
| id                    |<------------| feature_spec_id  FK  |
| name, version     U   |             | git_sha, git_dirty  |
| representation_kind   |             | protocol_id      FK  |----> eval_protocols
| definition jsonb      |             | model_family        |
| definition_sha256     |             | hyperparams   jsonb |
+-----------------------+             | seed                |
                                      | parent_run_id   FK  |----> experiment_runs (self, nullable)
                                      | hypothesis          |
                                      | status, metrics     |
                                      +---------------------+
                                               |          |
                                               v          v
                                  run_input_manifests  run_predictions
                                  +-----------------+    (run_id, match_id,
                                  | run_id PK/FK    |     athlete_id, p_win)
                                  | cutoff_policy   |
                                  | data_summary    |    run_models
                                  | manifest_sha256 |    (run_id, params jsonb)
                                  +-----------------+
                                           |
                                           v
                                  run_feature_rows
                                  (run_id, fold_index, match_id, role,
                                   payload jsonb, payload_sha256)
```

Two deliberate omissions, and why:
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

### Protocol lifecycle (MPI-24)

A lockbox is seeded before any rolling-origin development protocol. Its one
fold trains on completed matches from events strictly before the earliest
selected lockbox event and tests on completed matches from the selected
events. `eval_protocols.spec` records the selected event slugs and freeze
date. Rolling-origin creation refuses to proceed until at least one lockbox
exists and records `min_training_events` in its own spec.

A `lockbox_prospective` protocol may grow only through the explicit
`prediction.prospective` command. It appends all matches from one named event,
including scheduled matches, while preserving idempotency. Protocol and fold
membership remain inspectable through `prediction.report`.

### First real baseline (2026-09-05)

The canonical database's first non-fixture data: 57 completed dyadic matches
across `east-vs-west-22` through `east-vs-west-25` (4 events, 90 athletes,
48 with a linked YouTube video), hand-transcribed from armsport.app's
rendered competition pages — not its API — into
`data/manual_results/east_vs_west_22_25.csv` and loaded via
`cmd/load-results`. `east-vs-west-25` (2026-08-01, the most recent event) was
chosen as `lockbox_retrospective_v1`'s sole event, freezing training data to
matches strictly before that date; `rolling_origin_v1` was seeded against the
remaining 3 events with `min_training_events=1` (the smallest value that
still produces any folds at this data volume).

Run 2 (`elo`, `k_factor=24.0`, git SHA `ae858d6`, promotable): accuracy
0.828 (Wilson 95% CI [0.655, 0.924], n=29), log-loss 0.701, Brier 0.254.
The CI is honestly wide — this is a first-pass signal from 2 rolling-origin
folds, not a stable estimate, and both the lockbox event choice and
`min_training_events=1` should be revisited once more real events are
collected.

### First lockbox consultation (2026-09-05)

`lockbox_retrospective_v1` consulted once (`evaluate_lockbox.py`, `elo`,
run 6, promotable): accuracy 0.60 (Wilson 95% CI [0.36, 0.80], n=15),
log-loss 0.691, Brier 0.249 — notably lower than the rolling-origin dev
accuracy of 0.828 above. The CI is wide enough at n=15 that this alone
doesn't prove overfitting to the dev folds, but it's the exact kind of gap
the lockbox exists to surface, and it's a real signal to keep in mind
rather than something to re-run away: the lockbox is spent for this
protocol/family combination until more retrospective events justify
reseeding it.

## Model Families (MPI-25)

Tier A (results-only rating systems) sits behind one interface:

```python
class Predictor(Protocol):
    def predict(self, match: CompletedMatch) -> float: ...
    def params(self) -> dict: ...

class ModelFamily(Protocol):
    def fit(self, train_matches: list[CompletedMatch]) -> Predictor: ...

MODEL_FAMILIES = {"elo": EloFamily(), "glicko2": Glicko2Family(), "bradley_terry": BradleyTerryFamily()}
```

`run_baseline.py` calls `MODEL_FAMILIES[model_family].fit(...)` instead of
`elo.fit`/`elo.predict` directly; `--model-family` selects it on the CLI
(default `elo`, unchanged behavior). `report --run-id` reads `run_models`
generically — no family-specific branching — because every family's
`params()` already returns its full fitted, inspectable state.

`glicko2.py` hand-rolls Glickman's algorithm (dependency-free, white-box)
rather than pulling a library. `glicko2_update` is one full rating period
(the paper's steps 3-8) and is tested directly against the paper's own
worked example; `Glicko2Family.fit` calls it once per match, sequentially,
with a single-result list, matching how `elo.fit` already walks a fold.

`bradley_terry.py` fits fresh per fold via `choix.opt_pairwise` with L2
regularization. A batch MLE over one fold's `train_matches` is not the
leakage a single global fit would be — everything in that set is already
pre-cutoff by `folds.generate_rolling_origin`.

## Point-In-Time Feature Models (MPI-26)

Tier B adds an **inner** temporal loop on top of the outer rolling-origin
split: building the training set itself requires walking forward in time,
not just splitting by fold. `point_in_time_features.build_training_table`
threads a running state (per-athlete Elo rating via `elo.step`, head-to-head
counts, a 5-match recent-form window, all-time win rate, last-match date)
through a fold's `train_matches` exactly like `elo.fit` threads its ratings
dict: a row's features come from state as of the *previous* match, and only
then does that match update state. `features_for_test_match` applies the
same state, built from every training match, to the one match being
predicted — the tabular equivalent of `elo.fit`'s final ratings dict.

The failure mode this guards against is easy to miss: computing e.g.
"head-to-head record as of the fold cutoff" once for the whole training
window and reusing it for every training row is still "before the cutoff,"
just not before *that specific row* — a March example would see its own
June rematch. `test_leakage_a_later_rematch_never_changes_an_earlier_rows_features`
is the test that would catch a regression back into that shape.

Feature values are left raw (numbers as numbers, `arm`/`weight_class` as
strings) — encoding is a model's concern, not the builder's. `logreg.py`
one-hot encodes categoricals against a vocabulary fixed from the fold's own
training rows (an unseen category at test time becomes an all-zero
indicator, never an error) and falls back to an explicit uninformative 0.5
predictor for the degenerate single-outcome-class fold small real data
produces early on. `tabpfn_family.py` reuses the same encoding behind an
optional `[tabpfn]` extra (pulls in torch); `MODEL_FAMILIES` only registers
`"tabpfn"` when the import succeeds.

`prediction.explain_prediction` extends generically: every persisted
`run_feature_rows` payload already carries its `features` and a
`provenance` map (feature name -> the source match ids it was derived
from); an empty list means "no source record, this is a documented
default," which the CLI surfaces explicitly as `defaulted_features`. It
also reconstructs the fold cutoff (the latest training match's
`scheduled_at`) and each athlete's observed outcome, all read-only.

Cold-start rating priors from external rankings (`athlete_rankings`,
point-in-time `as_of`-gated selection, the additive
`ModelFamily.fit(..., default_ratings=...)` hook the contract describes)
were scoped out of this pass: no real ranking data exists for any loaded
athlete yet, and nothing downstream depends on it. `default_ratings` is
already a no-op-safe optional parameter throughout
`point_in_time_features.py` and `logreg.py`, so wiring a real source in
later is additive, not a redesign.

## Paired Comparison And The Lockbox Gate (MPI-27)

`comparison_stats.py` is pure: given two runs' paired predictions on the
same matches, it reports McNemar's exact (binomial, not the
continuity-corrected chi-square approximation — the discordant-pair counts
here are in the dozens, not hundreds) test on accuracy alongside a paired
bootstrap CI on the log-loss difference. The bootstrap CI is the primary
verdict (`distinguishable` iff it excludes zero) because it uses the full
predicted probability, not just the thresholded pick; two runs can tie on
accuracy while still being reliably distinguishable on calibration, and the
reverse is also possible. `compare.py` is the thin database-facing wrapper:
it refuses two runs on different protocols outright, restricts to an
explicit `match_ids` subset when given one (MPI-28 needs this for
evidence-covered matches only), and reports the exact evaluated scope so a
comparison can't be misread as covering a different population than it did.

`evaluate_lockbox.py` treats a lockbox protocol as a scarce,
non-renewable-within-a-session resource: it refuses outright on a dirty
working tree (stricter than the ordinary `run_baseline` path, which merely
records `git_dirty` and lets a human judge later — spending a lockbox
consultation on an unreproducible run is worse than flagging one after the
fact), and reports how many times a protocol has already been consulted
(`count(experiment_runs where protocol_id = ...)`, no new tracking table)
before and after. `--dry-run` runs every guard and shows what would be
evaluated without inserting a run or spending a consultation.

## Experiment Input Provenance (MPI-30)

`feature_specs` names and versions each model-facing representation. Its
canonical-JSON SHA-256 makes the definition inspectable independently of the
model code. `experiment_runs.feature_spec_id` selects exactly one registered
representation for a run.

Before fitting, `run_baseline.py` copies each fold's train and test payloads
from `v_completed_matches` into `run_feature_rows`. `run_input_manifests`
records the cutoff policy, input summary, and manifest hash. PostgreSQL
triggers reject inserts, updates, and deletes from either input table after a
run becomes `completed`; a correction to canonical data therefore cannot
silently change the basis of a historical result.

`prediction.report` and `prediction.explain_prediction` are read-only
operator commands. They reconstruct the persisted run, schema, folds,
manifest, feature payloads, and recorded probabilities; they neither refit a
model nor write ledger data.

## services/prediction (MPI-22)

The first component to write to the ledger. Python, sibling to
`services/importer`, with its own `pyproject.toml`/`uv.lock`.

```text
db.py            reads events and v_completed_matches only -- never
                 matches/match_competitors directly. This is the boundary:
                 Go can change how outcomes are stored underneath without
                 breaking this service, and "what counts as a usable
                 completed match" has exactly one definition.

elo.py / glicko2.py / pure fit/predict per family, no database dependency;
bradley_terry.py    model_families.py holds the Predictor/ModelFamily
                     interface and the MODEL_FAMILIES registry

point_in_time_features.py  Tier B's inner loop: build_training_table,
                 features_for_test_match, history_v1_fold_payloads

logreg.py /      Tier B models over the same feature table; tabpfn_family
tabpfn_family.py is optional ([tabpfn] extra) and self-excludes from
                 MODEL_FAMILIES when the import is unavailable

folds.py         generate_rolling_origin (pure, over db.py's lists) and
                 seed_lockbox (writes -- which events go in a lockbox is a
                 deliberate human decision made at seeding time)

metrics.py       pure: accuracy, log-loss, Brier score, Wilson interval

run_baseline.py  composition root; the only module that opens a
                 connection and commits

input_manifest.py persists fold-scoped model inputs before fitting and
                 resolves the named feature schema

report.py /      read-only reconstruction of a completed run and one
explain_prediction.py persisted test prediction, respectively

seed_lockbox.py / operator commands for initial lockbox materialization and
prospective.py    explicit prospective event growth
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

`run_baseline.py` calls `family.fit(...)` fresh for every fold, using only
that fold's `train_match_ids`. State from one fold is never carried into the
next, for any family. This is the leakage guardrail the whole rolling-origin
design exists
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
- `docs/contracts/MPI-30-experiment-input-contracts-and-feature-schema-provenance.md`
  — versioned feature schemas and immutable run inputs.
- `docs/contracts/MPI-25-pluggable-model-families.md` — Glicko-2 and
  Bradley-Terry behind the same interface as Elo.
- `docs/contracts/MPI-26-point-in-time-feature-models.md` — the inner
  temporal loop, LogReg/TabPFN, and feature-provenance explanation.
- `docs/contracts/MPI-27-paired-comparison-lockbox-gate.md` — statistically
  honest comparison and the lockbox consultation gate.
