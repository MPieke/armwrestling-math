"""Shared integration-test fixtures.

Mirrors services/importer's integration test pattern: a dedicated test
database, guarded by name, reset to a known-empty state before each test.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest

INTEGRATION_DATABASE_NAME = "armwrestling_math_test"


@pytest.fixture()
def connection() -> Iterator[psycopg.Connection]:
    database_url = os.environ.get("PREDICTION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PREDICTION_TEST_DATABASE_URL is required for integration tests")
    conn = psycopg.connect(database_url)
    with conn.cursor() as cursor:
        cursor.execute("select current_database()")
        (actual_database,) = cursor.fetchone()
    if actual_database != INTEGRATION_DATABASE_NAME:
        conn.close()
        pytest.fail(
            f"PREDICTION_TEST_DATABASE_URL must target {INTEGRATION_DATABASE_NAME!r}, "
            f"got {actual_database!r}"
        )
    _reset_schema(conn)
    yield conn
    conn.close()


def _reset_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            truncate claim_subjects, claims, source_extractions, sources,
                     match_videos, match_competitors, matches, events, athletes, ingestion_runs,
                     run_predictions, run_models, experiment_runs, eval_folds, eval_protocols
            restart identity cascade
            """
        )
        cursor.execute(
            """
            delete from feature_specs
            where not (name = 'outcomes_elo' and version = 1)
            """
        )
    conn.commit()


def seed_completed_match(
    connection: psycopg.Connection,
    *,
    event_slug: str,
    held_on: date,
    athlete_a: str,
    athlete_b: str,
    arm: str = "right",
) -> tuple[int, int]:
    """Seeds one event and one completed match between two fresh athletes.
    Returns (event_id, match_id)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "insert into events (slug, promoter, name, held_on) values (%s, 'fixture', %s, %s) returning id",
            (event_slug, event_slug, held_on),
        )
        (event_id,) = cursor.fetchone()
        athlete_ids = []
        for name in (athlete_a, athlete_b):
            cursor.execute(
                "insert into athletes (canonical_name) values (%s) returning id", (name,)
            )
            athlete_ids.append(cursor.fetchone()[0])
        cursor.execute(
            """
            insert into matches (natural_key, weight_class, arm, scheduled_at, event_id, status)
            values (%s, 'open', %s, %s, %s, 'completed') returning id
            """,
            (f"{event_slug}:{athlete_a}:{athlete_b}:{arm}", arm, held_on, event_id),
        )
        (match_id,) = cursor.fetchone()
        cursor.execute(
            "insert into match_competitors (match_id, athlete_id, score, result) values (%s, %s, 3, 'win')",
            (match_id, athlete_ids[0]),
        )
        cursor.execute(
            "insert into match_competitors (match_id, athlete_id, score, result) values (%s, %s, 1, 'loss')",
            (match_id, athlete_ids[1]),
        )
    connection.commit()
    return event_id, match_id
