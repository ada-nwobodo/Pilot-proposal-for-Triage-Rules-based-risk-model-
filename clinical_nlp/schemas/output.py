from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Severity(str, Enum):
    UNKNOWN = "UNKNOWN"
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class EntityContribution(BaseModel):
    text: str
    label: str
    is_negated: bool
    severity: Severity
    weight: float
    score_contribution: float


class VitalsFlag(BaseModel):
    field: str
    value: float
    points: int
    reason: str


class RiskAssessment(BaseModel):
    patient_id: Optional[str] = None
    risk_level: RiskLevel
    combined_score: float
    entity_score: float
    vitals_score: int
    entity_contributions: list[EntityContribution]
    vitals_flags: list[VitalsFlag]
    override_triggered: bool = False
    override_reason: Optional[str] = None
    reasoning_text: str
    suggested_diagnosis: Optional[str] = None
    next_steps: list[str] = []
    processing_time_ms: float = 0.0

    # ── Priority tier fields (populated by priority_mapper; None until set) ──
    priority_tier: Optional[str] = Field(
        None,
        description=(
            "MTS-derived priority tier: IMMEDIATE | VERY_URGENT | URGENT | "
            "STANDARD | NON_URGENT. Populated after Layers 1-3 are applied."
        ),
    )
    max_wait_minutes: Optional[int] = Field(
        None,
        description="Maximum safe waiting time in minutes derived from priority_tier.",
    )
    priority_colour: Optional[str] = Field(
        None,
        description="Display colour for priority banner: RED | ORANGE | YELLOW | GREEN | BLUE.",
    )
    priority_basis: Optional[str] = Field(
        None,
        description="Human-readable explanation of what drove the final priority tier.",
    )
    chest_pain_safety_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Red flag differentials detected by the chest pain safety screen. "
            "Empty list if screen did not trigger or no flags found."
        ),
    )
    clarification_required: Optional[bool] = Field(
        None,
        description="True if the COPD clarification question should be shown to the nurse.",
    )
    clarification_question: Optional[str] = Field(
        None,
        description="Populated when clarification_required is True.",
    )
