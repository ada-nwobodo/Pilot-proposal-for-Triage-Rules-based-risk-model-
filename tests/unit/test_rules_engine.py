from clinical_nlp.phrase_matcher.negation import AnnotatedEntity
from clinical_nlp.schemas.output import RiskLevel, Severity
from clinical_nlp.vitals.scorer import VitalsScore
from clinical_nlp.rules_engine.engine import assess


def make_entity(text, label="PE_SYMPTOM", negated=False, severity=Severity.UNKNOWN):
    ent = AnnotatedEntity(text=text, label=label, start=0, end=1, is_negated=negated)
    ent._severity = severity
    return ent


# ── Risk level tests ──────────────────────────────────────────────────────────

def test_no_features_scores_low():
    result = assess([], VitalsScore())
    assert result.risk_level == RiskLevel.LOW


def test_all_negated_entities_score_low():
    entities = [
        make_entity("chest pain", negated=True),
        make_entity("shortness of breath", negated=True),
    ]
    result = assess(entities, VitalsScore())
    assert result.risk_level == RiskLevel.LOW


def test_single_strong_symptom_scores_medium():
    entities = [make_entity("haemoptysis")]
    result = assess(entities, VitalsScore())
    assert result.risk_level == RiskLevel.MEDIUM


def test_three_pe_symptoms_scores_medium():
    # Acceptance criterion: pleuritic chest pain + SOB + haemoptysis
    entities = [
        make_entity("pleuritic chest pain"),
        make_entity("shortness of breath"),
        make_entity("haemoptysis"),
    ]
    result = assess(entities, VitalsScore())
    assert result.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


def test_multiple_features_plus_vitals_scores_high():
    entities = [
        make_entity("pleuritic chest pain"),
        make_entity("shortness of breath"),
        make_entity("haemoptysis"),
    ]
    from clinical_nlp.schemas.input import VitalSigns
    from clinical_nlp.vitals.scorer import score_vitals
    vitals = score_vitals(VitalSigns(heart_rate=115, spo2=90))
    result = assess(entities, vitals)
    assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


# ── Suggested diagnosis tests ─────────────────────────────────────────────────

def test_low_risk_has_no_suggested_diagnosis():
    result = assess([], VitalsScore())
    assert result.suggested_diagnosis is None


def test_medium_risk_suggests_possible_pe():
    entities = [make_entity("haemoptysis")]
    result = assess(entities, VitalsScore())
    assert result.suggested_diagnosis == "Possible Pulmonary Embolism"


def test_high_risk_suggests_possible_pe():
    entities = [
        make_entity("pleuritic chest pain"),
        make_entity("shortness of breath"),
        make_entity("previous dvt", label="PE_RISK_FACTOR"),
    ]
    from clinical_nlp.schemas.input import VitalSigns
    from clinical_nlp.vitals.scorer import score_vitals
    vitals = score_vitals(VitalSigns(heart_rate=112))
    result = assess(entities, vitals)
    assert "Pulmonary Embolism" in (result.suggested_diagnosis or "")


# ── Next steps tests ──────────────────────────────────────────────────────────

def test_low_risk_has_no_next_steps():
    result = assess([], VitalsScore())
    assert result.next_steps == []


def test_pe_positive_has_all_required_next_steps():
    entities = [make_entity("haemoptysis")]
    result = assess(entities, VitalsScore())
    required = {"ECG", "Insert wide bore cannula (pink)", "FBC", "U&E", "Clotting", "D-dimer"}
    assert required.issubset(set(result.next_steps))


# ── Reasoning text tests ──────────────────────────────────────────────────────

def test_low_risk_reasoning_says_not_suggestive():
    result = assess([], VitalsScore())
    assert "Not suggestive of PE" in result.reasoning_text


def test_reasoning_text_not_empty():
    result = assess([], VitalsScore())
    assert len(result.reasoning_text) > 10


# ── Acceptance criterion ──────────────────────────────────────────────────────

def test_acceptance_criterion_three_features_detected_and_scored():
    """All three findings in the acceptance criterion note must be non-zero."""
    entities = [
        make_entity("pleuritic chest pain"),
        make_entity("shortness of breath"),
        make_entity("haemoptysis"),
    ]
    result = assess(entities, VitalsScore())
    active = [c for c in result.entity_contributions if not c.is_negated]
    active_texts = {c.text.lower() for c in active}
    assert "pleuritic chest pain" in active_texts
    assert "shortness of breath" in active_texts
    assert "haemoptysis" in active_texts
    # All three must contribute positively to the score
    for c in active:
        assert c.score_contribution > 0
