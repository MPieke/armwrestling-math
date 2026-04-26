from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


AthleteTag = Literal["ermes", "morozov", "both", "other"]
ClaimType = Literal[
    "style",
    "form",
    "injury",
    "strength",
    "weakness",
    "prediction",
    "historical",
    "setup",
    "endurance",
    "psychology",
    "other",
]
Stance = Literal["supports_ermes", "supports_morozov", "neutral", "counter_case"]
RecencyClass = Literal["current", "recent", "old_context", "unknown"]
SourceQuality = Literal["high", "medium", "low"]
SourceRecency = Literal["current_window", "recent_context", "historical_context", "unknown"]


class EvidenceClaim(BaseModel):
    claim: str
    timestamp: str = ""
    source_url: HttpUrl
    speaker_or_source: str = "unknown"
    relevance: str = ""
    confidence: str = "unknown"
    video_id: str
    video_title: str
    channel: str
    selected_model: str
    source_published_at: str | None = None
    source_age_days: int | None = None
    source_recency: SourceRecency = "unknown"
    current_form_allowed: bool = False
    allowed_evidence_roles: list[str] = Field(default_factory=list)


class ClassifiedClaim(BaseModel):
    evidence_index: int
    evidence: EvidenceClaim
    athlete: AthleteTag
    claim_type: ClaimType
    stance: Stance
    recency: RecencyClass
    source_quality: SourceQuality
    synthesis_value: int = Field(ge=1, le=5)
    durable_style_signal: bool = False
    current_form_signal: bool = False
    caveat: str = ""


class NarrativeCluster(BaseModel):
    title: str
    summary: str
    stance: Stance
    claim_type: ClaimType
    supporting_claim_indices: list[int]
    caveat: str = ""


class ShareCard(BaseModel):
    headline: str
    key_stat: str
    counter_insight: str
    key_question: str


class CasePoint(BaseModel):
    claim_index: int | None = None
    summary: str
    caveat: str = ""


class MatchSynthesis(BaseModel):
    matchup: str
    event_context: str
    popular_take: str
    counter_case: str
    what_community_might_be_missing: str
    key_question: str
    ermes_case: list[CasePoint]
    morozov_case: list[CasePoint]
    uncertainty_flags: list[str]
    clusters: list[NarrativeCluster]
    top_evidence_indices: list[int]
    share_card: ShareCard


class SynthesisArtifact(BaseModel):
    generated_at: str
    synthesis_model: str
    input_claim_count: int
    classified_claims: list[ClassifiedClaim]
    synthesis: MatchSynthesis
