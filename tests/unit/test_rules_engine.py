from clinical_nlp.phrase_matcher.negation import AnnotatedEntity
from clinical_nlp.schemas.output import RiskLevel, Severity
from clinical_nlp.vitals.scorer import VitalsScore
from clinical_nlp.rules_engine.engine import assess, _check_overrides


def make_entity(text, label="SYMPTOM", negated=False):
    ent = AnnotatedEntity(text=text, label=label, start=0, end=1, is_negated=negated)
    ent._severity = Severity.UNKNOWN
    return ent


def test_all_negated_entities_score_low():
    entities = [
        make_entity("chest pain", negated=True),
        make_entity("shortness of breath", negated=True),
    ]
    result = assess(entities, VitalsScore())
    assert result.risk_level == RiskLevel.LOW


def test_critical_entity_override():
    entities = [make_entity("cardiac arrest", label="DIAGNOSIS")]
    result = assess(entities, VitalsScore())
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.override_triggered


def test_critically_low_spo2_override():
    from clinical_nlp.schemas.input import VitalSigns
    from clinical_nlp.vitals.scorer import score_vitals
    vitals = score_vitals(VitalSigns(spo2=82))
    result = assess([], vitals)
    assert result.risk_level == RiskLevel.CRITICAL


def test_high_risk_combination():
    entities = [
        make_entity("chest pain"),
        make_entity("diaphoresis"),
        make_entity("shortness of breath"),
    ]
    for e in entities:
        e._severity = Severity.SEVERE
    from clinical_nlp.schemas.input import VitalSigns
    from clinical_nlp.vitals.scorer import score_vitals
    vitals = score_vitals(VitalSigns(heart_rate=118, systolic_bp=88))
    result = assess(entities, vitals)
    assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


def test_reasoning_text_not_empty():
    result = assess([], VitalsScore())
    assert len(result.reasoning_text) > 10
