"""Paired statistical comparison between two runs' predictions on the same
match set. Pure -- no database -- so the statistics themselves are unit
tested against synthetic data, independent of how the pairs were fetched.

At this project's data volume (n in the dozens to low hundreds), two point
estimates a few points apart are not distinguishable from noise by eye.
The bootstrap CI on the paired log-loss difference is the primary verdict
because it uses the full predicted probability, not just the thresholded
pick; McNemar's exact (binomial, not chi-square) test on the discordant
pairs is reported alongside as a corroborating, accuracy-specific view --
exact rather than the continuity-corrected approximation because the
discordant-pair counts here are small (dozens, not hundreds).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb, log
import random

DEFAULT_BOOTSTRAP_RESAMPLES = 2000
DEFAULT_BOOTSTRAP_SEED = 0
DEFAULT_ALPHA = 0.05
_LOG_LOSS_EPSILON = 1e-15


@dataclass(frozen=True)
class PairedPrediction:
    match_id: int
    athlete_a_won: bool
    p_win_a_run_a: float
    p_win_a_run_b: float


@dataclass(frozen=True)
class ComparisonResult:
    n: int
    accuracy_a: float
    accuracy_b: float
    mcnemar_discordant_pairs: tuple[int, int]  # (a_right_b_wrong, b_right_a_wrong)
    mcnemar_p_value: float
    log_loss_diff_ci: tuple[float, float]  # (a - b), paired bootstrap
    distinguishable: bool


def _log_loss(p_win_a: float, athlete_a_won: bool) -> float:
    p = p_win_a if athlete_a_won else (1.0 - p_win_a)
    p = min(max(p, _LOG_LOSS_EPSILON), 1.0 - _LOG_LOSS_EPSILON)
    return -log(p)


def _predicted_a_won(p_win_a: float) -> bool:
    return p_win_a >= 0.5


def mcnemar_exact_p_value(a_right_b_wrong: int, b_right_a_wrong: int) -> float:
    """Two-sided exact binomial test on the discordant pairs, p=0.5 under
    the null that the two runs are equally likely to be the one that's
    right when they disagree."""
    n = a_right_b_wrong + b_right_a_wrong
    if n == 0:
        return 1.0
    smaller = min(a_right_b_wrong, b_right_a_wrong)
    tail = sum(comb(n, i) for i in range(smaller + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def paired_log_loss_bootstrap_ci(
    pairs: list[PairedPrediction],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[float, float]:
    n = len(pairs)
    if n == 0:
        return (0.0, 0.0)
    diffs = [
        _log_loss(pair.p_win_a_run_a, pair.athlete_a_won)
        - _log_loss(pair.p_win_a_run_b, pair.athlete_a_won)
        for pair in pairs
    ]
    rng = random.Random(seed)
    resample_means = []
    for _ in range(resamples):
        resample_means.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    resample_means.sort()
    lower_index = int((alpha / 2) * resamples)
    upper_index = min(resamples - 1, int((1 - alpha / 2) * resamples))
    return resample_means[lower_index], resample_means[upper_index]


def compare_predictions(
    pairs: list[PairedPrediction],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> ComparisonResult:
    n = len(pairs)
    correct_a = sum(1 for p in pairs if _predicted_a_won(p.p_win_a_run_a) == p.athlete_a_won)
    correct_b = sum(1 for p in pairs if _predicted_a_won(p.p_win_a_run_b) == p.athlete_a_won)
    a_right_b_wrong = sum(
        1
        for p in pairs
        if _predicted_a_won(p.p_win_a_run_a) == p.athlete_a_won
        and _predicted_a_won(p.p_win_a_run_b) != p.athlete_a_won
    )
    b_right_a_wrong = sum(
        1
        for p in pairs
        if _predicted_a_won(p.p_win_a_run_b) == p.athlete_a_won
        and _predicted_a_won(p.p_win_a_run_a) != p.athlete_a_won
    )
    ci_lower, ci_upper = paired_log_loss_bootstrap_ci(pairs, resamples=resamples, seed=seed)
    return ComparisonResult(
        n=n,
        accuracy_a=correct_a / n if n else 0.0,
        accuracy_b=correct_b / n if n else 0.0,
        mcnemar_discordant_pairs=(a_right_b_wrong, b_right_a_wrong),
        mcnemar_p_value=mcnemar_exact_p_value(a_right_b_wrong, b_right_a_wrong),
        log_loss_diff_ci=(ci_lower, ci_upper),
        distinguishable=not (ci_lower <= 0.0 <= ci_upper),
    )
