from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SourceBasis = Literal[
    "observed_match_event",
    "athlete_self_report",
    "coach_or_training_partner_report",
    "analyst_interpretation",
    "measurement_or_lift",
    "general_principle",
    "community_narrative",
    "unclear",
]

AtomConfidence = Literal["low", "medium", "high"]


class MechanismAtom(BaseModel):
    atom_id: str
    evidence_index: int
    actor: str
    target: str = ""
    action: str
    lane: str = ""
    position_state: str = ""
    match_phase: str = ""
    enables: list[str] = Field(default_factory=list)
    denies: list[str] = Field(default_factory=list)
    follow_up: list[str] = Field(default_factory=list)
    condition: str = ""
    source_basis: SourceBasis = "unclear"
    current_form_usable: bool = False
    durable_style_usable: bool = False
    historical_context_usable: bool = False
    confidence: AtomConfidence = "medium"
    caveat: str = ""


class MechanismConflict(BaseModel):
    conflict: str
    side_a_atom_ids: list[str]
    side_b_atom_ids: list[str]
    why_it_matters: str
    unresolved_question: str = ""


class MechanismGraphArtifact(BaseModel):
    generated_at: str
    model: str
    input_claim_count: int
    atoms: list[MechanismAtom]
    conflicts: list[MechanismConflict]
    missing_or_underdeveloped_mechanisms: list[str]
