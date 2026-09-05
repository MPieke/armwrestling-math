from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from conftest import seed_completed_match
from prediction.compare import compare, evidence_covered_match_ids
from prediction.explain_prediction import build_prediction_explanation
from prediction.folds import seed_lockbox
from prediction.run_baseline import get_or_create_rolling_origin_protocol, run_baseline

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_MODEL = "fixture-model"
EVIDENCE_PROMPT_VERSION = "v1"


def _seed_claim(connection, *, athlete_id, published_at, claim_type):
    """claims.match_id is a required FK but carries no meaning for evidence
    eligibility here -- select_eligible_claims joins through claim_subjects,
    not claims.match_id -- so any existing match satisfies it."""
    with connection.cursor() as cursor:
        cursor.execute(
            "insert into sources (source_type, external_id, url, published_at) "
            "values ('youtube', %s, 'https://example.com', %s) returning id",
            (f"video-{athlete_id}-{published_at.isoformat()}", published_at),
        )
        (source_id,) = cursor.fetchone()
        cursor.execute("select id from matches order by id limit 1")
        (any_match_id,) = cursor.fetchone()
        cursor.execute(
            "insert into claims (source_id, match_id, claim_text, extracted_at) "
            "values (%s, %s, 'fixture claim', now()) returning id",
            (source_id, any_match_id),
        )
        (claim_id,) = cursor.fetchone()
        cursor.execute("insert into claim_subjects (claim_id, athlete_id) values (%s, %s)", (claim_id, athlete_id))
        cursor.execute(
            "insert into claim_annotations (claim_id, model, prompt_version, claim_type, concepts, temporality, certainty) "
            "values (%s, %s, %s, %s, array['top_roll'], 'current_form', 'observed')",
            (claim_id, EVIDENCE_MODEL, EVIDENCE_PROMPT_VERSION, claim_type),
        )
    connection.commit()


def _seed_protocol_with_evidence(connection) -> tuple[int, int]:
    """4 dev events + 1 lockbox event; the last dev event's athlete A has a
    tactic claim published before that event, giving exactly one
    evidence-covered test match."""
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
    with connection.cursor() as cursor:
        cursor.execute("select id from athletes where canonical_name = 'A3'")
        (athlete_id,) = cursor.fetchone()
        cursor.execute("select m.id from matches m join events e on e.id = m.event_id where e.slug = 'event-3'")
        (evidence_match_id,) = cursor.fetchone()
    _seed_claim(
        connection,
        athlete_id=athlete_id,
        published_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
        claim_type="tactic",
    )
    # A claim published after the match: excluded, not eligible -- proves
    # explain-prediction's partitioning, not just the encoding.
    _seed_claim(
        connection,
        athlete_id=athlete_id,
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        claim_type="form",
    )
    protocol_id = get_or_create_rolling_origin_protocol(connection, "rolling_origin_test", min_training_events=2)
    return protocol_id, evidence_match_id


@pytest.mark.integration
def test_evidence_v1_run_persists_evidence_alongside_history_features(connection):
    protocol_id, evidence_match_id = _seed_protocol_with_evidence(connection)

    run_id = run_baseline(
        connection,
        protocol_id,
        model_family="evidence_v1",
        feature_schema="history_v1",
        evidence_model=EVIDENCE_MODEL,
        evidence_prompt_version=EVIDENCE_PROMPT_VERSION,
        repo_root=REPO_ROOT,
    )

    with connection.cursor() as cursor:
        cursor.execute("select status, model_family from experiment_runs where id = %s", (run_id,))
        status, model_family = cursor.fetchone()
        cursor.execute(
            "select payload from run_feature_rows where run_id = %s and match_id = %s and role = 'test'",
            (run_id, evidence_match_id),
        )
        (payload,) = cursor.fetchone()
    assert status == "completed"
    assert model_family == "evidence_v1"
    assert payload["evidence"]["evidence_count"] == 1
    assert payload["evidence"]["technique_advantage_flag"] is True
    assert "features" in payload and "prior_rating_a" in payload["features"]


@pytest.mark.integration
def test_explain_prediction_partitions_eligible_and_excluded_evidence_claims(connection):
    protocol_id, evidence_match_id = _seed_protocol_with_evidence(connection)
    run_id = run_baseline(
        connection,
        protocol_id,
        model_family="evidence_v1",
        feature_schema="history_v1",
        evidence_model=EVIDENCE_MODEL,
        evidence_prompt_version=EVIDENCE_PROMPT_VERSION,
        repo_root=REPO_ROOT,
    )

    explanation = build_prediction_explanation(connection, run_id, evidence_match_id)

    basis = explanation["evidence_basis"]
    assert basis is not None
    assert basis["evidence_model"] == EVIDENCE_MODEL
    assert basis["encoded"]["evidence_count"] == 1
    assert len(basis["eligible_claims"]) == 1
    assert basis["eligible_claims"][0]["claim_type"] == "tactic"
    assert len(basis["excluded_claims"]) == 1
    assert basis["excluded_claims"][0]["reason"] == "published at or after the match"


@pytest.mark.integration
def test_evidence_v1_matches_without_evidence_get_the_zero_encoding(connection):
    protocol_id, _ = _seed_protocol_with_evidence(connection)

    run_id = run_baseline(
        connection,
        protocol_id,
        model_family="evidence_v1",
        feature_schema="history_v1",
        evidence_model=EVIDENCE_MODEL,
        evidence_prompt_version=EVIDENCE_PROMPT_VERSION,
        repo_root=REPO_ROOT,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "select payload from run_feature_rows where run_id = %s and role = 'train'",
            (run_id,),
        )
        train_payloads = [row[0] for row in cursor.fetchall()]
    assert any(payload["evidence"]["evidence_count"] == 0 for payload in train_payloads)


@pytest.mark.integration
def test_compare_evidence_covered_only_restricts_to_matches_with_evidence(connection):
    protocol_id, evidence_match_id = _seed_protocol_with_evidence(connection)
    tier_b_run = run_baseline(connection, protocol_id, model_family="logreg", feature_schema="history_v1", repo_root=REPO_ROOT)
    evidence_run = run_baseline(
        connection,
        protocol_id,
        model_family="evidence_v1",
        feature_schema="history_v1",
        evidence_model=EVIDENCE_MODEL,
        evidence_prompt_version=EVIDENCE_PROMPT_VERSION,
        repo_root=REPO_ROOT,
    )

    covered = evidence_covered_match_ids(connection, evidence_run)
    assert covered == [evidence_match_id]

    result = compare(connection, tier_b_run, evidence_run, match_ids=covered)
    assert result["match_ids_restricted"] is True
    assert result["match_ids"] == [evidence_match_id]
    assert result["n"] == 1
