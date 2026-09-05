---
linear_issue: MPI-29
status: proposed
---

# Contract MPI-29: LLM Direct Predictor, Prospective-Only

## Scope

Tier D: give a large LLM the match context and let it predict directly —
the "bitter lesson" hypothesis, tested rather than argued. Depends on
MPI-25 (model interface), MPI-27 (`compare`/lockbox gate exist). Uses
MPI-28's selection layer for the evidence packet when merged; a
results-only packet is a valid v1, so this does not block on MPI-28.

## The Non-Negotiable Rule

A pre-trained LLM has almost certainly seen historical armwrestling results
in training. Asking it about a past match may simply recall the outcome —
a leak inside the model's weights that no rolling-origin fold can detect,
because the fold boundary only governs *our* data, not what the model
already knows. Consequence: **this family is refused on any protocol whose
`kind` is not `lockbox_prospective`**, enforced in code with the
contamination reason in the error, not left as an operating convention.

## 1. Current-State Architecture

```text
run_baseline(protocol_id, model_family, ...) accepts any protocol_id.
MODEL_FAMILIES (MPI-25) has no "llm" entry.
run_predictions has no place for a rationale.
```

## 2. Target-State Architecture

### Protocol Guard

```python
def run_baseline(connection, protocol_id, *, model_family, ...):
    if model_family == "llm":
        kind = _protocol_kind(connection, protocol_id)
        if kind != "lockbox_prospective":
            raise ContaminationError(
                f"model_family='llm' refused on protocol kind {kind!r}: "
                "a pretrained LLM may have memorized historical results; "
                "only lockbox_prospective is a valid backtest for it"
            )
```

### LLM Family

```text
LLMFamily.fit(train_matches) -> LLMPredictor(train_matches)
   -- "fit" stores context; no parameters are learned in the usual sense

LLMPredictor.predict(match):
   1. build a packet: both athletes' prior results (+ evidence claims via
      MPI-28's selection, if available), match metadata
   2. prompt for structured output: {winner_athlete_id, probability,
      rationale: str}  -- derived Go-style schema equivalent in Python
      (pydantic model + provider's structured-output mode)
   3. validate: winner is one of the two athletes, probability in (0,1);
      a malformed response records a FAILED prediction for that match,
      not a crash of the whole run
```

Model id and prompt version go in `hyperparams` — `seed` does not control
an LLM's output.

### Rationale Storage

```text
run_match_rationale
+------------------+
| run_id       FK  |
| match_id     FK  |
| rationale        |
+------------------+
  PK(run_id, match_id)
```

A new table, not a column on `run_predictions` — the rationale is
per-*match*, and `run_predictions` is keyed per-athlete-per-match; a jsonb
column there would duplicate the same text across both rows.

### Calibration

```text
Platt scaling: fit a 1-D logistic regression mapping raw LLM probability
-> calibrated probability, using (prediction, outcome) pairs from
PRIOR completed lockbox_prospective evaluations of this model_family --
never the batch currently being predicted, which has no outcomes yet.

First-ever prospective evaluation: no calibration data exists. Store the
raw probability, flag it explicitly (metrics.calibrated = false) rather
than silently fabricating a calibration from nothing.
```

## 3. Test Plan Defined Before Implementation

### Unit (fake LLM client — no real API calls)

- protocol guard rejects `rolling_origin` and `lockbox_retrospective` with
  the contamination reason; accepts `lockbox_prospective`
- a fake client returning a well-formed response validates and records
  normally; one returning an unrecognized winner, an out-of-range
  probability, or malformed JSON records a failed prediction for that
  match without aborting the run
- Platt scaling: fit/predict correctness on synthetic (raw, outcome) pairs;
  the first-ever run (no prior data) uses raw probability and is flagged
  uncalibrated

### Integration

- a full run against a seeded `lockbox_prospective` protocol (fake client)
  records model id, prompt version, both probabilities, and a
  `run_match_rationale` row per match

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-29): add LLM direct predictor contract`
2. `test(MPI-29): define the protocol-kind guard` — red
3. `feat(MPI-29): add the protocol-kind guard`
4. `test(MPI-29): define the LLM predictor and structured-output validation` — red
5. `feat(MPI-29): add the LLM predictor family`
6. `test(MPI-29): define rationale storage` — red
7. `feat(MPI-29): add run_match_rationale schema and wiring`
8. `test(MPI-29): define calibration` — red
9. `feat(MPI-29): add calibration`
10. `docs(MPI-29): document the prospective-only rule and calibration bootstrap`

## 5. Verification Plan

```sh
cd services/prediction
uv run pytest -v -m "not integration"
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration

# Refusal proof:
DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --model-family llm   # must fail, contamination reason

# Real run, once a lockbox_prospective protocol has matches:
DATABASE_URL=... OPENAI_API_KEY=... uv run python -m prediction.run_baseline \
  --protocol-name lockbox_prospective_v1 --model-family llm
DATABASE_URL=... uv run python -m prediction.report --run-id <llm-run>
```
