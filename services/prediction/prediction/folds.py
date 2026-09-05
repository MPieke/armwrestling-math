"""Rolling-origin fold generation and lockbox seeding.

generate_rolling_origin is pure over the events/matches lists db.py returns
-- it decides fold membership but does not write anything, so the leakage
property (a fold's training set never includes a same-or-later-event match)
is directly testable against real seeded data without also exercising a
write path.

seed_lockbox is the one fold-generation path that writes to the database
directly: which events belong to a lockbox is a deliberate, rarely-repeated
human decision made at seeding time, not a mechanical computation to
unit-test the way rolling-origin generation is.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg

from prediction.db import CompletedMatch, Event


@dataclass(frozen=True)
class Fold:
    fold_index: int
    train_match_ids: list[int]
    test_match_ids: list[int]


def generate_rolling_origin(
    events: list[Event],
    completed_matches: list[CompletedMatch],
    min_training_events: int,
    excluded_event_ids: frozenset[int] = frozenset(),
) -> list[Fold]:
    """One fold per eligible event from the min_training_events'th onward:
    train = every match from a strictly earlier eligible event, test = that
    event's own matches. An event with no completed matches of its own
    contributes no fold (nothing to test). Events in excluded_event_ids
    (a lockbox) are removed from both training and testing entirely, so
    lockbox data never leaks into a dev fold's training set either.
    """
    eligible_events = [event for event in events if event.id not in excluded_event_ids]
    match_ids_by_event: dict[int, list[int]] = {}
    for match in completed_matches:
        if match.event_id in excluded_event_ids:
            continue
        match_ids_by_event.setdefault(match.event_id, []).append(match.match_id)

    folds: list[Fold] = []
    for position in range(min_training_events, len(eligible_events)):
        event = eligible_events[position]
        test_match_ids = match_ids_by_event.get(event.id, [])
        if not test_match_ids:
            continue
        train_match_ids = [
            match_id
            for earlier_event in eligible_events[:position]
            for match_id in match_ids_by_event.get(earlier_event.id, [])
        ]
        folds.append(
            Fold(fold_index=len(folds), train_match_ids=train_match_ids, test_match_ids=test_match_ids)
        )
    return folds


def seed_lockbox(connection: psycopg.Connection, *, name: str, kind: str, event_ids: list[int]) -> None:
    """Creates a lockbox protocol with a single fold whose test_match_ids
    are every completed match in the given events."""
    with connection.cursor() as cursor:
        cursor.execute(
            "insert into eval_protocols (name, kind) values (%s, %s) returning id", (name, kind)
        )
        (protocol_id,) = cursor.fetchone()
        cursor.execute(
            """
            select coalesce(array_agg(match_id order by match_id), '{}')
            from v_completed_matches
            where event_id = any(%s)
            """,
            (event_ids,),
        )
        (test_match_ids,) = cursor.fetchone()
        cursor.execute(
            """
            insert into eval_folds (protocol_id, fold_index, train_match_ids, test_match_ids)
            values (%s, 0, '{}', %s)
            """,
            (protocol_id, test_match_ids),
        )
    connection.commit()
