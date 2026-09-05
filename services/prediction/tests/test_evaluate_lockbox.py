from datetime import date
from pathlib import Path

import pytest

from conftest import seed_completed_match
from prediction import evaluate_lockbox as evaluate_lockbox_module
from prediction.evaluate_lockbox import evaluate_lockbox
from prediction.folds import seed_lockbox
from prediction.run_baseline import get_or_create_rolling_origin_protocol

REPO_ROOT = Path(__file__).resolve().parents[3]


def _seeded_lockbox(connection) -> str:
    for index in range(2):
        seed_completed_match(
            connection,
            event_slug=f"pre-lockbox-{index}",
            held_on=date(2026, index + 1, 1),
            athlete_a=f"A{index}",
            athlete_b=f"B{index}",
        )
    lockbox_event_id, _ = seed_completed_match(
        connection,
        event_slug="the-lockbox-event",
        held_on=date(2027, 1, 1),
        athlete_a="Lockbox A",
        athlete_b="Lockbox B",
    )
    protocol_name = "lockbox_under_test"
    seed_lockbox(connection, name=protocol_name, kind="lockbox_retrospective", event_ids=[lockbox_event_id])
    return protocol_name


@pytest.mark.integration
def test_evaluate_lockbox_refuses_on_a_dirty_working_tree(connection, monkeypatch):
    protocol_name = _seeded_lockbox(connection)
    monkeypatch.setattr(evaluate_lockbox_module, "get_git_info", lambda repo_root: ("deadbeef", True))

    with pytest.raises(RuntimeError, match="dirty working tree"):
        evaluate_lockbox(connection, protocol_name, repo_root=REPO_ROOT)

    with connection.cursor() as cursor:
        cursor.execute("select count(*) from experiment_runs")
        assert cursor.fetchone()[0] == 0


@pytest.mark.integration
def test_evaluate_lockbox_refuses_a_non_lockbox_protocol(connection, monkeypatch):
    monkeypatch.setattr(evaluate_lockbox_module, "get_git_info", lambda repo_root: ("deadbeef", False))
    for index in range(3):
        seed_completed_match(
            connection,
            event_slug=f"event-{index}",
            held_on=date(2026, index + 1, 1),
            athlete_a=f"A{index}",
            athlete_b=f"B{index}",
        )
    lockbox_event_id, _ = seed_completed_match(
        connection, event_slug="lockbox", held_on=date(2027, 1, 1), athlete_a="LA", athlete_b="LB"
    )
    seed_lockbox(connection, name="a-lockbox", kind="lockbox_retrospective", event_ids=[lockbox_event_id])
    protocol_id = get_or_create_rolling_origin_protocol(connection, "rolling_origin_test", min_training_events=1)
    with connection.cursor() as cursor:
        cursor.execute("select name from eval_protocols where id = %s", (protocol_id,))
        (protocol_name,) = cursor.fetchone()

    with pytest.raises(ValueError, match="not a lockbox"):
        evaluate_lockbox(connection, protocol_name, repo_root=REPO_ROOT)


@pytest.mark.integration
def test_evaluate_lockbox_dry_run_writes_nothing_and_reports_the_current_count(connection, monkeypatch):
    monkeypatch.setattr(evaluate_lockbox_module, "get_git_info", lambda repo_root: ("deadbeef", False))
    protocol_name = _seeded_lockbox(connection)

    result = evaluate_lockbox(connection, protocol_name, dry_run=True, repo_root=REPO_ROOT)

    assert result["dry_run"] is True
    assert result["run_id"] is None
    assert result["consultations_before"] == 0
    assert result["consultations_after"] == 0
    assert result["train_match_count"] == 2
    assert result["test_match_count"] == 1
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from experiment_runs")
        assert cursor.fetchone()[0] == 0


@pytest.mark.integration
def test_evaluate_lockbox_consultation_count_increments_by_exactly_one_per_call(connection, monkeypatch):
    protocol_name = _seeded_lockbox(connection)
    monkeypatch.setattr(evaluate_lockbox_module, "get_git_info", lambda repo_root: ("deadbeef", False))

    first = evaluate_lockbox(connection, protocol_name, repo_root=REPO_ROOT)
    second = evaluate_lockbox(connection, protocol_name, model_family="glicko2", repo_root=REPO_ROOT)

    assert first["consultations_before"] == 0
    assert first["consultations_after"] == 1
    assert second["consultations_before"] == 1
    assert second["consultations_after"] == 2
    assert first["run_id"] != second["run_id"]
