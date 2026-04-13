"""Layer 1 — Vital signs hard escalators.

Applies MTS-derived priority escalation rules based on objective vital sign
readings. Rules are evaluated in order; the first matching rule determines the
output (highest-severity match wins by placement order).

This module is entirely independent of the existing PE risk scorer. It reads
VitalSigns and returns an EscalationResult that is later consumed by
priority_mapper.py. The existing VITAL_THRESHOLDS / scorer.py pipeline is
not affected in any way.

COPD clarification gate
-----------------------
When SpO2 < SPO2_SEVERE_THRESHOLD and known_copd is None (not answered),
the rule still defaults to IMMEDIATE for safety, but also sets
clarification_required=True so the frontend can prompt the nurse.
If known_copd is True the severe SpO2 rule is suppressed entirely.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from clinical_nlp.schemas.input import VitalSigns
from clinical_nlp.vitals.thresholds import (
    HR_BRADYCARDIA_THRESHOLD,
    SPO2_SEVERE_THRESHOLD,
    RR_SEVERE_THRESHOLD,
)

# ── Priority tier constants (shared with priority_mapper.py) ─────────────────
IMMEDIATE   = "IMMEDIATE"    # 0 min  — RED
VERY_URGENT = "VERY_URGENT"  # 10 min — ORANGE
URGENT      = "URGENT"       # 60 min — YELLOW


@dataclass
class EscalationResult:
    """Output of the Layer 1 vital signs escalation check."""

    triggered: bool
    """True if any hard escalator fired."""

    priority_tier: Optional[str] = None
    """IMMEDIATE | VERY_URGENT | URGENT, or None if no escalator fired."""

    priority_basis: str = ""
    """Human-readable explanation of which rule triggered and why."""

    clarification_required: bool = False
    """True when SpO2 <90% but known_copd has not been answered (None).
    The system defaults to IMMEDIATE for safety but asks the nurse to confirm."""

    clarification_question: Optional[str] = None
    """Populated when clarification_required is True."""


def apply_escalation_rules(vitals: Optional[VitalSigns]) -> EscalationResult:
    """Evaluate Layer 1 hard escalators against the supplied vital signs.

    Rules are tested in priority order. The first rule that fires is returned.
    If vitals is None or all readings are absent, no escalation is triggered.

    Args:
        vitals: VitalSigns object from the clinical input (may be None).

    Returns:
        EscalationResult describing whether and why escalation was triggered.
    """
    if vitals is None:
        return EscalationResult(triggered=False)

    hr  = vitals.heart_rate
    sbp = vitals.systolic_bp
    dbp = vitals.diastolic_bp
    rr  = vitals.respiratory_rate
    sp  = vitals.spo2
    known_copd = vitals.known_copd

    # ── Rule 1: Circulatory compromise — hypotension + tachycardia ───────────
    hypotensive = (sbp is not None and sbp <= 90) or (dbp is not None and dbp <= 60)
    tachycardic = hr is not None and hr > 100
    if hypotensive and tachycardic:
        bp_part = (
            f"SBP {sbp} mmHg" if sbp is not None and sbp <= 90
            else f"DBP {dbp} mmHg"
        )
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Circulatory compromise: hypotension ({bp_part}) combined with "
                f"tachycardia (HR {hr} bpm) — Immediate (0 min)."
            ),
        )

    # ── Rule 2: Severe hypoxia — SpO2 < 90% (COPD conditional) ──────────────
    if sp is not None and sp < SPO2_SEVERE_THRESHOLD:
        if known_copd is True:
            # COPD confirmed — severe SpO2 rule suppressed; falls through to
            # standard combined threshold (Rule 4) if applicable.
            pass
        else:
            # known_copd is False or None — escalate to IMMEDIATE.
            # If None, also request clarification from the nurse.
            needs_clarification = known_copd is None
            question = (
                f"SpO\u2082 recorded as {sp}%. "
                "Does this patient have a known diagnosis of COPD?\n"
                "\u2610 Yes \u2014 known COPD\n"
                "\u2610 No / Not known"
            ) if needs_clarification else None
            return EscalationResult(
                triggered=True,
                priority_tier=IMMEDIATE,
                priority_basis=(
                    f"Severe hypoxia: SpO\u2082 {sp}% (threshold <{SPO2_SEVERE_THRESHOLD}%) "
                    "— Immediate (0 min)."
                    + (" COPD status unconfirmed — defaulting to Immediate for safety."
                       if needs_clarification else "")
                ),
                clarification_required=needs_clarification,
                clarification_question=question,
            )

    # ── Rule 3: Severe tachypnoea — RR ≥ 25 ─────────────────────────────────
    if rr is not None and rr >= RR_SEVERE_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=IMMEDIATE,
            priority_basis=(
                f"Severe tachypnoea: RR {rr} breaths/min "
                f"(threshold \u2265{RR_SEVERE_THRESHOLD}) — Immediate (0 min)."
            ),
        )

    # ── Rule 4: Combined SpO2 ≤ 93% + RR ≥ 22 ───────────────────────────────
    hypoxic_combined     = sp is not None and sp <= 93
    tachypnoeic_combined = rr is not None and rr >= 22
    if hypoxic_combined and tachypnoeic_combined:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Respiratory compromise: SpO\u2082 {sp}% and RR {rr} breaths/min "
                "— Very Urgent (10 min)."
            ),
        )

    # ── Rule 5: Tachycardia alone — HR > 100 ─────────────────────────────────
    if tachycardic:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Tachycardia: HR {hr} bpm (threshold >100) — Very Urgent (10 min)."
            ),
        )

    # ── Rule 6: Bradycardia alone — HR < 60 ──────────────────────────────────
    if hr is not None and hr < HR_BRADYCARDIA_THRESHOLD:
        return EscalationResult(
            triggered=True,
            priority_tier=VERY_URGENT,
            priority_basis=(
                f"Bradycardia: HR {hr} bpm "
                f"(threshold <{HR_BRADYCARDIA_THRESHOLD}) — Very Urgent (10 min)."
            ),
        )

    # ── No escalation rule fired ──────────────────────────────────────────────
    return EscalationResult(triggered=False)
