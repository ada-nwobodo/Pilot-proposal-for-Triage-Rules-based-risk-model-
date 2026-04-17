"""Layer 1 — Vital signs hard escalators.

Applies MTS-derived priority escalation rules based on objective vital sign
readings. ALL matching rules are evaluated and returned together so that
co-existing problems (e.g. low SpO2 AND tachycardia) are each reported
independently in the priority banner.

IMMEDIATE triggers:
  1. Unconscious / Unresponsive  — GCS <= 8
  2. Haemodynamic shock          — hypotension (SBP<=90 or DBP<=60) + HR > 120
  3. Critical hypoxia            — SpO2 < 85%
  4. Severe tachypnoea           — RR >= 35
  5. Respiratory depression      — RR < 10

VERY URGENT triggers:
  6. Severe hypoxia              — SpO2 85–89%  (COPD annotation if applicable)
  7. Moderate tachypnoea         — RR 25–34
  8. Combined hypoxia+tachypnoea — SpO2 90–93% AND RR >= 22
                                   (guard: SpO2 > 89% prevents overlap with Rule 6)
  9. Tachycardia alone           — HR >= 120
                                   (guard: not already caught as haemodynamic shock)
  10. Bradycardia alone          — HR < 60

Overlap guards
--------------
- Rule 8 only fires when SpO2 is 90–93% (not 85–89%) to avoid duplicating Rule 6.
- Rule 9 only fires when the patient is NOT in haemodynamic shock (Rule 2), since
  shock already captures the tachycardia component.

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

# Tier order used to determine the highest tier across all triggered rules
_TIER_ORDER = {IMMEDIATE: 2, VERY_URGENT: 1, URGENT: 0}


@dataclass
class EscalationResult:
    """Output of the Layer 1 vital signs escalation check."""

    triggered: bool
    """True if any hard escalator fired."""

    priority_tier: Optional[str] = None
    """IMMEDIATE | VERY_URGENT | URGENT, or None if no escalator fired."""

    priority_basis: str = ""
    """Human-readable explanation of all rules that triggered, including the
    exact recorded vital sign values. Multiple triggers are separated by ' | '."""

    clarification_required: bool = False
    """True when SpO2 is 85–89% and known_copd has not been answered (None)."""

    clarification_question: Optional[str] = None
    """Populated when clarification_required is True."""


def apply_escalation_rules(vitals: Optional[VitalSigns]) -> EscalationResult:
    """Evaluate ALL Layer 1 hard escalators against the supplied vital signs.

    Every matching rule is collected. The final priority_tier is the highest
    tier reached across all triggered rules. The priority_basis contains each
    triggered rule's explanation, separated by ' | ', so co-existing problems
    (e.g. low SpO2 AND tachycardia) are both visible in the priority banner.

    Args:
        vitals: VitalSigns object from the clinical input (may be None).

    Returns:
        EscalationResult describing all triggered rules and the highest tier.
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

    # Collect all triggered rules as (tier, basis_text) tuples
    triggered: list[tuple[str, str]] = []
    clarification_required = False
    clarification_question: Optional[str] = None

    # Pre-compute shared conditions used by multiple rules
    hypotensive       = (sbp is not None and sbp <= 90) or (dbp is not None and dbp <= 60)
    tachycardic_shock = hr is not None and hr > HR_SHOCK_THRESHOLD
    in_shock          = hypotensive and tachycardic_shock

    # ══════════════════════════════════════════════════════════════════════════
    # IMMEDIATE RULES
    # ══════════════════════════════════════════════════════════════════════════

    # Rule 1 — Unconscious / Unresponsive: GCS <= 8
    if gcs is not None and gcs <= GCS_IMMEDIATE_THRESHOLD:
        triggered.append((IMMEDIATE, (
            f"Unconscious/Unresponsive: GCS {gcs} "
            f"(threshold \u2264{GCS_IMMEDIATE_THRESHOLD}) \u2014 {_ESCALATE_NOW}"
        )))

    # Rule 2 — Haemodynamic shock: hypotension + HR > 120
    if in_shock:
        bp_part = (
            f"SBP {int(sbp)}mmHg" if sbp is not None and sbp <= 90
            else f"DBP {int(dbp)}mmHg"
        )
        triggered.append((IMMEDIATE, (
            f"Haemodynamic shock: {bp_part} + HR {int(hr)}bpm "
            f"(threshold HR >{int(HR_SHOCK_THRESHOLD)}) \u2014 {_ESCALATE_NOW}"
        )))

    # Rule 3 — Critical hypoxia: SpO2 < 85%
    if sp is not None and sp < SPO2_CRITICAL_THRESHOLD:
        triggered.append((IMMEDIATE, (
            f"Respiratory Compromise: SpO\u2082 {sp}% "
            f"(critical hypoxia \u2014 threshold <{int(SPO2_CRITICAL_THRESHOLD)}%) "
            f"\u2014 {_ESCALATE_NOW}"
        )))

    # Rule 4 — Severe tachypnoea: RR >= 35
    if rr is not None and rr >= RR_IMMEDIATE_THRESHOLD:
        triggered.append((IMMEDIATE, (
            f"Respiratory Compromise: RR {int(rr)} breaths/min "
            f"(severe tachypnoea \u2014 threshold \u2265{int(RR_IMMEDIATE_THRESHOLD)}) "
            f"\u2014 {_ESCALATE_NOW}"
        )))

    # Rule 5 — Respiratory depression: RR < 10
    if rr is not None and rr < RR_DEPRESSION_THRESHOLD:
        triggered.append((IMMEDIATE, (
            f"Respiratory Compromise: RR {int(rr)} breaths/min "
            f"(respiratory depression \u2014 threshold <{int(RR_DEPRESSION_THRESHOLD)}) "
            f"\u2014 {_ESCALATE_NOW}"
        )))

    # ══════════════════════════════════════════════════════════════════════════
    # VERY URGENT RULES
    # ══════════════════════════════════════════════════════════════════════════

    # Rule 6 — Severe hypoxia: SpO2 85–89%
    # Natural guard: SPO2_CRITICAL_THRESHOLD (85) <= sp <= SPO2_SEVERE_THRESHOLD (89)
    # so this cannot overlap with Rule 3 (sp < 85).
    if sp is not None and SPO2_CRITICAL_THRESHOLD <= sp <= SPO2_SEVERE_THRESHOLD:
        copd_note = ""

        if known_copd is True:
            copd_note = (
                " Note: known COPD \u2014 consider whether "
                f"SpO\u2082 {sp}% represents this patient\u2019s usual baseline "
                "before escalating further."
            )
        elif known_copd is None:
            clarification_required = True
            copd_note = " COPD status not confirmed \u2014 please clarify with nurse."
            clarification_question = (
                f"SpO\u2082 recorded as {sp}%. "
                "Does this patient have a known diagnosis of COPD?\n"
                "\u2610 Yes \u2014 known COPD\n"
                "\u2610 No / Not known"
            )

        triggered.append((VERY_URGENT, (
            f"Respiratory Compromise: SpO\u2082 {sp}% "
            f"(severe hypoxia \u2014 range {int(SPO2_CRITICAL_THRESHOLD)}"
            f"\u2013{int(SPO2_SEVERE_THRESHOLD)}%) "
            f"\u2014 Very Urgent (10 min).{copd_note}"
        )))

    # Rule 7 — Moderate tachypnoea: RR 25–34
    # Natural guard: RR_VU_THRESHOLD (25) <= rr < RR_IMMEDIATE_THRESHOLD (35)
    # so this cannot overlap with Rule 4 (rr >= 35) or Rule 5 (rr < 10).
    if rr is not None and RR_VU_THRESHOLD <= rr < RR_IMMEDIATE_THRESHOLD:
        triggered.append((VERY_URGENT, (
            f"Respiratory Compromise: RR {int(rr)} breaths/min "
            f"(moderate tachypnoea \u2014 range "
            f"{int(RR_VU_THRESHOLD)}\u2013{int(RR_IMMEDIATE_THRESHOLD) - 1}) "
            "\u2014 Very Urgent (10 min)."
        )))

    # Rule 8 — Combined hypoxia + tachypnoea: SpO2 90–93% AND RR >= 22
    # Explicit guard: sp > SPO2_SEVERE_THRESHOLD (89) prevents overlap with Rule 6.
    # This rule is intended for the SpO2 90–93% band not covered by Rule 6.
    if (sp is not None and sp > SPO2_SEVERE_THRESHOLD and sp <= 93
            and rr is not None and rr >= 22):
        triggered.append((VERY_URGENT, (
            f"Respiratory Compromise: SpO\u2082 {sp}% and RR {int(rr)} breaths/min "
            "(combined hypoxia + tachypnoea) \u2014 Very Urgent (10 min)."
        )))

    # Rule 9 — Tachycardia alone: HR >= 120
    # Explicit guard: not in_shock prevents double-reporting when Rule 2 already
    # covers the tachycardia as part of haemodynamic shock.
    if hr is not None and hr >= HR_SHOCK_THRESHOLD and not in_shock:
        triggered.append((VERY_URGENT, (
            f"Tachycardia: HR {int(hr)}bpm "
            f"(threshold \u2265{int(HR_SHOCK_THRESHOLD)}) \u2014 Very Urgent (10 min)."
        )))

    # Rule 10 — Bradycardia alone: HR < 60
    if hr is not None and hr < HR_BRADYCARDIA_THRESHOLD:
        triggered.append((VERY_URGENT, (
            f"Bradycardia: HR {int(hr)}bpm "
            f"(threshold <{int(HR_BRADYCARDIA_THRESHOLD)}) \u2014 Very Urgent (10 min)."
        )))

    # ── No escalation rule fired ──────────────────────────────────────────────
    if not triggered:
        return EscalationResult(triggered=False)

    # ── Highest tier across all triggered rules ───────────────────────────────
    highest_tier = max(triggered, key=lambda x: _TIER_ORDER.get(x[0], 0))[0]

    # ── Combine all basis strings separated by ' | ' ──────────────────────────
    combined_basis = " | ".join(basis for _, basis in triggered)

    return EscalationResult(
        triggered=True,
        priority_tier=highest_tier,
        priority_basis=combined_basis,
        clarification_required=clarification_required,
        clarification_question=clarification_question,
    )
