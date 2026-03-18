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
