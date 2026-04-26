from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EvidenceKind = Literal[
    "observed_match_event",
    "athlete_self_report",
    "coach_or_training_partner_report",
    "technical_analyst_interpretation",
    "gym_lift_proxy",
    "measurement",
    "science_general",
    "community_narrative",
    "unclear",
]

TemporalScope = Literal[
    "current_form",
    "recent_context",
    "historical_event",
    "durable_style",
    "future_prediction",
    "general_principle",
    "unclear",
]

NoiseRisk = Literal["low", "medium", "high"]


class MeasurementDimension(BaseModel):
    metric: str
    value: str
    unit: str = ""
    setup_or_context: str = ""
    confidence: str = Field(default="medium", pattern="^(low|medium|high)$")
    caveat: str = ""


class LiftDimension(BaseModel):
    lift_name: str
    value: str = ""
    unit: str = ""
    setup_details_visible: bool = False
    maps_to_table_action: str = ""
    comparability_caveat: str = ""
    confidence: str = Field(default="medium", pattern="^(low|medium|high)$")


class TransferDimension(BaseModel):
    referenced_opponent_or_match: str
    tested_property: str
    transfers_to_ermes_morozov_how: str
    transfer_strength: str = Field(default="medium", pattern="^(low|medium|high)$")
    caveat: str = ""


class EvidenceDimensions(BaseModel):
    evidence_index: int
    evidence_kind: EvidenceKind
    temporal_scope: TemporalScope
    subject_athletes: list[str] = Field(default_factory=list)
    arm_side: str = "unknown"
    mechanics: list[str] = Field(default_factory=list)
    table_positions: list[str] = Field(default_factory=list)
    physical_attributes: list[str] = Field(default_factory=list)
    measurements: list[MeasurementDimension] = Field(default_factory=list)
    lifts: list[LiftDimension] = Field(default_factory=list)
    transferable_lessons: list[TransferDimension] = Field(default_factory=list)
    current_form_usable: bool = False
    durable_style_usable: bool = False
    historical_context_usable: bool = False
    verification_needed: list[str] = Field(default_factory=list)
    noise_risk: NoiseRisk = "medium"
    dimension_confidence: str = Field(default="medium", pattern="^(low|medium|high)$")
    abstained_dimensions: list[str] = Field(default_factory=list)


class DimensionArtifact(BaseModel):
    generated_at: str
    model: str
    input_claim_count: int
    dimensions: list[EvidenceDimensions]
