
import pytest

from prediction.glicko2 import (
    DEFAULT_MU,
    DEFAULT_PHI,
    DEFAULT_SIGMA,
    Glicko2Family,
    glicko2_update,
    to_glicko2_scale,
    to_original_scale,
)
from prediction.db import CompletedMatch
from datetime import datetime, timezone


def test_glicko2_update_reproduces_glickmans_worked_example():
    mu, phi = to_glicko2_scale(1500.0, 200.0)
    sigma = 0.06
    results = [
        (*to_glicko2_scale(1400.0, 30.0), 1.0),
        (*to_glicko2_scale(1550.0, 100.0), 0.0),
        (*to_glicko2_scale(1700.0, 300.0), 0.0),
    ]

    new_mu, new_phi, new_sigma = glicko2_update(mu, phi, sigma, results)

    new_rating, new_rd = to_original_scale(new_mu, new_phi)
    assert new_rating == pytest.approx(1464.06, abs=0.01)
    assert new_rd == pytest.approx(151.52, abs=0.01)
    assert new_sigma == pytest.approx(0.05999, abs=0.00001)


def test_glicko2_update_with_no_games_only_grows_uncertainty():
    mu, phi, sigma = 0.3, 1.0, 0.06

    new_mu, new_phi, new_sigma = glicko2_update(mu, phi, sigma, [])

    assert new_mu == mu
    assert new_sigma == sigma
    assert new_phi > phi


def test_glicko2_update_shrinks_deviation_after_a_game():
    mu, phi, sigma = DEFAULT_MU, DEFAULT_PHI, DEFAULT_SIGMA
    opponent_mu, opponent_phi = to_glicko2_scale(1500.0, 100.0)

    _, new_phi, _ = glicko2_update(mu, phi, sigma, [(opponent_mu, opponent_phi, 1.0)])

    assert new_phi < phi


def _match(athlete_a_id: int, athlete_b_id: int, result_a: str) -> CompletedMatch:
    return CompletedMatch(
        match_id=0,
        event_id=0,
        scheduled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        arm="right",
        weight_class="105 kg",
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        result_a=result_a,
    )


def test_glicko2_family_gives_a_debuting_athlete_the_documented_defaults():
    predictor = Glicko2Family().fit([])

    params = predictor.params()

    assert params == {}
    rating, rd = to_original_scale(DEFAULT_MU, DEFAULT_PHI)
    assert rating == pytest.approx(1500.0)
    assert rd == pytest.approx(350.0, abs=0.01)


def test_glicko2_family_is_deterministic_across_repeated_fits():
    matches = [_match(1, 2, "win"), _match(2, 3, "loss"), _match(1, 3, "win")]

    first = Glicko2Family().fit(matches).params()
    second = Glicko2Family().fit(matches).params()

    assert first == second


def test_glicko2_family_predict_never_claims_certainty():
    matches = [_match(1, 2, "win")] * 5

    predictor = Glicko2Family().fit(matches)
    p_win = predictor.predict(_match(1, 2, "win"))

    assert 0.0 < p_win < 1.0
