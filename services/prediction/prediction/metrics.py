"""Pure prediction-quality metrics. No database dependency."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoredPrediction:
    p_win_a: float
    athlete_a_won: bool


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """A confidence interval on a proportion that stays sane at small n,
    unlike a naive normal approximation."""
    if n == 0:
        return (0.0, 0.0)
    p_hat = successes / n
    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denominator
    margin = z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2)) / denominator
    return (center - margin, center + margin)


def compute_metrics(predictions: list[ScoredPrediction]) -> dict[str, float | int | None]:
    n = len(predictions)
    if n == 0:
        return {"n": 0, "accuracy": None, "log_loss": None, "brier_score": None}

    correct = sum(1 for p in predictions if (p.p_win_a >= 0.5) == p.athlete_a_won)
    log_loss = -sum(
        math.log(p.p_win_a if p.athlete_a_won else 1.0 - p.p_win_a) for p in predictions
    ) / n
    brier_score = sum(
        (p.p_win_a - (1.0 if p.athlete_a_won else 0.0)) ** 2 for p in predictions
    ) / n
    ci_lower, ci_upper = wilson_interval(correct, n)

    return {
        "n": n,
        "accuracy": correct / n,
        "accuracy_ci_lower": ci_lower,
        "accuracy_ci_upper": ci_upper,
        "log_loss": log_loss,
        "brier_score": brier_score,
    }
