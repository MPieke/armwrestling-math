"""Pure Elo rating computation. No database dependency, no side effects."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_RATING = 1500.0
DEFAULT_K_FACTOR = 24.0
RATING_SCALE = 400.0


@dataclass(frozen=True)
class MatchResult:
    """One completed match, in the shape elo.fit needs. Callers (folds.py,
    db.py) are responsible for producing these in chronological order."""

    athlete_a_id: int
    athlete_b_id: int
    athlete_a_won: bool


def predict(rating_a: float, rating_b: float) -> float:
    """Expected probability athlete A beats athlete B. Never exactly 0 or 1
    for a finite rating gap -- an Elo model must never claim certainty."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / RATING_SCALE))


def step(
    ratings: dict[int, float],
    match: MatchResult,
    k_factor: float = DEFAULT_K_FACTOR,
    default_rating: float = DEFAULT_RATING,
) -> dict[int, float]:
    """One match's rating update. Returns a new dict; `ratings` is read but
    never mutated, so a caller (point_in_time_features.py's inner loop, in
    particular) can safely read `ratings` as "state strictly before this
    match" right up until the moment it calls step()."""
    rating_a = ratings.get(match.athlete_a_id, default_rating)
    rating_b = ratings.get(match.athlete_b_id, default_rating)
    expected_a = predict(rating_a, rating_b)
    actual_a = 1.0 if match.athlete_a_won else 0.0
    delta = k_factor * (actual_a - expected_a)
    updated = dict(ratings)
    updated[match.athlete_a_id] = rating_a + delta
    updated[match.athlete_b_id] = rating_b - delta
    return updated


def fit(
    matches: list[MatchResult],
    k_factor: float = DEFAULT_K_FACTOR,
    default_rating: float = DEFAULT_RATING,
) -> dict[int, float]:
    """Sequentially fit ratings from an ordered list of matches.

    Matches must already be in chronological order. Ratings update match by
    match rather than as a simultaneous fit, so a debuting athlete (absent
    from every prior match) starts from `default_rating` instead of raising.
    """
    ratings: dict[int, float] = {}
    for match in matches:
        ratings = step(ratings, match, k_factor, default_rating)
    return ratings
