from datetime import date
from pathlib import Path

import pytest

from conftest import seed_completed_match
from prediction.run_baseline import get_or_create_rolling_origin_protocol, is_promotable, run_baseline

REPO_ROOT = Path(__file__).resolve().parents[3]


def _seed_four_events(connection):
    for i in range(4):
        seed_completed_match(
            connection,
            event_slug=f"event-{i}",
            held_on=date(2026, i + 1, 1),
            athlete_a=f"A{i}",
            athlete_b=f"B{i}",
        )


@pytest.mark.integration
def test_run_baseline_creates_one_completed_run_with_correct_git_dirty(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(connection, "rolling_origin_test", min_training_events=2)

    run_id = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute("select status, git_sha, git_dirty from experiment_runs where id = %s", (run_id,))
        status, git_sha, git_dirty = cursor.fetchone()
    assert status == "completed"
    assert len(git_sha) == 40
    assert isinstance(git_dirty, bool)


@pytest.mark.integration
def test_run_baseline_records_two_complementary_predictions_per_test_match(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(connection, "rolling_origin_test", min_training_events=2)

    run_id = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute(
            "select match_id, array_agg(p_win order by athlete_id) from run_predictions where run_id = %s group by match_id",
            (run_id,),
        )
        rows = cursor.fetchall()
    assert len(rows) == 2  # two test folds (events 2 and 3), one match each
    for _, p_wins in rows:
        assert len(p_wins) == 2
        assert abs(sum(p_wins) - 1.0) < 1e-9


@pytest.mark.integration
def test_run_baseline_records_a_rating_for_every_athlete_seen_in_training(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(connection, "rolling_origin_test", min_training_events=2)

    run_id = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute("select params from run_models where run_id = %s", (run_id,))
        (params,) = cursor.fetchone()
        # Athletes from events 0 and 1 (the training data for the last fold).
        cursor.execute("select id, canonical_name from athletes where canonical_name in ('A0','B0','A1','B1')")
        training_athletes = dict(cursor.fetchall())

    for athlete_id in training_athletes:
        assert str(athlete_id) in params


def test_is_promotable_rejects_a_dirty_working_tree():
    assert is_promotable(git_dirty=False) is True
    assert is_promotable(git_dirty=True) is False
