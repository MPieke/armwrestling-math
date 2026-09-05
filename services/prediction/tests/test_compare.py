from datetime import date
from pathlib import Path

import pytest

from conftest import seed_completed_match
from prediction.compare import compare
from prediction.folds import seed_lockbox
from prediction.run_baseline import get_or_create_rolling_origin_protocol, run_baseline

REPO_ROOT = Path(__file__).resolve().parents[3]


def _seeded_protocol(connection, protocol_name: str) -> int:
    for index in range(4):
        seed_completed_match(
            connection,
            event_slug=f"{protocol_name}-event-{index}",
            held_on=date(2026, index + 1, 1),
            athlete_a=f"{protocol_name}-A{index}",
            athlete_b=f"{protocol_name}-B{index}",
        )
    lockbox_event_id, _ = seed_completed_match(
        connection,
        event_slug=f"{protocol_name}-lockbox",
        held_on=date(2027, 1, 1),
        athlete_a=f"{protocol_name}-Lockbox A",
        athlete_b=f"{protocol_name}-Lockbox B",
    )
    seed_lockbox(
        connection,
        name=f"{protocol_name}-lockbox",
        kind="lockbox_retrospective",
        event_ids=[lockbox_event_id],
    )
    return get_or_create_rolling_origin_protocol(connection, protocol_name, min_training_events=2)


@pytest.mark.integration
def test_compare_refuses_two_runs_on_different_protocols(connection):
    protocol_a = _seeded_protocol(connection, "protocol-a")
    protocol_b = _seeded_protocol(connection, "protocol-b")
    run_a = run_baseline(connection, protocol_a, repo_root=REPO_ROOT)
    run_b = run_baseline(connection, protocol_b, repo_root=REPO_ROOT)

    with pytest.raises(ValueError, match="not on the same protocol"):
        compare(connection, run_a, run_b)


@pytest.mark.integration
def test_compare_reports_full_scope_by_default(connection):
    protocol_id = _seeded_protocol(connection, "protocol")
    run_a = run_baseline(connection, protocol_id, k_factor=16.0, repo_root=REPO_ROOT)
    run_b = run_baseline(connection, protocol_id, k_factor=64.0, repo_root=REPO_ROOT)

    result = compare(connection, run_a, run_b)

    assert result["match_ids_restricted"] is False
    assert result["n"] == len(result["match_ids"]) == 2
    assert result["run_a"]["run_id"] == run_a
    assert result["run_b"]["run_id"] == run_b


@pytest.mark.integration
def test_compare_with_match_ids_restricts_to_exactly_that_subset(connection):
    protocol_id = _seeded_protocol(connection, "protocol")
    run_a = run_baseline(connection, protocol_id, k_factor=16.0, repo_root=REPO_ROOT)
    run_b = run_baseline(connection, protocol_id, k_factor=64.0, repo_root=REPO_ROOT)
    with connection.cursor() as cursor:
        cursor.execute(
            "select distinct match_id from run_predictions where run_id = %s order by match_id limit 1",
            (run_a,),
        )
        (one_match_id,) = cursor.fetchone()

    result = compare(connection, run_a, run_b, match_ids=[one_match_id])

    assert result["match_ids_restricted"] is True
    assert result["match_ids"] == [one_match_id]
    assert result["n"] == 1


@pytest.mark.integration
def test_compare_reports_promotability_of_both_runs(connection):
    protocol_id = _seeded_protocol(connection, "protocol")
    run_a = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)
    run_b = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)

    result = compare(connection, run_a, run_b)

    assert "promotable" in result["run_a"]
    assert "promotable" in result["run_b"]
