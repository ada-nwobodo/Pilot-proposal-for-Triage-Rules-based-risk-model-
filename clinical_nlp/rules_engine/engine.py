from __future__ import annotations
import time
from clinical_nlp.schemas.input import ClinicalInput
from clinical_nlp.schemas.output import (
    RiskLevel, RiskAssessment, EntityContribution, VitalsFlag, Severity
)
from clinical_nlp.phrase_matcher import AnnotatedEntity, get_severity
from clinical_nlp.vitals.scorer import VitalsScore
from .entity_scorer import score_entity, aggregate_entity_scores, ENTITY_WEIGHTS

# Entities that force CRITICAL regardless of score
CRITICAL_OVERRIDE_ENTITIES = {
    "cardiac arrest", "respiratory arrest", "respiratory failure",
    "anaphylaxis", "anaphylactic shock", "status epilepticus",
    "unresponsive",
}

RISK_THRESHOLDS = [
    (RiskLevel.CRITICAL, 8.0),
    (RiskLevel.HIGH, 5.0),
    (RiskLevel.MEDIUM, 2.0),
    (RiskLevel.LOW, 0.0),
]


def assess(
    entities: list[AnnotatedEntity],
    vitals_score: VitalsScore,
    patient_id: str | None = None,
    entity_weight: float = 0.55,
    vitals_weight: float = 0.45,
) -> RiskAssessment:
    t0 = time.perf_counter()

    # Phase 1: Override rules
    override, override_reason = _check_overrides(entities, vitals_score)

    # Phase 2: Numeric scoring
    scored_entities = [(ent, score_entity(ent)) for ent in entities]
    entity_scores = [s for _, s in scored_entities]
    entity_score_agg = aggregate_entity_scores(entity_scores)

    combined_score = round(
        entity_score_agg * entity_weight + vitals_score.total_points * vitals_weight,
        3,
    )

    # Phase 3: Threshold to risk level (or override)
    if override:
        risk_level = override
    else:
        risk_level = _score_to_risk(combined_score)

    # Build output
    contributions = _build_contributions(scored_entities)
    vitals_flags = [
        VitalsFlag(field=f, value=v, points=p, reason=r)
        for f, v, p, r in vitals_score.flagged_fields
    ]

    reasoning = _build_reasoning(
        risk_level, combined_score, contributions, vitals_flags,
        override_triggered=bool(override_reason), override_reason=override_reason,
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return RiskAssessment(
        patient_id=patient_id,
        risk_level=risk_level,
        combined_score=combined_score,
        entity_score=entity_score_agg,
        vitals_score=vitals_score.total_points,
        entity_contributions=contributions,
        vitals_flags=vitals_flags,
        override_triggered=bool(override_reason),
        override_reason=override_reason,
        reasoning_text=reasoning,
        processing_time_ms=elapsed_ms,
    )


def _check_overrides(
    entities: list[AnnotatedEntity],
    vitals: VitalsScore,
) -> tuple[RiskLevel | None, str | None]:
    # CRITICAL entity override
    for ent in entities:
        if not ent.is_negated and ent.text.lower() in CRITICAL_OVERRIDE_ENTITIES:
            return RiskLevel.CRITICAL, f"Critical entity detected: '{ent.text}'"

    # CRITICAL vitals override
    for field_name, value, points, reason in vitals.flagged_fields:
        if field_name == "spo2" and value < 85:
            return RiskLevel.CRITICAL, f"SpO2 critically low: {value}%"
        if field_name == "gcs" and value < 9:
            return RiskLevel.CRITICAL, f"GCS critically low: {value}"

    # HIGH vitals override
    severe_entity_count = sum(
        1 for ent in entities
        if not ent.is_negated and get_severity(ent) == Severity.SEVERE
    )
    if severe_entity_count >= 3:
        return RiskLevel.HIGH, f"{severe_entity_count} severe-severity entities present"

    return None, None


def _score_to_risk(score: float) -> RiskLevel:
    for level, threshold in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return RiskLevel.LOW


def _build_contributions(
    scored: list[tuple[AnnotatedEntity, float]]
) -> list[EntityContribution]:
    return [
        EntityContribution(
            text=ent.text,
            label=ent.label,
            is_negated=ent.is_negated,
            severity=get_severity(ent),
            weight=ENTITY_WEIGHTS.get(ent.text.lower(), 1.0),
            score_contribution=score,
        )
        for ent, score in scored
    ]


def _build_reasoning(
    risk_level: RiskLevel,
    combined_score: float,
    contributions: list[EntityContribution],
    vitals_flags: list[VitalsFlag],
    override_triggered: bool,
    override_reason: str | None,
) -> str:
    active = [c for c in contributions if not c.is_negated]
    negated = [c for c in contributions if c.is_negated]

    parts = [f"Risk assessed as {risk_level.value} (combined score: {combined_score:.2f})."]

    if override_triggered:
        parts.append(f"Override rule triggered: {override_reason}.")

    if active:
        entity_summary = ", ".join(
            f"{c.text} [{c.severity.value}]" for c in active[:5]
        )
        parts.append(f"Active entities: {entity_summary}.")

    if negated:
        neg_summary = ", ".join(c.text for c in negated[:3])
        parts.append(f"Negated (not counted): {neg_summary}.")

    if vitals_flags:
        vitals_summary = ", ".join(f.reason for f in vitals_flags[:4])
        parts.append(f"Vital sign flags: {vitals_summary}.")
    else:
        parts.append("Vital signs within normal limits or not provided.")

    return " ".join(parts)
