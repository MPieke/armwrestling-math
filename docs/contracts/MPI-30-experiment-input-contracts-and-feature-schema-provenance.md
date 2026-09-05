---
linear_issue: MPI-30
status: proposed
---

# Contract MPI-30: Experiment Input Contracts And Feature-Schema Provenance

## Scope

Make a prediction run inspectable after canonical PostgreSQL data changes by
separating canonical facts, feature schemas, and model families. This is the
shared foundation for MPI-24 through MPI-29; those tickets must not invent
their own input snapshots or explanation formats.

In scope: tier-2 ledger tables and Python prediction-service commands. The
canonical tables `events`, `athletes`, `matches`, `match_competitors`,
`sources`, `claims`, and `claim_subjects` remain owned by
`services/importer` and are read-only to this ticket. Out of scope: new
armwrestling measurements (including athlete style), provider calls, and
training a neural model.

## 1. Current-State Architecture

### Components

```text
PostgreSQL canonical facts             services/prediction
events, athletes, matches,             run_baseline.py
match_competitors, claims                    |
        |                                    v
        `--> v_completed_matches ------> model family
                                              |
                                              v
experiment ledger                      experiment_runs, run_predictions,
eval_protocols/eval_folds              run_models
```

`experiment_runs.feature_spec` exists but no contract defines its shape or
links it to the model inputs. `run_predictions` records a probability but
not the feature vector or prompt packet that produced it. `eval_folds`
materializes match membership, but it cannot preserve a canonical row's
contents if a result or evidence record is corrected later.

### Current ER Boundary

```text
eval_protocols <- eval_folds
       ^                |
       |                v
experiment_runs ---> run_predictions
       |
       `-------------> run_models

No persisted relation identifies the feature-schema version, training rows,
test inputs, missingness, or immutable payload used by a prediction.
```

## 2. Target-State Architecture

### Components

```text
Canonical PostgreSQL facts (Go-owned, read-only to prediction)
  events athletes matches match_competitors sources claims claim_subjects
                                  |
                                  v
services/prediction
  FeatureSchema(name, version, representation_kind, build)
  ModelFamily(compatible_representation_kinds, fit, predict)
                                  |
                                  v
Tier-2 experiment ledger (Python-owned writes)
  feature_specs -> experiment_runs -> run_input_manifests
                       |                    |
                       v                    v
                 run_predictions <--- run_feature_rows
```

Canonical schema captures real-world facts. A feature schema is an
experimental, versioned representation of those facts; examples are
`outcomes_elo_v1`, `history_v1`, `evidence_dyad_v1`, and a later
`style_transitive_v1`. A model family declares which representation kinds it
can consume (`rating`, `tabular`, `sequence`, `graph`, or `prompt`). This
lets an experiment change the model, feature schema, or both deliberately.

### Ledger ER Diagram

```text
feature_specs                         experiment_runs
+-----------------------+             +---------------------------+
| id                    |<------------| feature_spec_id       FK  |
| name, version     U   |             | protocol_id           FK  |
| representation_kind   |             | model_family              |
| definition jsonb      |             | hyperparams, seed         |
| definition_sha256     |             | git_sha, git_dirty        |
+-----------------------+             +---------------------------+
                                           |                 |
                                           v                 v
                                  run_input_manifests   run_predictions
                                  +-----------------+          |
                                  | run_id PK/FK    |          |
                                  | cutoff_policy   |          v
                                  | data_summary    |   run_feature_rows
                                  | manifest_sha256 |   +--------------------------+
                                  +-----------------+   | run_id FK                |
                                                        | fold_index               |
                                                        | match_id FK              |
                                                        | role: train | test       |
                                                        | payload jsonb            |
                                                        | payload_sha256           |
                                                        +--------------------------+
                                                        PK(run_id, fold_index,
                                                           match_id, role)
```

`feature_specs.definition` is the stable, machine-readable contract for a
representation: required canonical inputs, transformations, availability and
missingness semantics, and code-level schema version. The SHA-256 is computed
from a canonical JSON serialization and prevents two definitions from being
mistakenly treated as the same feature schema.

`run_input_manifests` persists the exact protocol/fold membership, cutoff
policy, data-availability summary, and hashes of all feature rows for one
run. `run_feature_rows.payload` persists the model-facing input for every
training and test match in every fold, including values already copied from
canonical rows, source identifiers, time-eligibility decisions, and explicit
missing/defaulted values. It is append-only once the run completes. This
small-project v1 intentionally stores JSON in PostgreSQL; a future large
payload implementation may replace `payload` with an immutable object-store
reference without changing the feature-schema or report interfaces.

