"""Hand-rolled Glicko-2 (Glickman, "Example of the Glicko-2 system"), kept
dependency-free and white-box rather than pulled from a library.

glicko2_update implements one full rating period (the paper's steps 3-8)
over an arbitrary number of simultaneous results, and is tested directly
against the paper's own worked example. Glicko2Family.fit calls it once per
match, sequentially, with a single-result list -- each match becomes its
own one-game rating period, applied chronologically. That is a deliberate
choice to match how elo.fit already walks a fold (a debuting opponent's
rating stays visible to every later match in the same fold), not an
approximation of the paper's multi-opponent period, which glicko2_update
supports directly and is exactly what its own unit test exercises.
"""

from __future__ import annotations

import math

from prediction.db import CompletedMatch

GLICKO2_SCALE = 173.7178
DEFAULT_MU = 0.0
DEFAULT_PHI = 350.0 / GLICKO2_SCALE
DEFAULT_SIGMA = 0.06
_SYSTEM_CONSTANT_TAU = 0.5
_CONVERGENCE_EPSILON = 1e-6


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi**2 / math.pi**2)


def _expected_score(mu: float, opp_mu: float, opp_phi: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g(opp_phi) * (mu - opp_mu)))


def glicko2_update(
    mu: float,
    phi: float,
    sigma: float,
    results: list[tuple[float, float, float]],
) -> tuple[float, float, float]:
    """results is a list of (opponent_mu, opponent_phi, score), score in
    {0.0, 1.0}. Returns the updated (mu, phi, sigma) after this rating
    period. An empty results list is step 7's no-games case: only phi
    grows (uncertainty increases), mu and sigma are unchanged."""
    if not results:
        return mu, math.sqrt(phi**2 + sigma**2), sigma

    variance_inverse = 0.0
    delta_sum = 0.0
    for opponent_mu, opponent_phi, score in results:
        g_opponent = _g(opponent_phi)
        expected = _expected_score(mu, opponent_mu, opponent_phi)
        variance_inverse += g_opponent**2 * expected * (1.0 - expected)
        delta_sum += g_opponent * (score - expected)
    variance = 1.0 / variance_inverse
    delta = variance * delta_sum

    new_sigma = _new_volatility(phi, sigma, variance, delta)
    phi_star = math.sqrt(phi**2 + new_sigma**2)
    new_phi = 1.0 / math.sqrt(1.0 / phi_star**2 + 1.0 / variance)
    new_mu = mu + new_phi**2 * delta_sum
    return new_mu, new_phi, new_sigma


def _new_volatility(phi: float, sigma: float, variance: float, delta: float) -> float:
    """Step 5's iterative (Illinois/regula falsi) solve for the new
    volatility, exactly as the paper specifies."""

    def f(x: float) -> float:
        ex = math.exp(x)
        numerator = ex * (delta**2 - phi**2 - variance - ex)
        denominator = 2.0 * (phi**2 + variance + ex) ** 2
        return numerator / denominator - (x - a) / _SYSTEM_CONSTANT_TAU**2

    a = math.log(sigma**2)
    upper = a
    if delta**2 > phi**2 + variance:
        lower = math.log(delta**2 - phi**2 - variance)
    else:
        k = 1
        while f(a - k * _SYSTEM_CONSTANT_TAU) < 0:
            k += 1
        lower = a - k * _SYSTEM_CONSTANT_TAU

    f_upper, f_lower = f(upper), f(lower)
    while abs(lower - upper) > _CONVERGENCE_EPSILON:
        midpoint = upper + (upper - lower) * f_upper / (f_lower - f_upper)
        f_midpoint = f(midpoint)
        if f_midpoint * f_lower < 0:
            upper, f_upper = lower, f_lower
        else:
            f_upper = f_upper / 2.0
        lower, f_lower = midpoint, f_midpoint
    return math.exp(upper / 2.0)


def expected_win_probability(mu_a: float, phi_a: float, mu_b: float, phi_b: float) -> float:
    """Match win probability from two independent Glicko-2 states, using
    the combined-deviation form (sqrt(phi_a^2 + phi_b^2)) recommended for
    comparing two rated players rather than scoring one player's single
    game, where only the opponent's phi enters."""
    combined_phi = math.sqrt(phi_a**2 + phi_b**2)
    return _expected_score(mu_a, mu_b, combined_phi)


def to_glicko2_scale(rating: float, rd: float) -> tuple[float, float]:
    return (rating - 1500.0) / GLICKO2_SCALE, rd / GLICKO2_SCALE


def to_original_scale(mu: float, phi: float) -> tuple[float, float]:
    return 1500.0 + mu * GLICKO2_SCALE, phi * GLICKO2_SCALE


class Glicko2Predictor:
    def __init__(self, states: dict[int, tuple[float, float, float]]):
        self._states = states

    def predict(self, match: CompletedMatch) -> float:
        mu_a, phi_a, _ = self._states.get(
            match.athlete_a_id, (DEFAULT_MU, DEFAULT_PHI, DEFAULT_SIGMA)
        )
        mu_b, phi_b, _ = self._states.get(
            match.athlete_b_id, (DEFAULT_MU, DEFAULT_PHI, DEFAULT_SIGMA)
        )
        return expected_win_probability(mu_a, phi_a, mu_b, phi_b)

    def params(self) -> dict:
        params = {}
        for athlete_id, (mu, phi, sigma) in self._states.items():
            rating, rd = to_original_scale(mu, phi)
            params[str(athlete_id)] = {"rating": rating, "rd": rd, "sigma": sigma}
        return params


class Glicko2Family:
    def hyperparams(self) -> dict:
        return {}

    def fit(self, train_matches: list[CompletedMatch]) -> "Glicko2Predictor":
        states: dict[int, tuple[float, float, float]] = {}
        for match in train_matches:
            mu_a, phi_a, sigma_a = states.get(
                match.athlete_a_id, (DEFAULT_MU, DEFAULT_PHI, DEFAULT_SIGMA)
            )
            mu_b, phi_b, sigma_b = states.get(
                match.athlete_b_id, (DEFAULT_MU, DEFAULT_PHI, DEFAULT_SIGMA)
            )
            score_a = 1.0 if match.result_a == "win" else 0.0
            new_a = glicko2_update(mu_a, phi_a, sigma_a, [(mu_b, phi_b, score_a)])
            new_b = glicko2_update(mu_b, phi_b, sigma_b, [(mu_a, phi_a, 1.0 - score_a)])
            states[match.athlete_a_id] = new_a
            states[match.athlete_b_id] = new_b
        return Glicko2Predictor(states)
