import pytest
from clinical_nlp.schemas.input import ClinicalInput, VitalSigns
from clinical_nlp.schemas.output import RiskLevel


# ── Safety assertions ─────────────────────────────────────────────────────────

SAFETY_CASES = [
    (
        "haemoptysis + pleuritic chest pain must not be LOW",
        "Pt presents with 3 day history of pleuritic chest pain, shortness of breath and haemoptysis.",
        {"heart_rate": 95, "systolic_bp": 118, "spo2": 95},
        RiskLevel.LOW,
    ),
    (
        "previous PE + SOB + tachycardia must not be LOW",
        "Patient with history of previous PE presents with shortness of breath and calf swelling.",
        {"heart_rate": 110, "spo2": 94},
        RiskLevel.LOW,
    ),
    (
        "all negated PE symptoms should not be HIGH",
        "Patient denies chest pain. No shortness of breath. No haemoptysis. No leg swelling.",
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
        f"FAILED: {description}\n"
        f"Got: {result.risk_level}\n"
        f"Reasoning: {result.reasoning_text}"
    )


# ── Acceptance criterion ──────────────────────────────────────────────────────

def test_acceptance_criterion_note(pipeline):
    """
    The exact note from the acceptance criterion must detect all three features
    and produce a PE-positive result with next steps.
    """
    inp = ClinicalInput(
        note_text=(
            "Pt presents with 3 day history of pleuritic chest pain, "
            "shortness of breath and haemoptysis."
        ),
    )
    result = pipeline.run(inp)

    active_texts = {
        c.text.lower()
        for c in result.entity_contributions
        if not c.is_negated
    }
    assert "pleuritic chest pain" in active_texts, "pleuritic chest pain not detected"
    assert "shortness of breath" in active_texts, "shortness of breath not detected"
    assert "haemoptysis" in active_texts, "haemoptysis not detected"

    assert result.risk_level != RiskLevel.LOW
    assert result.suggested_diagnosis is not None
    assert "Pulmonary Embolism" in result.suggested_diagnosis
    assert len(result.next_steps) > 0


# ── General pipeline tests ────────────────────────────────────────────────────

def test_pipeline_returns_reasoning(pipeline):
    inp = ClinicalInput(note_text="Patient presents with shortness of breath and calf swelling.")
    result = pipeline.run(inp)
    assert result.reasoning_text
    assert result.risk_level in RiskLevel.__members__.values()


def test_pipeline_no_pe_features_scores_low(pipeline):
    inp = ClinicalInput(
        note_text="Routine follow-up. Patient doing well. No complaints.",
    )
    result = pipeline.run(inp)
    assert result.risk_level == RiskLevel.LOW
    assert result.suggested_diagnosis is None
    assert result.next_steps == []
    assert "Not suggestive of PE" in result.reasoning_text


def test_pipeline_handles_missing_vitals(pipeline):
    inp = ClinicalInput(
        note_text="Pleuritic chest pain and haemoptysis.",
        vitals=None,
    )
    result = pipeline.run(inp)
    assert result is not None
    assert result.vitals_score == 0


def test_low_risk_next_steps_empty(pipeline):
    inp = ClinicalInput(
        note_text="Patient denies all symptoms. Routine check.",
        vitals=VitalSigns(heart_rate=70, systolic_bp=120, spo2=99),
    )
    result = pipeline.run(inp)
    assert result.next_steps == []


def test_pe_positive_next_steps_present(pipeline):
    inp = ClinicalInput(
        note_text="Sudden onset pleuritic chest pain and haemoptysis.",
        vitals=VitalSigns(heart_rate=112, spo2=91),
    )
    result = pipeline.run(inp)
    required = {"ECG", "Insert wide bore cannula (pink)", "FBC", "U&E", "Clotting", "D-dimer"}
    assert required.issubset(set(result.next_steps))
