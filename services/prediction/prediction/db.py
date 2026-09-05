"""Read-only database access for the prediction service.

Queries v_completed_matches and events only, never matches or
match_competitors directly -- the view is the boundary this service and
Go's canonical writers agree on. This module never writes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime

import psycopg


def connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


@dataclass(frozen=True)
class Event:
    id: int
    slug: str
    held_on: date


@dataclass(frozen=True)
class CompletedMatch:
    match_id: int
    event_id: int
    scheduled_at: datetime
    arm: str
    athlete_a_id: int
    athlete_b_id: int
    result_a: str


def list_events(connection: psycopg.Connection) -> list[Event]:
    """Events ordered chronologically, the sequence rolling-origin folds
    walk through."""
    with connection.cursor() as cursor:
        cursor.execute("select id, slug, held_on from events order by held_on, id")
        return [Event(id=row[0], slug=row[1], held_on=row[2]) for row in cursor.fetchall()]


def list_completed_matches(connection: psycopg.Connection) -> list[CompletedMatch]:
    """Every completed match, ordered chronologically."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select match_id, event_id, scheduled_at, arm, athlete_a_id, athlete_b_id, result_a
            from v_completed_matches
            order by scheduled_at, match_id
            """
        )
        return [
            CompletedMatch(
                match_id=row[0],
                event_id=row[1],
                scheduled_at=row[2],
                arm=row[3],
                athlete_a_id=row[4],
                athlete_b_id=row[5],
                result_a=row[6],
            )
            for row in cursor.fetchall()
        ]
