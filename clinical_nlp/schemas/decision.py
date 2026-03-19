from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional


class DecisionPayload(BaseModel):
    """
    Payload sent by the frontend to POST /decisions.

    Contains the full assessment snapshot plus the clinician's decision.
    created_at is NOT accepted from the client — it is set server-side.
    """

    clinical_note: str
    detected_features: list[str]      # text of scored, non-negated entities
    abnormal_vitals: list[str]        # reason strings from flagged vitals
    score: float
    risk_level: str
    suggested_diagnosis: Optional[str] = None
    next_steps: list[str] = []
    decision: str                     # "accept" or "reject"
    decision_reason: str

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("accept", "reject"):
            raise ValueError('decision must be "accept" or "reject"')
        return v

    @field_validator("decision_reason")
    @classmethod
    def validate_reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("decision_reason must not be empty")
        return v.strip()
