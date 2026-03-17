from __future__ import annotations
from clinical_nlp.phrase_matcher import AnnotatedEntity, get_severity
from clinical_nlp.schemas.output import Severity

# Clinical weights per entity text (lowercase). Defaults to 1.0.
ENTITY_WEIGHTS: dict[str, float] = {
    "cardiac arrest": 5.0,
    "respiratory failure": 4.5,
    "anaphylaxis": 4.5,
    "anaphylactic shock": 4.5,
    "septic shock": 4.0,
    "sepsis": 3.5,
    "stemi": 3.5,
    "myocardial infarction": 3.5,
    "mi": 3.5,
    "acs": 3.0,
    "acute coronary syndrome": 3.0,
    "pulmonary embolism": 3.0,
    "pe": 3.0,
    "stroke": 3.0,
    "loss of consciousness": 2.5,
    "altered consciousness": 2.5,
    "altered mental status": 2.5,
    "syncope": 2.5,
    "chest pain": 2.0,
    "shortness of breath": 2.0,
    "dyspnea": 2.0,
    "difficulty breathing": 2.0,
    "diaphoresis": 2.0,
    "diaphoretic": 2.0,
    "hypotension": 2.0,
    "tachycardia": 1.5,
    "bradycardia": 1.5,
    "tachypnea": 1.5,
    "fever": 1.5,
    "febrile": 1.5,
    "palpitations": 1.5,
    "hemoptysis": 1.5,
    "confusion": 2.0,
    "unresponsive": 4.0,
    "nausea": 0.5,
    "vomiting": 0.5,
    "headache": 0.5,
    "dizziness": 0.5,
    "fatigue": 0.3,
    "cough": 0.5,
}

SEVERITY_MULTIPLIERS: dict[Severity, float] = {
    Severity.UNKNOWN: 1.0,
    Severity.MILD: 0.75,
    Severity.MODERATE: 1.25,
    Severity.SEVERE: 2.0,
}

# Diagnosis label gets a boost
DIAGNOSIS_BOOST = 1.2


def score_entity(entity: AnnotatedEntity) -> float:
    if entity.is_negated:
        return 0.0

    base = ENTITY_WEIGHTS.get(entity.text.lower(), 1.0)
    severity = get_severity(entity)
    multiplier = SEVERITY_MULTIPLIERS[severity]

    if entity.label == "DIAGNOSIS":
        multiplier *= DIAGNOSIS_BOOST

    return round(base * multiplier, 3)


def aggregate_entity_scores(scored: list[float]) -> float:
    """Weighted max + contribution sum strategy."""
    if not scored:
        return 0.0
    return round(max(scored) * 0.6 + sum(scored) * 0.4, 3)
