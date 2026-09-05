"""Bradley-Terry via choix, refit fresh per fold.

A batch MLE over one fold's train_matches is not the leakage a single
global fit would be: every match in a fold's training set is already
pre-cutoff by construction (folds.generate_rolling_origin), so fitting
"all of it at once" here uses no information a sequential walk wouldn't
also have had by the end of the fold. It differs from Elo/Glicko-2 only in
*how* it uses that already-legal set (one MLE instead of a sequential
walk), not in *what* it's allowed to see.
"""

from __future__ import annotations

import math

import choix

from prediction.db import CompletedMatch

L2_REGULARIZATION = 1.0
DEFAULT_STRENGTH = 0.0


def bt_fit(train_matches: list[CompletedMatch]) -> dict[int, float]:
    athlete_ids = sorted(
        {match.athlete_a_id for match in train_matches}
        | {match.athlete_b_id for match in train_matches}
    )
    if not athlete_ids:
        return {}
    index_by_athlete = {athlete_id: index for index, athlete_id in enumerate(athlete_ids)}
    comparisons = [
        (index_by_athlete[_winner(match)], index_by_athlete[_loser(match)])
        for match in train_matches
    ]
    strengths = choix.opt_pairwise(len(athlete_ids), comparisons, alpha=L2_REGULARIZATION)
    return {athlete_ids[index]: float(strengths[index]) for index in range(len(athlete_ids))}


def _winner(match: CompletedMatch) -> int:
    return match.athlete_a_id if match.result_a == "win" else match.athlete_b_id


def _loser(match: CompletedMatch) -> int:
    return match.athlete_b_id if match.result_a == "win" else match.athlete_a_id


def bt_predict(theta_a: float, theta_b: float) -> float:
    return 1.0 / (1.0 + math.exp(-(theta_a - theta_b)))


class BradleyTerryPredictor:
    def __init__(self, strengths: dict[int, float]):
        self._strengths = strengths

    def predict(self, match: CompletedMatch) -> float:
        theta_a = self._strengths.get(match.athlete_a_id, DEFAULT_STRENGTH)
        theta_b = self._strengths.get(match.athlete_b_id, DEFAULT_STRENGTH)
        return bt_predict(theta_a, theta_b)

    def params(self) -> dict:
        return {str(athlete_id): theta for athlete_id, theta in self._strengths.items()}


class BradleyTerryFamily:
    representation_kind = "rating"

    def hyperparams(self) -> dict:
        return {"l2_regularization": L2_REGULARIZATION}

    def fit(self, train_matches: list[CompletedMatch]) -> "BradleyTerryPredictor":
        return BradleyTerryPredictor(bt_fit(train_matches))
