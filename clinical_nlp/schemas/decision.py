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
    decision: str                     # "accept" or "reject" (computed from granular fields)
    decision_reason: str = ""         # optional when both recommendations accepted
    clinician_name: str               # name of the clinician recording the decision
    patient_ref: str = ""             # anonymised internal reference code (no PII)

    # Encounter timing — optional; only present if clinician used Start Encounter
    encounter_start_ts:   Optional[str] = None  # ISO 8601 UTC string
    encounter_end_ts:     Optional[str] = None  # ISO 8601 UTC string (frozen at decision click)
    encounter_duration_s: Optional[int] = None  # whole seconds (start → decision click)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("accept", "reject"):
            raise ValueError('decision must be "accept" or "reject"')
        return v

    @field_validator("decision_reason")
    @classmethod
    def normalise_reason(cls, v: str) -> str:
        return v.strip()

    @field_validator("clinician_name")
    @classmethod
    def validate_clinician_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("clinician_name must not be empty")
        return v.strip()
