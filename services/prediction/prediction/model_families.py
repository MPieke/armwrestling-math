"""One fit/predict interface behind which every model family lives.

A ModelFamily.fit(train_matches) call must return a fresh Predictor with no
state carried over from a previous fold -- MPI-25's parity test asserts this
by fitting the same family twice on the same fold and comparing output.
Each Predictor exposes its fitted state through params() so
prediction.report can show the model basis generically, with no
family-specific database inspection.
"""

from __future__ import annotations

from typing import Protocol

from prediction import elo
from prediction.bradley_terry import BradleyTerryFamily
from prediction.db import CompletedMatch
from prediction.glicko2 import Glicko2Family
from prediction.logreg import LogRegFamily


class Predictor(Protocol):
    def predict(self, match: CompletedMatch) -> float:
        """Probability that match.athlete_a_id wins."""
        ...

    def params(self) -> dict:
        """JSON-serializable fitted state, persisted to run_models.params."""
        ...


class ModelFamily(Protocol):
    representation_kind: str
    """Which feature_specs.representation_kind this family can consume --
    checked via feature_specs.require_compatible before every run, so a
    schema/model mismatch fails before any database write."""

    def fit(self, train_matches: list[CompletedMatch]) -> Predictor: ...

    def hyperparams(self) -> dict:
        """The run-configuration a family was given, recorded on
        experiment_runs.hyperparams before fitting -- distinct from the
        fitted state a Predictor exposes through params() afterward."""
        ...


def match_result(match: CompletedMatch) -> elo.MatchResult:
    return elo.MatchResult(
        athlete_a_id=match.athlete_a_id,
        athlete_b_id=match.athlete_b_id,
        athlete_a_won=match.result_a == "win",
    )


class EloPredictor:
    def __init__(self, ratings: dict[int, float]):
        self._ratings = ratings

    def predict(self, match: CompletedMatch) -> float:
        rating_a = self._ratings.get(match.athlete_a_id, elo.DEFAULT_RATING)
        rating_b = self._ratings.get(match.athlete_b_id, elo.DEFAULT_RATING)
        return elo.predict(rating_a, rating_b)

    def params(self) -> dict:
        return {str(athlete_id): rating for athlete_id, rating in self._ratings.items()}


class EloFamily:
    """Thin adapter: identical behavior to calling elo.fit/elo.predict
    directly, just behind the common interface."""

    representation_kind = "rating"

    def __init__(self, k_factor: float = elo.DEFAULT_K_FACTOR):
        self.k_factor = k_factor

    def fit(self, train_matches: list[CompletedMatch]) -> Predictor:
        results = [match_result(match) for match in train_matches]
        ratings = elo.fit(results, k_factor=self.k_factor)
        return EloPredictor(ratings)

    def hyperparams(self) -> dict:
        return {"k_factor": self.k_factor}


MODEL_FAMILIES: dict[str, ModelFamily] = {
    "elo": EloFamily(),
    "glicko2": Glicko2Family(),
    "bradley_terry": BradleyTerryFamily(),
    "logreg": LogRegFamily(),
}

try:
    from prediction.tabpfn_family import TABPFN_AVAILABLE, TabPFNFamily

    if TABPFN_AVAILABLE:
        MODEL_FAMILIES["tabpfn"] = TabPFNFamily()
except ImportError:  # pragma: no cover - tabpfn_family itself has no hard import
    pass
