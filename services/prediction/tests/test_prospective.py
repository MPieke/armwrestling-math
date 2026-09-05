from datetime import date

import pytest

from conftest import seed_completed_match
from prediction.folds import seed_lockbox
from prediction.prospective import add_prospective_event


@pytest.mark.integration
def test_add_prospective_event_includes_all_matches_and_is_idempotent(connection):
    lockbox_event_id, _ = seed_completed_match(
        connection,
        event_slug="initial-lockbox",
        held_on=date(2026, 1, 1),
        athlete_a="Initial A",
        athlete_b="Initial B",
    )
    seed_lockbox(
        connection,
        name="prospective_v1",
        kind="lockbox_prospective",
        event_ids=[lockbox_event_id],
    )
    _, target_match_id = seed_completed_match(
        connection,
        event_slug="future-event",
        held_on=date(2026, 2, 1),
        athlete_a="Future A",
        athlete_b="Future B",
    )
    with connection.cursor() as cursor:
        cursor.execute("update matches set status = 'scheduled' where id = %s", (target_match_id,))
    connection.commit()

    first_ids = add_prospective_event(connection, "prospective_v1", "future-event")
    second_ids = add_prospective_event(connection, "prospective_v1", "future-event")

    assert first_ids == [target_match_id]
    assert second_ids == []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select f.test_match_ids
            from eval_folds f join eval_protocols p on p.id = f.protocol_id
            where p.name = 'prospective_v1'
            """
        )
        (test_match_ids,) = cursor.fetchone()
    assert test_match_ids.count(target_match_id) == 1
