"""Priority mapper — combines all layers into a single final priority tier.

Receives the outputs of:
  - Layer 3 (existing rules engine): risk_level, combined_score,
                                     entity_contributions
  - Layer 1 (escalation_rules):      EscalationResult
  - Layer 2 (symptom_flags):         SymptomFlagResult
  - Chest pain safety screen:        ChestPainSafetyResult

And produces a FinalPriority that populates the new fields on RiskAssessment
without touching any of the existing fields.

Combining logic (steps applied in order, final tier = highest reached):

  Step 1 — Base tier from existing PE risk level:
    CRITICAL  → IMMEDIATE    (0 min,   RED)
    HIGH      → VERY_URGENT  (10 min,  ORANGE)
    MEDIUM    → URGENT       (60 min,  YELLOW)
    LOW, score >= 1 → STANDARD    (120 min, GREEN)
    LOW, score == 0 → NON_URGENT  (240 min, BLUE)

  Step 2 — Apply Layer 1 vital hard escalators:
    If triggered → raise to escalation tier if higher than base.

  Step 3 — Apply Layer 2 symptom floor:
    If priority_floor set → raise to that floor if higher than current.
    If dvt_chest_combo_detected → bump current tier up one level.

  Step 4 — Apply chest pain safety floor:
    If screen_triggered → enforce minimum STANDARD.
    If red_flags_detected → enforce minimum URGENT.

The highest tier reached across all four steps is the final output.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from clinical_nlp.schemas.output import RiskLevel, EntityContribution
from clinical_nlp.vitals.escalation_rules import EscalationResult
from clinical_nlp.rules_engine.symptom_flags import SymptomFlagResult
from clinical_nlp.rules_engine.chest_pain_safety import ChestPainSafetyResult

# ── Tier definitions ──────────────────────────────────────────────────────────
_TIERS: list[tuple[str, int, str]] = [
    # (tier_name,    max_wait_minutes, colour)
    ("NON_URGENT",  240, "BLUE"),
    ("STANDARD",    120, "GREEN"),
    ("URGENT",       60, "YELLOW"),
    ("VERY_URGENT",  10, "ORANGE"),
    ("IMMEDIATE",     0, "RED"),
]

# Index lookup: tier_name → position in _TIERS (higher = more urgent)
_TIER_INDEX: dict[str, int] = {t[0]: i for i, t in enumerate(_TIERS)}


def _higher(a: str, b: str) -> str:
    """Return whichever tier is more urgent (higher index)."""
    return a if _TIER_INDEX[a] >= _TIER_INDEX[b] else b


def _bump(tier: str) -> str:
    """Move a tier one step more urgent. IMMEDIATE stays IMMEDIATE."""
    idx = _TIER_INDEX[tier]
    new_idx = min(idx + 1, len(_TIERS) - 1)
    return _TIERS[new_idx][0]


def _tier_meta(tier: str) -> tuple[int, str]:
    """Return (max_wait_minutes, colour) for a given tier name."""
    for name, wait, colour in _TIERS:
        if name == tier:
            return wait, colour
    return 240, "BLUE"  # safe fallback


@dataclass
class FinalPriority:
    """Combined output of all four priority layers."""

    priority_tier: str
    """Final MTS-derived tier: IMMEDIATE | VERY_URGENT | URGENT |
    STANDARD | NON_URGENT."""

    max_wait_minutes: int
    """Maximum safe waiting time in minutes."""

    priority_colour: str
    """Display colour: RED | ORANGE | YELLOW | GREEN | BLUE."""

    priority_basis: str
    """Concatenated human-readable explanation from all layers that fired."""

    clarification_required: bool = False
    """Forwarded from EscalationResult when COPD question is needed."""

    clarification_question: Optional[str] = None
    """Forwarded from EscalationResult when clarification_required is True."""

    chest_pain_safety_flags: list[str] = field(default_factory=list)
    """Red-flag differentials detected by the chest pain safety screen."""

    next_steps_override: Optional[list[str]] = None
    """When set, replaces the existing PE next_steps on RiskAssessment.
    Populated only when the chest pain safety screen fires."""


def map_priority(
    risk_level: RiskLevel,
    combined_score: float,
    entity_contributions: list[EntityContribution],
    escalation: EscalationResult,
    symptom_flags: SymptomFlagResult,
    chest_pain_safety: ChestPainSafetyResult,
) -> FinalPriority:
    """Combine all layer outputs into a single final priority tier.

    Args:
        risk_level:          PE risk level from the existing rules engine.
        combined_score:      Combined entity + vitals score from existing engine.
        entity_contributions: Entity list from existing engine (read-only).
        escalation:          Result from Layer 1 (escalation_rules).
        symptom_flags:       Result from Layer 2 (symptom_flags).
        chest_pain_safety:   Result from chest pain safety screen.

    Returns:
        FinalPriority populated with the highest tier reached and full audit
        trail of which layers contributed.
    """
    reasons: list[str] = []

    # ── Step 1: Base tier from PE risk level (silent — not shown in banner) ───
    # The banner displays only objective vital sign and symptom triggers.
    # PE risk level is already shown in the results section below the banner.
    if risk_level == RiskLevel.CRITICAL:
        tier = "URGENT"
    elif risk_level == RiskLevel.HIGH:
        tier = "VERY_URGENT"
    elif risk_level == RiskLevel.MEDIUM:
        tier = "URGENT"
    else:
        # LOW risk
        tier = "STANDARD" if combined_score >= 1 else "NON_URGENT"

    # ── Step 2: Layer 1 — vital sign hard escalators ──────────────────────────
    # Each individual trigger is added separately so the final numbered list
    # gives every finding its own number (e.g. 1. Respiratory... 2. Circulatory...)
    if escalation.triggered and escalation.priority_tier:
        tier = _higher(tier, escalation.priority_tier)
        if escalation.priority_bases:
            reasons.extend(escalation.priority_bases)
        elif escalation.priority_basis:
            reasons.append(escalation.priority_basis)

    # ── Step 3: Layer 2 — symptom floor ──────────────────────────────────────
    if symptom_flags.triggered:
        if symptom_flags.priority_floor:
            tier = _higher(tier, symptom_flags.priority_floor)
            reasons.append(symptom_flags.priority_basis)
        if symptom_flags.dvt_chest_combo_detected:
            before = tier
            tier = _bump(tier)
            if tier != before:
                reasons.append(
                    "DVT signs combined with chest/respiratory symptoms detected."
                )

    # ── Step 4: Chest pain safety floor ──────────────────────────────────────
    if chest_pain_safety.screen_triggered:
        floor = chest_pain_safety.recommended_priority_floor or "STANDARD"
        tier = _higher(tier, floor)
        if chest_pain_safety.red_flags_detected:
            flag_summary = "; ".join(chest_pain_safety.red_flags_detected)
            reasons.append(
                f"Chest pain safety screen: red flags detected — {flag_summary}."
            )
        else:
            reasons.append(
                "Chest pain safety screen: no red flags detected but chest pain present."
            )

    # ── Assemble final output — number each trigger for readability ───────────
    if reasons:
        numbered_basis = " ".join(f"{i + 1}. {r}" for i, r in enumerate(reasons))
    else:
        numbered_basis = "No objective escalation triggers detected."

    wait, colour = _tier_meta(tier)

    # Next steps override: chest pain safety screen result takes precedence
    # for LOW risk chest pain presentations
    next_steps_override = (
        chest_pain_safety.next_steps
        if chest_pain_safety.screen_triggered and chest_pain_safety.next_steps
        else None
    )

    return FinalPriority(
        priority_tier=tier,
        max_wait_minutes=wait,
        priority_colour=colour,
        priority_basis=numbered_basis,
        clarification_required=escalation.clarification_required,
        clarification_question=escalation.clarification_question,
        chest_pain_safety_flags=chest_pain_safety.red_flags_detected,
        next_steps_override=next_steps_override,
    )
