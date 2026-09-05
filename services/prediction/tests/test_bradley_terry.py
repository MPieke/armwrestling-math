from datetime import datetime, timezone

from prediction.bradley_terry import BradleyTerryFamily, bt_fit, bt_predict
from prediction.db import CompletedMatch


def _match(athlete_a_id: int, athlete_b_id: int, result_a: str = "win") -> CompletedMatch:
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


def test_bt_fit_returns_no_strengths_for_no_matches():
    assert bt_fit([]) == {}


def test_bt_fit_gives_a_dominant_athlete_a_higher_strength():
    matches = [_match(1, 2, "win"), _match(1, 3, "win"), _match(2, 3, "win")]

    strengths = bt_fit(matches)

    assert strengths[1] > strengths[2] > strengths[3]


def test_bt_predict_is_monotonic_in_the_strength_gap():
    low = bt_predict(theta_a=-1.0, theta_b=0.0)
    mid = bt_predict(theta_a=0.0, theta_b=0.0)
    high = bt_predict(theta_a=1.0, theta_b=0.0)

    assert low < mid < high
    assert mid == 0.5


def test_bt_fit_keeps_probability_finite_for_an_all_one_sided_record():
    matches = [_match(1, 2, "win")] * 10

    strengths = bt_fit(matches)
    p_win = bt_predict(strengths[1], strengths[2])

    assert 0.0 < p_win < 1.0


def test_bradley_terry_family_is_deterministic_across_repeated_fits():
    matches = [_match(1, 2, "win"), _match(2, 3, "loss"), _match(1, 3, "win")]

    first = BradleyTerryFamily().fit(matches).params()
    second = BradleyTerryFamily().fit(matches).params()

    assert first == second


def test_bradley_terry_predictor_defaults_unseen_athletes_to_even_odds():
    predictor = BradleyTerryFamily().fit([_match(1, 2, "win")] * 5)

    p_win = predictor.predict(_match(3, 4, "win"))

    assert p_win == 0.5
