from datetime import datetime, timezone

import pytest

from prediction import elo
from prediction.bradley_terry import BradleyTerryFamily
from prediction.db import CompletedMatch
from prediction.glicko2 import Glicko2Family
from prediction.model_families import MODEL_FAMILIES, EloFamily


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


_FIXTURE_MATCHES = [
    _match(1, 2, "win"),
    _match(2, 3, "loss"),
    _match(1, 3, "win"),
    _match(3, 1, "win"),
]


def test_elo_family_matches_the_pre_refactor_elo_module_exactly():
    direct_ratings = elo.fit([elo.MatchResult(m.athlete_a_id, m.athlete_b_id, m.result_a == "win") for m in _FIXTURE_MATCHES])
    direct_p_win = elo.predict(
        direct_ratings.get(1, elo.DEFAULT_RATING), direct_ratings.get(2, elo.DEFAULT_RATING)
    )

    predictor = EloFamily().fit(_FIXTURE_MATCHES)

    assert predictor.params() == {
        str(athlete_id): rating for athlete_id, rating in direct_ratings.items()
    }
    assert predictor.predict(_match(1, 2, "win")) == pytest.approx(direct_p_win)


def test_model_families_registry_has_every_tier_a_and_tier_b_family():
    assert set(MODEL_FAMILIES) == {"elo", "glicko2", "bradley_terry", "logreg"}
    assert isinstance(MODEL_FAMILIES["glicko2"], Glicko2Family)
    assert isinstance(MODEL_FAMILIES["bradley_terry"], BradleyTerryFamily)


@pytest.mark.parametrize(
    "family_name,expected_keys",
    [
        ("elo", {"k_factor"}),
        ("glicko2", set()),
        ("bradley_terry", {"l2_regularization"}),
        ("logreg", set()),
    ],
)
def test_every_family_declares_its_own_hyperparams(family_name, expected_keys):
    assert set(MODEL_FAMILIES[family_name].hyperparams()) == expected_keys


@pytest.mark.parametrize("family_name", ["elo", "glicko2", "bradley_terry", "logreg"])
def test_every_family_is_stateless_across_fits(family_name):
    family = MODEL_FAMILIES[family_name]

    first = family.fit(_FIXTURE_MATCHES).params()
    second = family.fit(_FIXTURE_MATCHES).params()

    assert first == second
