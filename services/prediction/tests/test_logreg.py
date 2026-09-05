from datetime import datetime, timedelta, timezone

from prediction.db import CompletedMatch
from prediction.logreg import LogRegFamily, LogRegPredictor, _ConstantPredictor

DAY = timedelta(days=1)
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _match(match_id, athlete_a_id, athlete_b_id, result_a, day_offset, weight_class="105 kg"):
    return CompletedMatch(
        match_id=match_id,
        event_id=0,
        scheduled_at=START + day_offset * DAY,
        arm="right",
        weight_class=weight_class,
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        result_a=result_a,
    )


def _mixed_outcome_matches():
    return [
        _match(1, 1, 2, "win", 0),
        _match(2, 3, 4, "loss", 1),
        _match(3, 1, 3, "win", 2),
        _match(4, 2, 4, "loss", 3),
        _match(5, 1, 4, "win", 4),
        _match(6, 2, 3, "loss", 5),
    ]


def test_logreg_family_fits_a_real_predictor_on_a_mixed_outcome_fold():
    predictor = LogRegFamily().fit(_mixed_outcome_matches())

    assert isinstance(predictor, LogRegPredictor)
    p_win = predictor.predict(_match(7, 1, 2, "win", 6))
    assert 0.0 <= p_win <= 1.0


def test_logreg_predictor_coefficients_have_interpretable_names():
    predictor = LogRegFamily().fit(_mixed_outcome_matches())

    params = predictor.params()

    assert "prior_rating_a" in params
    assert "arm=right" in params
    assert "weight_class=105 kg" in params
    assert "intercept" in params


def test_logreg_family_falls_back_to_constant_predictor_for_a_single_class_fold():
    all_wins = [_match(1, 1, 2, "win", 0), _match(2, 1, 3, "win", 1)]

    predictor = LogRegFamily().fit(all_wins)

    assert isinstance(predictor, _ConstantPredictor)
    assert predictor.predict(_match(3, 1, 4, "win", 2)) == 0.5


def test_logreg_family_is_deterministic_across_repeated_fits():
    matches = _mixed_outcome_matches()

    first = LogRegFamily().fit(matches).params()
    second = LogRegFamily().fit(matches).params()

    assert first == second


def test_logreg_predictor_handles_an_unseen_weight_class_at_test_time():
    predictor = LogRegFamily().fit(_mixed_outcome_matches())

    p_win = predictor.predict(_match(7, 1, 2, "win", 6, weight_class="Open category"))

    assert 0.0 <= p_win <= 1.0
