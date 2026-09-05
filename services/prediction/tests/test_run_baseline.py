from datetime import date
from pathlib import Path

import pytest

from conftest import seed_completed_match
from prediction.folds import seed_lockbox
from prediction.run_baseline import (
    get_or_create_rolling_origin_protocol,
    is_promotable,
    run_baseline,
)

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
    lockbox_event_id, _ = seed_completed_match(
        connection,
        event_slug="reserved-lockbox",
        held_on=date(2027, 1, 1),
        athlete_a="Lockbox A",
        athlete_b="Lockbox B",
    )
    seed_lockbox(
        connection,
        name="lockbox_retrospective_test",
        kind="lockbox_retrospective",
        event_ids=[lockbox_event_id],
    )


@pytest.mark.integration
def test_rolling_origin_requires_a_lockbox_before_creation(connection):
    for index in range(3):
        seed_completed_match(
            connection,
            event_slug=f"unguarded-{index}",
            held_on=date(2026, index + 1, 1),
            athlete_a=f"A{index}",
            athlete_b=f"B{index}",
        )

    with pytest.raises(ValueError, match="lockbox protocol must be seeded"):
        get_or_create_rolling_origin_protocol(
            connection, "rolling_origin_test", min_training_events=1
        )


@pytest.mark.integration
def test_run_baseline_creates_one_completed_run_with_correct_git_dirty(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

    run_id = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            select r.status, r.git_sha, r.git_dirty, fs.name, fs.version,
                   m.data_summary, count(f.*)
            from experiment_runs r
            join feature_specs fs on fs.id = r.feature_spec_id
            join run_input_manifests m on m.run_id = r.id
            left join run_feature_rows f on f.run_id = r.id
            where r.id = %s
            group by r.status, r.git_sha, r.git_dirty, fs.name, fs.version, m.data_summary
            """,
            (run_id,),
        )
        status, git_sha, git_dirty, feature_name, feature_version, data_summary, input_row_count = (
            cursor.fetchone()
        )
    assert status == "completed"
    assert len(git_sha) == 40
    assert isinstance(git_dirty, bool)
    assert (feature_name, feature_version) == ("outcomes_elo", 1)
    assert data_summary == {"feature_rows": 7, "roles": {"test": 2, "train": 5}}
    assert input_row_count == 7


@pytest.mark.integration
def test_run_baseline_records_two_complementary_predictions_per_test_match(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

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
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

    run_id = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute("select params from run_models where run_id = %s", (run_id,))
        (params,) = cursor.fetchone()
        # Athletes from events 0 and 1 (the training data for the last fold).
        cursor.execute(
            "select id, canonical_name from athletes where canonical_name in ('A0','B0','A1','B1')"
        )
        training_athletes = dict(cursor.fetchall())

    for athlete_id in training_athletes:
        assert str(athlete_id) in params


@pytest.mark.integration
def test_run_baseline_rejects_a_schema_the_elo_model_cannot_consume(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into feature_specs (name, version, representation_kind, definition, definition_sha256)
            values ('tabular_history', 1, 'tabular', '{}', repeat('f', 64))
            """
        )

    with pytest.raises(ValueError, match="does not support tabular"):
        run_baseline(
            connection,
            protocol_id,
            feature_schema="tabular_history_v1",
            repo_root=REPO_ROOT,
        )

    with connection.cursor() as cursor:
        cursor.execute("select count(*) from experiment_runs")
        assert cursor.fetchone()[0] == 0


def test_is_promotable_rejects_a_dirty_working_tree():
    assert is_promotable(git_dirty=False) is True
    assert is_promotable(git_dirty=True) is False


@pytest.mark.integration
@pytest.mark.parametrize(
    "model_family,expected_hyperparam_keys",
    [
        ("elo", {"k_factor"}),
        ("glicko2", set()),
        ("bradley_terry", {"l2_regularization"}),
    ],
)
def test_run_baseline_supports_every_registered_model_family(
    connection, model_family, expected_hyperparam_keys
):
    """CLI/run_baseline wiring, not the family's own math (that's
    test_model_families.py, test_glicko2.py, test_bradley_terry.py): proves
    report can show any family's basis with no family-specific branching."""
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

    run_id = run_baseline(connection, protocol_id, model_family=model_family, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute(
            "select model_family, hyperparams, status from experiment_runs where id = %s",
            (run_id,),
        )
        family, hyperparams, status = cursor.fetchone()
        cursor.execute("select params from run_models where run_id = %s", (run_id,))
        (params,) = cursor.fetchone()
    assert status == "completed"
    assert family == model_family
    assert set(hyperparams) == expected_hyperparam_keys
    assert params


@pytest.mark.integration
def test_run_baseline_rejects_an_unknown_model_family_before_creating_a_run(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

    with pytest.raises(ValueError, match="unknown model family"):
        run_baseline(connection, protocol_id, model_family="neural_net", repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute("select count(*) from experiment_runs")
        assert cursor.fetchone()[0] == 0


@pytest.mark.integration
def test_run_baseline_supports_logreg_over_the_tabular_history_schema(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

    run_id = run_baseline(
        connection,
        protocol_id,
        model_family="logreg",
        feature_schema="history_v1",
        repo_root=REPO_ROOT,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "select status, fs.representation_kind from experiment_runs r "
            "join feature_specs fs on fs.id = r.feature_spec_id where r.id = %s",
            (run_id,),
        )
        status, representation_kind = cursor.fetchone()
        cursor.execute(
            "select payload from run_feature_rows where run_id = %s and role = 'train' limit 1",
            (run_id,),
        )
        (train_payload,) = cursor.fetchone()
    assert status == "completed"
    assert representation_kind == "tabular"
    assert "features" in train_payload and "label" in train_payload


@pytest.mark.integration
def test_run_baseline_rejects_logreg_against_the_rating_only_schema(connection):
    _seed_four_events(connection)
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )

    with pytest.raises(ValueError, match="does not support rating"):
        run_baseline(connection, protocol_id, model_family="logreg", repo_root=REPO_ROOT)
