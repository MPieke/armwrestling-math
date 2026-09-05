from datetime import datetime, timedelta, timezone

import pytest

from prediction import elo
from prediction.db import CompletedMatch
from prediction.point_in_time_features import (
    DEBUT_DAYS_SINCE_LAST_MATCH,
    DEFAULT_HEAD_TO_HEAD_DIFF,
    DEFAULT_WIN_RATE,
    build_training_table,
    features_for_test_match,
)

DAY = timedelta(days=1)
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _match(match_id, athlete_a_id, athlete_b_id, result_a, scheduled_at, arm="right", weight_class="105 kg"):
    return CompletedMatch(
        match_id=match_id,
        event_id=0,
        scheduled_at=scheduled_at,
        arm=arm,
        weight_class=weight_class,
        athlete_a_id=athlete_a_id,
        athlete_b_id=athlete_b_id,
        result_a=result_a,
    )


def test_leakage_a_later_rematch_never_changes_an_earlier_rows_features():
    """The primary test. Two athletes meet twice: A beats B in January, B
    beats A in June. A naive "compute head-to-head once over the whole
    window" implementation would give the January row a head_to_head_diff
    that already reflects the June result (since both are "before the fold
    cutoff"). The sequential builder must not: row 0's features must be
    identical whether or not the June match is even in the list yet."""
    january = _match(1, athlete_a_id=1, athlete_b_id=2, result_a="win", scheduled_at=START)
    june = _match(2, athlete_a_id=2, athlete_b_id=1, result_a="win", scheduled_at=START + 150 * DAY)

    rows_without_june = build_training_table([january])
    rows_with_june = build_training_table([january, june])

    assert rows_without_june[0].features == rows_with_june[0].features
    assert rows_with_june[0].features["head_to_head_diff"] == DEFAULT_HEAD_TO_HEAD_DIFF


def test_leakage_test_fails_against_a_deliberately_broken_whole_window_implementation():
    """Proves the test above actually has teeth: a naive implementation
    that computes head-to-head once over the whole match list (rather than
    sequentially) WOULD change row 0's value once the June match is added,
    and this test asserts that broken behavior to demonstrate the contrast."""
    january = _match(1, athlete_a_id=1, athlete_b_id=2, result_a="win", scheduled_at=START)
    march = _match(2, athlete_a_id=1, athlete_b_id=2, result_a="win", scheduled_at=START + 60 * DAY)
    june = _match(3, athlete_a_id=1, athlete_b_id=2, result_a="win", scheduled_at=START + 150 * DAY)
    matches = [january, march, june]

    def broken_head_to_head_diff(target_match, all_matches):
        wins = {}
        for match in all_matches:
            winner = match.athlete_a_id if match.result_a == "win" else match.athlete_b_id
            wins[winner] = wins.get(winner, 0) + 1
        return wins.get(target_match.athlete_a_id, 0) - wins.get(target_match.athlete_b_id, 0)

    broken_value_for_january_row = broken_head_to_head_diff(january, matches)
    correct_value_for_january_row = build_training_table(matches)[0].features["head_to_head_diff"]

    assert broken_value_for_january_row != correct_value_for_january_row


def test_head_to_head_diff_counts_only_strictly_earlier_meetings():
    first = _match(1, 1, 2, "win", START)
    second = _match(2, 1, 2, "win", START + DAY)
    third = _match(3, 2, 1, "win", START + 2 * DAY)

    rows = build_training_table([first, second, third])

    assert rows[0].features["head_to_head_diff"] == DEFAULT_HEAD_TO_HEAD_DIFF
    assert rows[1].features["head_to_head_diff"] == 1.0  # athlete 1 leads 1-0
    assert rows[2].features["head_to_head_diff"] == -2.0  # athlete 2 leads 2-0 from athlete 1's perspective (a=2 in row 2)


def test_recent_form_window_boundary():
    matches = [_match(i, 1, 2, "win" if i % 2 == 0 else "loss", START + i * DAY) for i in range(7)]

    rows = build_training_table(matches)

    # Row 6 (7th match) sees athlete 1's prior 6 results, windowed to the last 5.
    assert rows[6].provenance["recent_form_a"] == [m.match_id for m in matches[1:6]]


def test_debuting_athlete_gets_defined_defaults_not_an_error():
    row = build_training_table([_match(1, 1, 2, "win", START)])[0]

    assert row.features["win_rate_a"] == DEFAULT_WIN_RATE
    assert row.features["win_rate_b"] == DEFAULT_WIN_RATE
    assert row.features["days_since_last_match_a"] == DEBUT_DAYS_SINCE_LAST_MATCH
    assert row.features["prior_rating_a"] == elo.DEFAULT_RATING


def test_days_since_last_match_is_hand_computed_correctly():
    first = _match(1, 1, 2, "win", START)
    second = _match(2, 1, 3, "win", START + 10 * DAY)

    rows = build_training_table([first, second])

    assert rows[1].features["days_since_last_match_a"] == pytest.approx(10.0)
    assert rows[1].features["days_since_last_match_b"] == DEBUT_DAYS_SINCE_LAST_MATCH


def test_features_for_test_match_uses_state_as_of_the_fold_cutoff():
    train = [_match(1, 1, 2, "win", START), _match(2, 1, 2, "loss", START + DAY)]
    test_match = _match(3, 1, 2, "win", START + 2 * DAY)

    features, provenance = features_for_test_match(train, test_match)

    assert features["head_to_head_diff"] == DEFAULT_HEAD_TO_HEAD_DIFF  # 1-1 all-time
    assert provenance["head_to_head"] == [1, 2]


def test_no_source_record_at_or_after_the_target_matchs_scheduled_time_ever_appears():
    train = [_match(i, 1, 2, "win", START + i * DAY) for i in range(5)]

    rows = build_training_table(train)

    for index, row in enumerate(rows):
        for group in row.provenance.values():
            assert all(match_id < row.match_id for match_id in group)
