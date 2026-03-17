import pytest
from clinical_nlp.schemas.input import ClinicalInput, VitalSigns
from clinical_nlp.schemas.output import RiskLevel


SAFETY_CASES = [
    # (description, note, vitals_dict, must_not_be)
    (
        "cardiac arrest note must not be LOW",
        "Patient found unresponsive. Cardiac arrest, no pulse detected.",
        {"heart_rate": 0, "systolic_bp": 0},
        RiskLevel.LOW,
    ),
    (
        "severe chest pain + bad vitals must not be LOW",
        "Severe chest pain radiating to left arm. Patient diaphoretic.",
        {"heart_rate": 115, "systolic_bp": 85, "spo2": 93},
        RiskLevel.LOW,
    ),
    (
        "all negated symptoms should not be HIGH",
        "Patient denies chest pain. No shortness of breath. No fever.",
        {"heart_rate": 72, "systolic_bp": 118, "spo2": 99},
        RiskLevel.HIGH,
    ),
]


@pytest.mark.parametrize("description,note,vitals_dict,must_not_be", SAFETY_CASES)
def test_pipeline_safety_assertions(pipeline, description, note, vitals_dict, must_not_be):
    inp = ClinicalInput(
        note_text=note,
        vitals=VitalSigns(**vitals_dict),
    )
    result = pipeline.run(inp)
    assert result.risk_level != must_not_be, (
        f"FAILED: {description}\nGot: {result.risk_level}\nReasoning: {result.reasoning_text}"
    )


def test_pipeline_returns_reasoning(pipeline):
    inp = ClinicalInput(note_text="Patient has fever and cough.")
    result = pipeline.run(inp)
    assert result.reasoning_text
    assert result.risk_level in RiskLevel.__members__.values()


def test_pipeline_no_entities_no_vitals(pipeline):
    inp = ClinicalInput(note_text="Routine follow-up visit. Patient doing well.")
    result = pipeline.run(inp)
    assert result.risk_level == RiskLevel.LOW


def test_pipeline_handles_missing_vitals(pipeline):
    inp = ClinicalInput(note_text="Chest pain reported.", vitals=None)
    result = pipeline.run(inp)
    assert result is not None
    assert result.vitals_score == 0
