from datetime import datetime, timedelta, timezone

import pytest

from prediction.db import CompletedMatch
from prediction.tabpfn_family import TABPFN_AVAILABLE, TabPFNFamily

DAY = timedelta(days=1)
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _match(match_id, athlete_a_id, athlete_b_id, result_a, day_offset):
    return CompletedMatch(
        match_id=match_id,
        event_id=0,
        scheduled_at=START + day_offset * DAY,
        arm="right",
        weight_class="105 kg",
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        result_a=result_a,
    )


def test_tabpfn_family_raises_a_clear_error_when_the_optional_dependency_is_missing():
    if TABPFN_AVAILABLE:
        pytest.skip("tabpfn is installed in this environment; nothing to guard against here")

    with pytest.raises(ImportError, match="tabpfn is not installed"):
        TabPFNFamily().fit([_match(1, 1, 2, "win", 0)])


@pytest.mark.skipif(not TABPFN_AVAILABLE, reason="requires `uv sync --extra tabpfn`")
def test_tabpfn_family_fits_a_real_predictor_on_a_mixed_outcome_fold():
    matches = [
        _match(1, 1, 2, "win", 0),
        _match(2, 3, 4, "loss", 1),
        _match(3, 1, 3, "win", 2),
        _match(4, 2, 4, "loss", 3),
    ]

    predictor = TabPFNFamily().fit(matches)
    p_win = predictor.predict(_match(5, 1, 2, "win", 4))

    assert 0.0 <= p_win <= 1.0
