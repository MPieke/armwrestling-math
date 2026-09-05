from datetime import date
from pathlib import Path

import pytest

from conftest import seed_completed_match
from prediction.explain_prediction import build_prediction_explanation
from prediction.folds import seed_lockbox
from prediction.report import build_run_report
from prediction.run_baseline import get_or_create_rolling_origin_protocol, run_baseline

REPO_ROOT = Path(__file__).resolve().parents[3]


def _completed_run(connection) -> tuple[int, int]:
    for index in range(4):
        seed_completed_match(
            connection,
            event_slug=f"event-{index}",
            held_on=date(2026, index + 1, 1),
            athlete_a=f"A{index}",
            athlete_b=f"B{index}",
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
    protocol_id = get_or_create_rolling_origin_protocol(
        connection, "rolling_origin_test", min_training_events=2
    )
    run_id = run_baseline(connection, protocol_id, repo_root=REPO_ROOT)
    with connection.cursor() as cursor:
        cursor.execute("update experiment_runs set git_dirty = false where id = %s", (run_id,))
        cursor.execute(
            "select match_id from run_feature_rows where run_id = %s and role = 'test' order by match_id limit 1",
            (run_id,),
        )
        (test_match_id,) = cursor.fetchone()
    connection.commit()
    return run_id, test_match_id


def _ledger_counts(connection) -> dict[str, int]:
    tables = (
        "experiment_runs",
        "run_input_manifests",
        "run_feature_rows",
        "run_predictions",
        "run_models",
    )
    with connection.cursor() as cursor:
        return {
            table: cursor.execute(f"select count(*) from {table}").fetchone()[0] for table in tables
        }


@pytest.mark.integration
def test_report_and_explanation_reconstruct_persisted_inputs_without_writing(connection):
    run_id, test_match_id = _completed_run(connection)
    counts_before = _ledger_counts(connection)

    report = build_run_report(connection, run_id)
    explanation = build_prediction_explanation(connection, run_id, test_match_id)

    assert report["run"]["id"] == run_id
    assert report["feature_schema"]["name"] == "outcomes_elo"
    assert report["input_manifest"]["data_summary"]["feature_rows"] == 7
    assert len(report["folds"]) == 2
    assert report["run"]["promotable"] is True
    assert report["protocol"]["spec"] == {"min_training_events": 2}
    assert report["folds"][0]["test_event_dates"] == ["2026-03-01"]
    assert report["folds"][0]["predicted_match_count"] == 1
    assert len(report["predictions"]) == 4
    assert {prediction["outcome"] for prediction in report["predictions"]} == {"win", "loss"}
    assert report["model"]
    assert explanation["match_id"] == test_match_id
    assert explanation["test_inputs"]
    assert "athlete_a_won" not in explanation["test_inputs"][0]["payload"]
    assert len(explanation["predictions"]) == 2
    assert _ledger_counts(connection) == counts_before

    with connection.cursor() as cursor:
        cursor.execute("update matches set status = 'scheduled' where id = %s", (test_match_id,))
    connection.commit()
    report_without_outcome = build_run_report(connection, run_id)
    affected_predictions = [
        prediction
        for prediction in report_without_outcome["predictions"]
        if prediction["match_id"] == test_match_id
    ]
    assert len(affected_predictions) == 2
    assert all(prediction["outcome"] is None for prediction in affected_predictions)