### Run Sequence

```text
operator -> run-baseline
run-baseline -> feature schema: validate model compatibility
run-baseline -> canonical DB: read only eligible facts per fold/match time
run-baseline -> run_feature_rows: persist train/test model inputs + hashes
run-baseline -> model family: fit(training payloads), predict(test payloads)
run-baseline -> experiment ledger: persist run, manifest, predictions, model
operator -> report/explain-prediction: read persisted ledger payloads only
```

`report --run-id [--format text|json]` shows the run, schema definition/hash,
protocol/folds, model metadata, metrics, model state, and data summary.
`explain-prediction --run-id --match-id [--format text|json]` shows the
persisted test payload, source eligibility and missingness decisions, and the
recorded probability. Neither command refits a model, writes a ledger row,
or contacts a provider.

## 3. Commit-by-Commit Breakdown

1. `docs(MPI-30): add experiment input provenance contract`
   - Files: this contract and linked MPI-24–29 contracts.
   - Records the common boundary and dependency before implementation.
   - Reviewable alone: no runtime behavior changes.
2. `test(MPI-30): define feature schema validation` — red.
   - Files: `services/prediction/tests/test_feature_specs.py`.
   - Defines canonical definition hashing and rejects unsupported
     model/representation combinations.
   - Reviewable alone: pure rules with no database dependency.
3. `feat(MPI-30): add feature schema registry`.
   - Files: `db/migrations/*`, `services/prediction/prediction/feature_specs.py`,
     `services/prediction/prediction/db.py`, generated/schema checks.
   - Adds `feature_specs` and validates registered schemas before a run.
   - Reviewable alone: establishes one schema identity boundary.
4. `test(MPI-30): define immutable run input snapshots` — red.
   - Files: `services/prediction/tests/test_input_manifest.py` and integration
     fixtures.
   - Defines row hashing, train/test role coverage, completed-run immutability,
     and explicit missingness preservation.
   - Reviewable alone: behavior of the new persistence boundary.
5. `feat(MPI-30): persist run input manifests and feature rows`.
   - Files: migration, `services/prediction/prediction/input_manifest.py`,
     `run_baseline.py`, integration helpers.
   - Records all model-facing rows and one immutable manifest per run.
   - Reviewable alone: uses the existing Elo path as the first real boundary.
6. `test(MPI-30): define report and explanation reconstruction` — red.
   - Files: report/explanation unit and PostgreSQL integration tests.
   - Defines JSON/text output and proves inspection does not invoke model fit,
     provider code, or ledger writes.
   - Reviewable alone: operator-visible contract before CLI implementation.
7. `feat(MPI-30): add report and explain-prediction commands`.
   - Files: `prediction/report.py`, `prediction/explain_prediction.py`, README,
     CLI tests.
   - Implements the common read-only inspection surface.
   - Reviewable alone: no new feature or model family is introduced.
8. `docs(MPI-30): document experiment input provenance`.
   - Files: `docs/architecture/prediction.md`, `services/prediction/README.md`.
   - Documents ownership, extension workflow, and manual operator commands.
   - Reviewable alone: records the implemented architecture.

## 4. Verification Plan

```sh
cd services/prediction
uv sync --extra dev
uv run ruff check .
uv run pytest --collect-only -q
uv run pytest -v -m "not integration"
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration

# Seed a named, versioned feature schema and run the existing Elo control.
DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --model-family elo \
  --feature-schema outcomes_elo_v1

# Inspect the exact persisted basis without writing or refitting.
DATABASE_URL=... uv run python -m prediction.report --run-id <run-id> --format json
DATABASE_URL=... uv run python -m prediction.explain_prediction \
  --run-id <run-id> --match-id <test-match-id> --format json

# Direct database checks: every fold member has a payload, and the manifest
# hash matches the persisted payload hashes.
psql "$DATABASE_URL" -c "select role, count(*) from run_feature_rows where run_id = <run-id> group by role order by role;"
psql "$DATABASE_URL" -c "select run_id, manifest_sha256, data_summary from run_input_manifests where run_id = <run-id>;"
```

The integration suite must additionally prove that a completed run's
`run_feature_rows` and `run_input_manifests` cannot be changed, and that the
read-only inspection commands leave all tier-2 table counts unchanged.
