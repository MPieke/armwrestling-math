"""Point-in-time evidence selection and encoding v1 (MPI-28, dyad-only).

Reads claims/claim_annotations/claim_subjects/sources directly rather than
through a view: unlike v_completed_matches, eligibility is inherently
parametrized per match (the target's scheduled_at and both athlete ids), so
a flat view can't express it. Still read-only -- this module never writes
to any Go-owned table.

is_eligible is the point-in-time leakage rule, kept pure and separate from
the database fetch so it's directly unit-testable: a null published_at is
never eligible (the conservative default when a source's date is unknown),
and a source published at or after the match is never eligible either.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg

from prediction.db import CompletedMatch

RECENT_INJURY_WINDOW_DAYS = 30
TECHNIQUE_ADVANTAGE_CLAIM_TYPES = frozenset({"tactic", "setup", "opponent_comparison"})


@dataclass(frozen=True)
class AnnotatedClaim:
    claim_id: int
    claim_text: str
    published_at: datetime | None
    claim_type: str
    concepts: list[str]
    temporality: str
    certainty: str
    source_id: int
    source_title: str | None


def is_eligible(claim: AnnotatedClaim, match_scheduled_at: datetime) -> bool:
    if claim.published_at is None:
        return False
    return claim.published_at < match_scheduled_at


def select_eligible_claims(
    connection: psycopg.Connection, match: CompletedMatch, model: str, prompt_version: str
) -> list[AnnotatedClaim]:
    """Every dyad claim (about either athlete in match), annotated by
    (model, prompt_version), that is_eligible as of match.scheduled_at."""
    return [
        candidate
        for candidate in _fetch_dyad_claims(connection, match, model, prompt_version)
        if is_eligible(candidate, match.scheduled_at)
    ]


def _fetch_dyad_claims(
    connection: psycopg.Connection, match: CompletedMatch, model: str, prompt_version: str
) -> list[AnnotatedClaim]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select distinct c.id, c.claim_text, s.published_at, ca.claim_type,
                   ca.concepts, ca.temporality, ca.certainty, s.id, s.title
            from claims c
            join sources s on s.id = c.source_id
            join claim_annotations ca on ca.claim_id = c.id
                and ca.model = %s and ca.prompt_version = %s
            join claim_subjects cs on cs.claim_id = c.id
            where cs.athlete_id in (%s, %s)
            order by c.id
            """,
            (model, prompt_version, match.athlete_a_id, match.athlete_b_id),
        )
        return [
            AnnotatedClaim(
                claim_id=row[0],
                claim_text=row[1],
                published_at=row[2],
                claim_type=row[3],
                concepts=row[4],
                temporality=row[5],
                certainty=row[6],
                source_id=row[7],
                source_title=row[8],
            )
            for row in cursor.fetchall()
        ]


def describe_claim_eligibility(
    connection: psycopg.Connection, match: CompletedMatch, model: str, prompt_version: str
) -> tuple[list[AnnotatedClaim], list[tuple[AnnotatedClaim, str]]]:
    """For operator inspection (prediction.explain_prediction): every dyad
    claim, partitioned into eligible and (excluded, reason). Reuses the
    exact same candidate fetch and is_eligible rule select_eligible_claims
    does, so the two can never silently disagree."""
    candidates = _fetch_dyad_claims(connection, match, model, prompt_version)
    eligible: list[AnnotatedClaim] = []
    excluded: list[tuple[AnnotatedClaim, str]] = []
    for claim in candidates:
        if is_eligible(claim, match.scheduled_at):
            eligible.append(claim)
        elif claim.published_at is None:
            excluded.append((claim, "unknown publication time"))
        else:
            excluded.append((claim, "published at or after the match"))
    return eligible, excluded


def encode_evidence(claims: list[AnnotatedClaim], as_of: datetime) -> dict:
    """Pure function of the eligible set. One fixed v1 encoding, not a menu
    -- iteration beyond this is a ledger hypothesis and a new run."""
    recent_injury_flag = any(
        claim.claim_type == "injury"
        and (as_of - claim.published_at).days <= RECENT_INJURY_WINDOW_DAYS
        for claim in claims
    )
    technique_advantage_flag = any(
        claim.claim_type in TECHNIQUE_ADVANTAGE_CLAIM_TYPES for claim in claims
    )
    return {
        "evidence_count": len(claims),
        "recent_injury_flag": recent_injury_flag,
        "technique_advantage_flag": technique_advantage_flag,
    }
