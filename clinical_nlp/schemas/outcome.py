from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional

_ALLOWED_OUTCOMES = {"pe_confirmed", "pe_excluded", "alternative_diagnosis", "inconclusive"}
_ALLOWED_TESTS = {
    "ctpa", "vq_scan", "d_dimer_negative", "echo",
    "clinical_judgement", "other",
}


class OutcomePayload(BaseModel):
    """
    Payload sent by the frontend to PATCH /decisions/{id}/outcome.

    Records the clinical outcome after investigations are complete.
    outcome_recorded_at is set server-side — never accepted from the client.
    """

    outcome: str                         # "pe_confirmed" | "pe_excluded" | "alternative_diagnosis" | "inconclusive"
    confirming_test: Optional[str] = None  # one of _ALLOWED_TESTS, or None
    outcome_date: Optional[str] = None   # ISO date "YYYY-MM-DD", or None
    outcome_notes: Optional[str] = None  # free-text, or None

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        if v not in _ALLOWED_OUTCOMES:
            raise ValueError(f"outcome must be one of {sorted(_ALLOWED_OUTCOMES)}")
        return v

    @field_validator("confirming_test")
    @classmethod
    def validate_confirming_test(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _ALLOWED_TESTS:
            raise ValueError(f"confirming_test must be one of {sorted(_ALLOWED_TESTS)}")
        return v
