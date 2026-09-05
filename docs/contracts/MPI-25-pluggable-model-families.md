---
linear_issue: MPI-25
status: proposed
---

# Contract MPI-25: Pluggable Model Families (Glicko-2, Bradley-Terry)

## Scope

Move Elo behind a small model interface without changing its behavior, then
add Glicko-2 (hand-rolled) and Bradley-Terry (`choix`) behind it. Minimal
refactor — one interface, three families — not a modeling framework.

## 1. Current-State Architecture

```text
run_baseline.py
   |
   `--> elo.fit(train_matches, k_factor) -> ratings dict
        elo.predict(rating_a, rating_b) -> p_win_a
```

`model_family` is a free-text label on `experiment_runs`; nothing enforces
that the label matches what actually ran.

## 2. Target-State Architecture

### Interface

```python
class Predictor(Protocol):
    def predict(self, match: CompletedMatch) -> float: ...
    def params(self) -> dict: ...          # -> run_models.params

class ModelFamily(Protocol):
    def fit(self, train_matches: list[CompletedMatch]) -> Predictor: ...

MODEL_FAMILIES: dict[str, ModelFamily] = {
    "elo": EloFamily(),
    "glicko2": Glicko2Family(),
    "bradley_terry": BradleyTerryFamily(),
}
```

`run_baseline._fit_predict_and_record` calls `MODEL_FAMILIES[model_family].fit(...)`
instead of `elo.fit`/`elo.predict` directly. `--model-family` added to the
CLI (default `elo`, preserving current behavior).

### Glicko-2 (hand-rolled)

The core update is a **rating period** — one or more results against known
opponents, applied together:

```python
def glicko2_update(
    mu: float, phi: float, sigma: float,
    results: list[tuple[float, float, float]],  # (opp_mu, opp_phi, score)
) -> tuple[float, float, float]:
    """Glickman's Glicko-2 algorithm, steps 3-8, exactly as published."""
```

`fit()` calls this **once per match, sequentially, with a single-result
list** — each match is its own one-game rating period, applied
chronologically, matching how Elo already processes matches. This is a
deliberate choice, not an approximation: it keeps a debuting opponent's
rating visible to every subsequent match in the same fold, same as Elo.

Debuting athlete defaults, per Glickman's recommendation: `mu=0` (rating
1500 on the original scale), `phi=350/173.7178`, `sigma=0.06`.

### Bradley-Terry (`choix`)

```python
def bt_fit(train_matches) -> dict[athlete_id, float]:
    # map athlete_id -> contiguous local index for this fold
    # choix.opt_pairwise(n_items, comparisons, alpha=L2_REG)
    # map strengths back to athlete_id
```

One MLE per fold over that fold's `train_matches` only — everything in a
fold's training set is already pre-cutoff, so a batch fit here is not the
leakage a single global fit would be (that distinction, and why it matters,
is recorded in the module docstring). `predict` is the BT sigmoid:
`1 / (1 + exp(-(theta_a - theta_b)))`.

New dependency: `choix` in `pyproject.toml`.

### Deliberately Out Of Scope

Neural models (FFNN/CNN/embeddings-as-features): no structural prior at
n≈300, and not white-box. Recorded here so the reasoning isn't re-litigated:
worth a `model_family` entry once data volume changes the tradeoff, not
before.

## 3. Test Plan Defined Before Implementation

### Unit

- `MODEL_FAMILIES["elo"]` run against a fixed match sequence produces
  identical predictions to the pre-refactor `elo.fit`/`elo.predict` (pinned
  fixture values) — proves the refactor changed nothing observable
- `glicko2_update` reproduces Glickman's published worked example exactly:
  player at (1500, 200, 0.06) facing three opponents
  ((1400,30),win), ((1550,100),loss), ((1700,300),loss) in one rating
  period yields rating ≈1464.06, RD ≈151.52, sigma ≈0.05999 (paper's
  precision)
  — this test feeds all three as one `results` list, the one case where
  `fit()`'s single-result-per-match usage differs from this direct test
- Glicko-2 debuting athlete gets the documented defaults; RD *shrinks*
  after a game (more certainty) and *grows* with the None-played default
- `choix`-backed BT: monotonic — higher fitted strength predicts higher win
  probability; regularization keeps a probability finite (not exactly 0/1)
  even for a fold with an all-one-sided record
- each family run twice on the same fold with fresh state produces
  identical output (no hidden cross-fold state)

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-25): add pluggable model families contract`
2. `test(MPI-25): define the model interface and Elo parity` — red
3. `feat(MPI-25): add model interface, move Elo behind it`
4. `test(MPI-25): define Glicko-2 against the published worked example` — red
5. `feat(MPI-25): add Glicko-2`
6. `test(MPI-25): define Bradley-Terry via choix` — red
7. `feat(MPI-25): add Bradley-Terry`
8. `docs(MPI-25): document model families` — `docs/architecture/prediction.md`

## 5. Verification Plan

```sh
cd services/prediction
uv sync --extra dev
uv run ruff check .
uv run pytest -v -m "not integration"
PREDICTION_TEST_DATABASE_URL='postgres://admin:admin@127.0.0.1:5432/armwrestling_math_test?sslmode=disable' \
  uv run pytest -v -m integration

DATABASE_URL=... uv run python -m prediction.run_baseline \
  --protocol-name rolling_origin_v1 --model-family glicko2
DATABASE_URL=... uv run python -m prediction.report --run-id <glicko2-run>
# Manual comparison against the MPI-24 Elo run's metrics; MPI-27's `compare`
# gives the statistically honest version once it lands.
```
