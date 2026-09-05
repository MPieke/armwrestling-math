from prediction.elo import DEFAULT_RATING, MatchResult, fit, predict


def test_equal_ratings_predict_even_odds():
    assert predict(1500.0, 1500.0) == 0.5


def test_higher_rating_predicts_higher_win_probability_monotonically():
    baseline = predict(1500.0, 1500.0)
    small_gap = predict(1600.0, 1500.0)
    large_gap = predict(1800.0, 1500.0)
    assert baseline < small_gap < large_gap


def test_large_rating_gap_never_reaches_zero_or_one():
    probability = predict(3000.0, 100.0)
    assert 0.0 < probability < 1.0
    probability = predict(100.0, 3000.0)
    assert 0.0 < probability < 1.0


def test_fit_on_empty_match_list_returns_no_ratings():
    assert fit([]) == {}


def test_fit_returns_default_rating_for_a_debuting_athlete():
    ratings = fit([MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=True)])
    # Both athletes had no prior matches; both start from the default before
    # this match adjusts them -- neither raises for lack of history.
    assert 1 in ratings and 2 in ratings


def test_fit_moves_winner_rating_up_and_loser_rating_down_from_equal_start():
    ratings = fit([MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=True)])
    assert ratings[1] > DEFAULT_RATING > ratings[2]


def test_fit_is_order_dependent_for_nonzero_k_factor():
    forward = fit(
        [
            MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=True),
            MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=False),
        ],
        k_factor=32.0,
    )
    backward = fit(
        [
            MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=False),
            MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=True),
        ],
        k_factor=32.0,
    )
    # Ratings converge back toward each other either way, but the
    # intermediate path differs -- proving ratings are updated match by
    # match, not as a simultaneous (Bradley-Terry-style) fit.
    assert forward != backward


def test_fit_is_order_independent_when_k_factor_is_zero():
    matches = [
        MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=True),
        MatchResult(athlete_a_id=1, athlete_b_id=2, athlete_a_won=False),
    ]
    forward = fit(matches, k_factor=0.0)
    backward = fit(list(reversed(matches)), k_factor=0.0)
    assert forward == backward == {1: DEFAULT_RATING, 2: DEFAULT_RATING}
