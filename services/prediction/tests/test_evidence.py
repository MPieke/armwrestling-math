from datetime import datetime, timedelta, timezone

from prediction.evidence import AnnotatedClaim, encode_evidence, is_eligible

MATCH_TIME = datetime(2026, 6, 15, tzinfo=timezone.utc)


def _claim(published_at, claim_type="tactic"):
    return AnnotatedClaim(
        claim_id=1,
        claim_text="fixture claim",
        published_at=published_at,
        claim_type=claim_type,
        concepts=["top_roll"],
        temporality="current_form",
        certainty="observed",
        source_id=1,
        source_title="fixture video",
    )


def test_a_claim_published_before_the_match_is_eligible():
    claim = _claim(MATCH_TIME - timedelta(days=1))
    assert is_eligible(claim, MATCH_TIME) is True


def test_a_claim_published_at_or_after_the_match_is_never_eligible():
    assert is_eligible(_claim(MATCH_TIME), MATCH_TIME) is False
    assert is_eligible(_claim(MATCH_TIME + timedelta(days=1)), MATCH_TIME) is False


def test_a_claim_with_unknown_publication_time_is_never_eligible():
    """The conservative default: null published_at is NEVER eligible, even
    if every other field looks safe."""
    assert is_eligible(_claim(None), MATCH_TIME) is False


def test_encode_evidence_on_empty_list_matches_the_no_evidence_majority():
    encoded = encode_evidence([], as_of=MATCH_TIME)

    assert encoded == {"evidence_count": 0, "recent_injury_flag": False, "technique_advantage_flag": False}


def test_encode_evidence_flags_a_recent_injury():
    claim = _claim(MATCH_TIME - timedelta(days=10), claim_type="injury")

    encoded = encode_evidence([claim], as_of=MATCH_TIME)

    assert encoded["recent_injury_flag"] is True
    assert encoded["evidence_count"] == 1


def test_encode_evidence_does_not_flag_an_old_injury():
    claim = _claim(MATCH_TIME - timedelta(days=45), claim_type="injury")

    encoded = encode_evidence([claim], as_of=MATCH_TIME)

    assert encoded["recent_injury_flag"] is False


def test_encode_evidence_flags_technique_advantage_claim_types():
    for claim_type in ("tactic", "setup", "opponent_comparison"):
        encoded = encode_evidence([_claim(MATCH_TIME - timedelta(days=1), claim_type)], as_of=MATCH_TIME)
        assert encoded["technique_advantage_flag"] is True

    encoded = encode_evidence([_claim(MATCH_TIME - timedelta(days=1), "form")], as_of=MATCH_TIME)
    assert encoded["technique_advantage_flag"] is False
