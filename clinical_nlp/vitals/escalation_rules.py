"""Layer 1 — Vital signs hard escalators.

Applies MTS-derived priority escalation rules based on objective vital sign
readings. Rules are evaluated in priority order; IMMEDIATE rules are checked
before VERY URGENT rules.

IMMEDIATE triggers (the only three categories):
  1. Unconscious / Unresponsive  — GCS <= 8
  2. Haemodynamic shock          — hypotension (SBP<=90 or DBP<=60) + HR > 120
  3. Respiratory Compromise      — SpO2 < 85%  OR  RR >= 35  OR  RR < 10

VERY URGENT triggers:
  4. Severe hypoxia              — SpO2 85–89%  (COPD annotation if applicable)
  5. Moderate tachypnoea         — RR 25–34
  6. Combined hypoxia+tachypnoea — SpO2 <= 93% AND RR >= 22
  7. Tachycardia alone           — HR >= 120
  8. Bradycardia alone           — HR < 60

COPD clarification gate (SpO2 85–89% only)
------------------------------------------
SpO2 < 85% is always IMMEDIATE regardless of COPD status.
SpO2 85–89%:
  known_copd True  → VERY URGENT + context note (may be patient's baseline)
  known_copd None  → VERY URGENT + clarification_required=True
  known_copd False → VERY URGENT, no annotation

This module is entirely independent of the existing PE risk scorer.
The existing VITAL_THRESHOLDS / scorer.py pipeline is not affected.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from clinical_nlp.schemas.input import VitalSigns
from clinical_nlp.vitals.thresholds import (
    HR_SHOCK_THRESHOLD,
    HR_BRADYCARDIA_THRESHOLD,
    SPO2_CRITICAL_THRESHOLD,
    SPO2_SEVERE_THRESHOLD,
    RR_IMMEDIATE_THRESHOLD,
    RR_DEPRESSION_THRESHOLD,
    RR_VU_THRESHOLD,
    GCS_IMMEDIATE_THRESHOLD,
)

# ── Priority tier constants ───────────────────────────────────────────────────
IMMEDIATE   = "IMMEDIATE"    # 0 min  — RED
VERY_URGENT = "VERY_URGENT"  # 10 min — ORANGE
URGENT      = "URGENT"       # 60 min — YELLOW

_ESCALATE_NOW = "IMMEDIATE: escalate immediately to a senior doctor."


@dataclass
class EscalationResult:
    """Output of the Layer 1 vital signs escalation check."""

    triggered: bool
    """True if any hard escalator fired."""

    priority_tier: Optional[str] = None
    """IMMEDIATE | VERY_URGENT | URGENT, or None if no escalator fired."""

    priority_basis: str = ""
    """Human-readable explanation of which rule triggered, including the
    exact recorded vital sign values."""

    clarification_required: bool = False
    """True when SpO2 is 85–89% and known_copd has not been answered (None)."""

    clarification_question: Optional[str] = None
    """Populated when clarification_required is True."""


def apply_escalation_rules(vitals: Optional[VitalSigns]) -> EscalationResult:
    """Evaluate Layer 1 hard escalators against the supplied vital signs.

    IMMEDIATE rules are checked first (GCS → shock → SpO2 → RR).
    VERY URGENT rules follow. The first matching rule is returned.

    Args:
        vitals: VitalSigns object from the clinical input (may be None).

    Returns:
        EscalationResult describing whether and why escalation was triggered.
    """
    if vitals is None:
        return EscalationResult(triggered=False)

    hr         = vitals.heart_rate
    sbp        = vitals.systolic_bp
    dbp        = vitals.diastolic_bp
    rr         = vitals.respiratory_rate
    sp         = vitals.spo2
    gcs        = vitals.gcs
    known_copd = vitals.known_copd

    # ══════════════════════════════════════════════════════════════════════════
    # IMMEDIATE RULES
    # ══════════════════════════════════════════════════════════════════════════

    # Rule 1 — Unconscious / Unresponsive: GCS <= 8
    if gcs is not None and gcs <= GCS_IMMEDIATE_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Unconscious/Unresponsive: GCS {gcs} "
                f"(threshold \u2264{GCS_IMMEDIATE_THRESHOLD}) \u2014 {_ESCALATE_NOW}"
            ),
        )

    # Rule 2 — Haemodynamic shock: hypotension + HR > 120
    hypotensive       = (sbp is not None and sbp <= 90) or (dbp is not None and dbp <= 60)
    tachycardic_shock = hr is not None and hr > HR_SHOCK_THRESHOLD
    if hypotensive and tachycardic_shock:
        bp_part = (
            f"SBP {int(sbp)}mmHg" if sbp is not None and sbp <= 90
            else f"DBP {int(dbp)}mmHg"
        )
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Haemodynamic shock: {bp_part} + HR {int(hr)}bpm "
                f"(threshold HR >{int(HR_SHOCK_THRESHOLD)}) \u2014 {_ESCALATE_NOW}"
            ),
        )

    # Rule 3 — Respiratory Compromise: critical hypoxia SpO2 < 85%
    # Applied regardless of COPD status — SpO2 < 85% is an emergency for all.
    if sp is not None and sp < SPO2_CRITICAL_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Respiratory Compromise: SpO\u2082 {sp}% "
                f"(critical hypoxia \u2014 threshold <{int(SPO2_CRITICAL_THRESHOLD)}%) "
                f"\u2014 {_ESCALATE_NOW}"
            ),
        )

    # Rule 4 — Respiratory Compromise: RR >= 35 (severe tachypnoea)
    if rr is not None and rr >= RR_IMMEDIATE_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Respiratory Compromise: RR {int(rr)} breaths/min "
                f"(severe tachypnoea \u2014 threshold \u2265{int(RR_IMMEDIATE_THRESHOLD)}) "
                f"\u2014 {_ESCALATE_NOW}"
            ),
        )

    # Rule 5 — Respiratory Compromise: RR < 10 (respiratory depression)
    if rr is not None and rr < RR_DEPRESSION_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Respiratory Compromise: RR {int(rr)} breaths/min "
                f"(respiratory depression \u2014 threshold <{int(RR_DEPRESSION_THRESHOLD)}) "
                f"\u2014 {_ESCALATE_NOW}"
            ),
        )

    # ══════════════════════════════════════════════════════════════════════════
    # VERY URGENT RULES
    # ══════════════════════════════════════════════════════════════════════════

    # Rule 6 — Severe hypoxia: SpO2 85–89%
    # At this point sp >= SPO2_CRITICAL_THRESHOLD (85) is guaranteed.
    if sp is not None and sp <= SPO2_SEVERE_THRESHOLD:
        copd_note           = ""
        needs_clarification = False
        question            = None

        if known_copd is True:
            copd_note = (
                " Note: known COPD — consider whether "
                f"SpO\u2082 {sp}% represents this patient's usual baseline "
                "before escalating further."
            )
        elif known_copd is None:
            needs_clarification = True
            copd_note = " COPD status not confirmed — please clarify with nurse."
            question = (
                f"SpO\u2082 recorded as {sp}%. "
                "Does this patient have a known diagnosis of COPD?\n"
                "\u2610 Yes \u2014 known COPD\n"
                "\u2610 No / Not known"
            )

        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Respiratory Compromise: SpO\u2082 {sp}% "
                f"(severe hypoxia \u2014 range {int(SPO2_CRITICAL_THRESHOLD)}"
                f"\u2013{int(SPO2_SEVERE_THRESHOLD)}%) "
                f"\u2014 Very Urgent (10 min).{copd_note}"
            ),
            clarification_required=needs_clarification,
            clarification_question=question,
        )

    # Rule 7 — Moderate tachypnoea: RR 25–34
    # At this point rr < RR_IMMEDIATE_THRESHOLD (35) and rr >= RR_DEPRESSION_THRESHOLD (10)
    # are both guaranteed.
    if rr is not None and rr >= RR_VU_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Respiratory Compromise: RR {int(rr)} breaths/min "
                f"(moderate tachypnoea \u2014 range "
                f"{int(RR_VU_THRESHOLD)}\u2013{int(RR_IMMEDIATE_THRESHOLD) - 1}) "
                "\u2014 Very Urgent (10 min)."
            ),
        )

    # Rule 8 — Combined hypoxia + tachypnoea: SpO2 <= 93% AND RR >= 22
    hypoxic_combined     = sp is not None and sp <= 93
    tachypnoeic_combined = rr is not None and rr >= 22
    if hypoxic_combined and tachypnoeic_combined:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Respiratory Compromise: SpO\u2082 {sp}% and RR {int(rr)} breaths/min "
                "(combined hypoxia + tachypnoea) \u2014 Very Urgent (10 min)."
            ),
        )

    # Rule 9 — Tachycardia alone: HR >= 120
    tachycardic_vu = hr is not None and hr >= HR_SHOCK_THRESHOLD
    if tachycardic_vu:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Tachycardia: HR {int(hr)}bpm "
                f"(threshold \u2265{int(HR_SHOCK_THRESHOLD)}) \u2014 Very Urgent (10 min)."
            ),
        )

    # Rule 10 — Bradycardia alone: HR < 60
    if hr is not None and hr < HR_BRADYCARDIA_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Bradycardia: HR {int(hr)}bpm "
                f"(threshold <{int(HR_BRADYCARDIA_THRESHOLD)}) \u2014 Very Urgent (10 min)."
            ),
        )

    # ── No escalation rule fired ──────────────────────────────────────────────
    return EscalationResult(triggered=False)
