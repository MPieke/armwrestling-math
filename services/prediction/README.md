# Prediction Service

Elo baseline and rolling-origin evaluation runner. See
[`docs/architecture/prediction.md`](../../docs/architecture/prediction.md).

Reads canonical match outcomes through the read-only `v_completed_matches`
view; writes only to the tier-2 experiment ledger (`feature_specs`,
`eval_protocols`, `eval_folds`, `experiment_runs`, `run_input_manifests`,
`run_feature_rows`, `run_predictions`, `run_models`). Never
writes to `matches`, `athletes`, or `events` — those are owned by
`services/importer` (Go).

## Setup

```sh
cd services/prediction
uv sync --extra dev
```

## Commands

```sh
uv run ruff check .
uv run pytest --collect-only -q
uv run pytest -v
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration

uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --min-training-events 5 \
  --feature-schema outcomes_elo_v1

uv run python -m prediction.report --run-id 1 --format json
uv run python -m prediction.explain_prediction --run-id 1 --match-id 42 --format json
```

`DATABASE_URL` (not `PREDICTION_TEST_DATABASE_URL`) is required for
`run_baseline` itself, matching `services/importer`'s convention of reading
configuration from the process environment rather than loading `.env`.

`report` and `explain_prediction` use the same `DATABASE_URL`, but only read
the persisted tier-2 ledger. They never refit a model or contact a provider.
