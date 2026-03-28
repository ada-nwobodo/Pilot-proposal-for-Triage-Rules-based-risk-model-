from __future__ import annotations
import time
from clinical_nlp.schemas.output import (
    RiskLevel, RiskAssessment, EntityContribution, VitalsFlag, Severity,
)
from clinical_nlp.phrase_matcher import AnnotatedEntity, get_severity
from clinical_nlp.vitals.scorer import VitalsScore
from .entity_scorer import deduplicate_and_score, canonical_group

# ── Risk thresholds (1-point-per-feature integer scale) ───────────────────────
# Combined score = unique entity groups + unique vital flags (simple addition).
RISK_THRESHOLDS = [
    (RiskLevel.CRITICAL, 5),
    (RiskLevel.HIGH,     3),
    (RiskLevel.MEDIUM,   2),
    (RiskLevel.LOW,      0),
]

# Investigations recommended for any PE-positive result (MEDIUM / HIGH / CRITICAL)
PE_NEXT_STEPS = [
    "ECG",
    "Insert wide bore cannula (pink)",
    "FBC",
    "U&E",
    "Clotting",
    "D-dimer",
]

# Investigations recommended for LOW risk with score = 1
LOW_RISK_NEXT_STEPS = [
    "ECG",
    "Insert wide bore cannula (pink)",
    "FBC",
    "U&E",
    "LFT",
]


def assess(
    entities: list[AnnotatedEntity],
    vitals_score: VitalsScore,
    patient_id: str | None = None,
) -> RiskAssessment:
    t0 = time.perf_counter()

    # Phase 1: Deduplicate entities — 1 point per unique canonical group
    scored_entities = deduplicate_and_score(entities)
    entity_score = sum(s for _, s in scored_entities)

    # Phase 2: Combined score = entity count + vital flag count (no weights)
    combined_score = float(entity_score + vitals_score.total_points)

    # Phase 3: Map integer total to PE risk level
    risk_level = _score_to_risk(combined_score)

    # Phase 4: Build structured outputs
    contributions = _build_contributions(scored_entities)
    vitals_flags = [
        VitalsFlag(field=f, value=v, points=p, reason=r)
        for f, v, p, r in vitals_score.flagged_fields
    ]

    suggested_diagnosis = _suggested_diagnosis(risk_level)
    if risk_level != RiskLevel.LOW:
        next_steps = PE_NEXT_STEPS
    elif combined_score >= 1:
        next_steps = LOW_RISK_NEXT_STEPS
    else:
        next_steps = []

    reasoning = _build_reasoning(risk_level, contributions, vitals_flags)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return RiskAssessment(
        patient_id=patient_id,
        risk_level=risk_level,
        combined_score=combined_score,
        entity_score=float(entity_score),
        vitals_score=vitals_score.total_points,
        entity_contributions=contributions,
        vitals_flags=vitals_flags,
        override_triggered=False,
        override_reason=None,
        reasoning_text=reasoning,
        suggested_diagnosis=suggested_diagnosis,
        next_steps=next_steps,
        processing_time_ms=elapsed_ms,
    )


def _score_to_risk(score: float) -> RiskLevel:
    for level, threshold in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return RiskLevel.LOW


def _suggested_diagnosis(risk_level: RiskLevel) -> str | None:
    if risk_level == RiskLevel.LOW:
        return None
    if risk_level == RiskLevel.CRITICAL:
        return "Possible Pulmonary Embolism — haemodynamically compromised"
    return "Possible Pulmonary Embolism"


def _build_contributions(
    scored: list[tuple[AnnotatedEntity, int]],
) -> list[EntityContribution]:
    return [
        EntityContribution(
            text=ent.text,
            label=ent.label,
            is_negated=ent.is_negated,
            severity=get_severity(ent),
            weight=1.0,                     # uniform — all features equal
            score_contribution=float(score),
        )
        for ent, score in scored
    ]


def _build_reasoning(
    risk_level: RiskLevel,
    contributions: list[EntityContribution],
    vitals_flags: list[VitalsFlag],
) -> str:
    # Scored (counted) vs negated vs visible-but-duplicate
    counted  = [c for c in contributions if c.score_contribution == 1.0]
    negated  = [c for c in contributions if c.is_negated]
    # (duplicates have score_contribution==0 and is_negated==False — shown but not counted)

    if risk_level == RiskLevel.LOW:
        parts = ["Not suggestive of PE."]
        if not counted:
            parts.append(
                "No PE-specific features were detected in the clinical history."
            )
        if negated:
            neg_summary = ", ".join(c.text for c in negated[:3])
            parts.append(
                f"The following features were explicitly negated and not counted:"
                f" {neg_summary}."
            )
        if not vitals_flags:
            parts.append("Vital signs show no PE-relevant abnormalities.")
        return " ".join(parts)

    # MEDIUM / HIGH / CRITICAL
    if risk_level == RiskLevel.CRITICAL:
        parts = [
            "This presentation is very concerning for Pulmonary Embolism"
            " with possible haemodynamic compromise."
        ]
    elif risk_level == RiskLevel.HIGH:
        parts = ["This presentation is concerning for possible Pulmonary Embolism."]
    else:
        parts = [
            "This presentation has features that may be consistent with"
            " Pulmonary Embolism."
        ]

    pe_symptoms     = [c for c in counted if c.label == "PE_SYMPTOM"]
    pe_risk_factors = [c for c in counted if c.label == "PE_RISK_FACTOR"]

    if pe_symptoms:
        sym_summary = ", ".join(c.text for c in pe_symptoms[:6])
        parts.append(f"PE-relevant symptoms/signs: {sym_summary}.")

    if pe_risk_factors:
        rf_summary = ", ".join(c.text for c in pe_risk_factors[:5])
        parts.append(f"PE risk factors identified: {rf_summary}.")

    if negated:
        neg_summary = ", ".join(c.text for c in negated[:3])
        parts.append(
            f"The following were explicitly negated (not counted): {neg_summary}."
        )

    if vitals_flags:
        vitals_summary = "; ".join(f.reason for f in vitals_flags)
        parts.append(f"PE-relevant vital sign abnormalities: {vitals_summary}.")
    else:
        parts.append("No PE-relevant vital sign abnormalities detected.")

    return " ".join(parts)
