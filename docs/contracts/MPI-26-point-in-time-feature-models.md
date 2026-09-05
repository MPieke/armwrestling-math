---
linear_issue: MPI-26
status: proposed
---

# Contract MPI-26: Point-In-Time Feature Models

## Scope

Tier B of the model ladder: results-derived features (plus rating outputs,
stacked) feeding LogReg and TabPFN. This is the first component with an
**inner** temporal loop — building the training set itself requires walking
forward in time, not just the outer rolling-origin split.
Depends on MPI-30: `history_v1` and later feature definitions use the shared
feature-schema registry, immutable feature rows, and explanation surface.

## 1. Current-State Architecture

```text
elo.fit(train_matches) -> ratings                (walks forward, correct)
choix / glicko fit(train_matches) -> ratings     (same)

Nothing builds a (features, label) row per match. If it did naively --
e.g. "head_to_head_wins as of the fold cutoff" computed once over the
whole training window and reused for every training row -- a March
training example would see its own June rematch. That leak is invisible:
every number still comes from "before the fold cutoff," just not before
that specific row.
```

## 2. Target-State Architecture

### The Inner Loop

```text
build_training_table(train_matches: list[CompletedMatch])
   -> list[FeatureRow]

for each match in train_matches (already chronological):
    features_i = compute_features(running_state)   # state as of match i-1
    label_i    = match.result_a
    update running_state with match i               # AFTER extracting features
```

`running_state` (head-to-head counts, recent-form deques, last-match dates
per athlete) is threaded exactly like `elo.fit`'s `ratings` dict — same
sequential-walk shape, same reason: state as of a point is only valid if
built from strictly earlier matches.

Predicting the actual test match reuses the state after the *last* training
match — i.e., state as of the fold cutoff, the same quantity `elo.fit`'s
final `ratings` represents.

### Prediction Basis Inspection

`prediction/explain_prediction.py` adds `explain-prediction --run-id
--match-id` for feature-model runs. It must print a human-readable account
and support `--format json`, showing the prediction and observed outcome,
the target match's scheduled time, the fold cutoff, every encoded feature
value, the historically eligible source records used to derive it, and any
missing/defaulted values. It must make the point-in-time boundary auditable:
no source record at or after the target match's scheduled time may appear.
The command reads persisted run/protocol state and must not refit a model or
write to the ledger.

### Features (v1)

```text
prior_rating_a, prior_rating_b     -- from any MPI-25 family, stacked
head_to_head_diff                  -- wins_a - wins_b before this match
recent_form_a, recent_form_b       -- win rate, last N matches
win_rate_a, win_rate_b             -- all-time as of cutoff
arm, weight_class                  -- categorical
days_since_last_match_a/b
```

### Models

```text
logreg.py    sklearn.linear_model.LogisticRegression
             coefficients -> run_models.params (name -> weight)

tabpfn.py    TabPFNClassifier over the same feature table
             optional dependency ([tabpfn] extra, pulls in torch);
             not white-box, a reference point only
```

### Rating Priors From External Rankings (cold-start)

```text
athlete_rankings
+------------------+
| athlete_id    FK |
| source           |
| rank             |
| as_of      date  |
+------------------+
```

`as_of` is load-bearing: selecting a ranking requires `as_of < fold cutoff`
— applying today's rank to a 2019 match is exactly the leakage this whole
project is built to avoid.

This changes MPI-25's interface: `ModelFamily.fit` gains an optional
`default_ratings: dict[athlete_id, float]` (falling back to the family's
flat default when absent or when an athlete has no qualifying ranking).
Resolving `default_ratings` for a fold is this ticket's job; the interface
change is a small, additive edit to `MPI-25`'s `ModelFamily` protocol.

## 3. Test Plan Defined Before Implementation

### Unit

- **Point-in-time leakage test, the primary one**: construct a synthetic
  match sequence where a later match's result would change an earlier
  match's `head_to_head_diff`/`recent_form` if computed naively; assert
  the built table does *not* reflect it — this test must fail on a
  deliberately-broken "compute once over the window" implementation and
  pass on the sequential one
- feature values match hand-computed expectations on a small fixed sequence
  (head-to-head count, recent-form window boundary, days-since-last-match
  for a debuting athlete — defined value, not an error)
- rating-prior selection: a ranking with `as_of` on/after the fold cutoff is
  never selected; the most recent qualifying one is
- LogReg coefficients round-trip with interpretable feature names in
  `run_models.params`
- `explain-prediction` for a fixed fixture match shows its feature values,
  source records, cutoff, and defaults; a post-match record is absent

### Integration

- a full LogReg run against the real protocol produces a ledger entry
  comparable via `report`
- `explain-prediction` reconstructs the stored LogReg prediction basis for
  a real persisted run without writing or refitting

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-26): add point-in-time feature models contract`
2. `test(MPI-26): define the point-in-time feature builder` — red, including
   the leakage test
3. `feat(MPI-26): add the point-in-time feature builder`
4. `test(MPI-26): define logistic regression over features` — red
5. `feat(MPI-26): add logistic regression`
6. `test(MPI-26): define athlete_rankings and point-in-time prior selection` — red
7. `feat(MPI-26): add athlete_rankings schema, CSV loader, rating-prior wiring`
   — includes the additive `ModelFamily.fit` signature change (MPI-25)
8. `test(MPI-26): define TabPFN over the same features` — red, behind an
   optional-import guard
9. `feat(MPI-26): add TabPFN as an optional model family`
10. `test(MPI-26): define explain-prediction feature provenance` — red
11. `feat(MPI-26): add explain-prediction for point-in-time feature basis`
12. `docs(MPI-26): document the feature builder and cold-start priors`

## 5. Verification Plan

```sh
cd services/prediction
uv sync --extra dev
uv run ruff check .
uv run pytest -v -m "not integration"
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration

DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --model-family logreg
DATABASE_URL=... uv run python -m prediction.report --run-id <logreg-run>
# confirm coefficients are present and named
DATABASE_URL=... uv run python -m prediction.explain_prediction \
  --run-id <logreg-run> --match-id <match-id>

uv sync --extra tabpfn
DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --model-family tabpfn
```
