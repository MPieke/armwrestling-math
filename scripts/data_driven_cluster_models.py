from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class ClusterEvidenceRef(BaseModel):
    evidence_index: int
    role_in_theme: str
    quote_level_summary: str
    supports_current_form: bool = False
    supports_durable_style: bool = False
    supports_historical_context: bool = False
    caveat: str = ""


class EmergentTheme(BaseModel):
    theme_id: str
    label: str
    why_this_theme_emerged: str
    match_relevance: str
    evidence_refs: list[ClusterEvidenceRef]
    challenged_assumption: str = ""
    current_form_read: str = ""
    historical_style_read: str = ""
    confidence: str = Field(default="low", pattern="^(low|medium|high)$")


class SourceGap(BaseModel):
    gap: str
    why_it_matters: str
    suggested_source_query: str


class EvidenceClaimInput(BaseModel):
    evidence_index: int
    claim: str
    relevance: str = ""
    timestamp: str = ""
    source_url: HttpUrl
    speaker_or_source: str = "unknown"
    video_title: str
    channel: str
    source_published_at: str | None = None
    source_recency: str = "unknown"
    current_form_allowed: bool = False
    allowed_evidence_roles: list[str] = Field(default_factory=list)


class DataDrivenClusterArtifact(BaseModel):
    generated_at: str
    model: str
    input_claim_count: int
    instruction: str
    themes: list[EmergentTheme]
    cross_theme_tensions: list[str]
    strongest_current_form_signals: list[ClusterEvidenceRef]
    strongest_historical_style_signals: list[ClusterEvidenceRef]
    source_gaps: list[SourceGap]
