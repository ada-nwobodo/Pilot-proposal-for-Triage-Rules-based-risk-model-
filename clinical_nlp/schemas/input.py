from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class VitalSigns(BaseModel):
    heart_rate: Optional[float] = Field(None, description="Heart rate in bpm")
    systolic_bp: Optional[float] = Field(None, description="Systolic BP in mmHg")
    diastolic_bp: Optional[float] = Field(None, description="Diastolic BP in mmHg")
    respiratory_rate: Optional[float] = Field(None, description="Respiratory rate breaths/min")
    spo2: Optional[float] = Field(None, description="Oxygen saturation %")
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    gcs: Optional[int] = Field(None, description="Glasgow Coma Scale 3-15")
    known_copd: Optional[bool] = Field(
        None,
        description=(
            "Whether the patient has a known diagnosis of COPD. "
            "True = confirmed COPD; False = confirmed no COPD; "
            "None = not answered / unknown (treated conservatively as False)."
        ),
    )


class ClinicalInput(BaseModel):
    note_text: str = Field(..., description="Free-text clinical note")
    vitals: Optional[VitalSigns] = None
    patient_id: Optional[str] = None
    case_label: Optional[str] = Field(None, description="Ground-truth label for evaluation")
