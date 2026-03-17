import pytest
from clinical_nlp.pipeline import ClinicalRiskOrchestrator
from clinical_nlp.schemas.input import ClinicalInput, VitalSigns


@pytest.fixture(scope="session")
def pipeline():
    return ClinicalRiskOrchestrator()


@pytest.fixture
def simple_note():
    return ClinicalInput(
        note_text="Patient complains of chest pain and shortness of breath.",
        vitals=VitalSigns(heart_rate=110, systolic_bp=92, spo2=95),
        patient_id="TEST-001",
    )


@pytest.fixture
def negated_note():
    return ClinicalInput(
        note_text="Patient denies chest pain. No shortness of breath. No fever.",
        vitals=VitalSigns(heart_rate=75, systolic_bp=120, spo2=98),
        patient_id="TEST-002",
    )
