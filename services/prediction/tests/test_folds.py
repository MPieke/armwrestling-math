from datetime import date

import pytest

from conftest import seed_completed_match
from prediction import db
from prediction.folds import generate_rolling_origin, seed_lockbox


@pytest.mark.integration
def test_generates_one_fold_per_event_from_nth_onward_in_date_order(connection):
    for i in range(4):
        seed_completed_match(
            connection,
            event_slug=f"event-{i}",
            held_on=date(2026, i + 1, 1),
            athlete_a=f"A{i}",
            athlete_b=f"B{i}",
        )

    events = db.list_events(connection)
    matches = db.list_completed_matches(connection)
    folds = generate_rolling_origin(events, matches, min_training_events=2)

    assert [fold.fold_index for fold in folds] == [0, 1]
    matches_by_id = {m.match_id: m for m in matches}
    tested_events_in_order = [matches_by_id[fold.test_match_ids[0]].event_id for fold in folds]
    assert tested_events_in_order == [events[2].id, events[3].id]


@pytest.mark.integration
def test_never_leaks_a_same_or_later_event_match_into_training(connection):
    for i in range(3):
        seed_completed_match(
            connection,
            event_slug=f"event-{i}",
            held_on=date(2026, i + 1, 1),
            athlete_a=f"A{i}",
            athlete_b=f"B{i}",
        )

    events = db.list_events(connection)
    matches = db.list_completed_matches(connection)
    matches_by_id = {m.match_id: m for m in matches}
    folds = generate_rolling_origin(events, matches, min_training_events=1)

    assert len(folds) == 2
    for fold in folds:
        min_test_time = min(matches_by_id[mid].scheduled_at for mid in fold.test_match_ids)
        for train_id in fold.train_match_ids:
            assert matches_by_id[train_id].scheduled_at < min_test_time


@pytest.mark.integration
def test_events_already_in_a_lockbox_are_excluded_entirely(connection):
    event_ids = []
    for i in range(3):
        event_id, _ = seed_completed_match(
            connection,
            event_slug=f"event-{i}",
            held_on=date(2026, i + 1, 1),
            athlete_a=f"A{i}",
            athlete_b=f"B{i}",
        )
        event_ids.append(event_id)

    events = db.list_events(connection)
    matches = db.list_completed_matches(connection)
    matches_by_id = {m.match_id: m for m in matches}
    lockbox_event_id = event_ids[-1]

    folds = generate_rolling_origin(
        events, matches, min_training_events=1, excluded_event_ids={lockbox_event_id}
    )

    for fold in folds:
        for match_id in fold.train_match_ids + fold.test_match_ids:
            assert matches_by_id[match_id].event_id != lockbox_event_id


@pytest.mark.integration
def test_seed_lockbox_creates_one_fold_scoped_to_the_given_events(connection):
    _, earlier_match_id = seed_completed_match(
        connection,
        event_slug="before-lockbox",
        held_on=date(2025, 12, 1),
        athlete_a="Earlier A",
        athlete_b="Earlier B",
    )
    event_ids = []
    for i in range(2):
        event_id, _ = seed_completed_match(
            connection,
            event_slug=f"lockbox-{i}",
            held_on=date(2026, i + 1, 1),
            athlete_a=f"A{i}",
            athlete_b=f"B{i}",
        )
        event_ids.append(event_id)
    # An event NOT in the lockbox must not leak into its test set.
    seed_completed_match(
        connection, event_slug="not-lockbox", held_on=date(2026, 3, 1), athlete_a="C", athlete_b="D"
    )

    seed_lockbox(
        connection,
        name="lockbox_retrospective_v1",
        kind="lockbox_retrospective",
        event_ids=event_ids,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "select kind, spec from eval_protocols where name = 'lockbox_retrospective_v1'"
        )
        kind, spec = cursor.fetchone()
        cursor.execute(
            """
            select f.fold_index, f.train_match_ids, f.test_match_ids
            from eval_folds f join eval_protocols p on p.id = f.protocol_id
            where p.name = 'lockbox_retrospective_v1'
            """
        )
        rows = cursor.fetchall()

    assert kind == "lockbox_retrospective"
    assert spec["event_ids"] == event_ids
    assert len(rows) == 1
    fold_index, train_match_ids, test_match_ids = rows[0]
    assert fold_index == 0
    assert train_match_ids == [earlier_match_id]
    assert len(test_match_ids) == 2
