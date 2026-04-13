"""Layer 2 — Keyword-driven symptom escalators.

Inspects the list of annotated entities already produced by the existing NLP
pipeline and applies MTS-derived escalation floors based on the presence of
specific high-acuity symptom groups.

This module is read-only with respect to the entity list — it does not modify
any existing entity objects. It produces a SymptomFlagResult that is consumed
downstream by priority_mapper.py.

Rules applied (in order of severity):
  1. Haemoptysis (non-negated)              → minimum VERY_URGENT
  2. Syncope / collapse (non-negated)       → minimum VERY_URGENT
  3. Sudden-onset SOB (non-negated, SEVERE) → minimum URGENT
  4. Pleuritic chest pain (non-negated)     → minimum URGENT
  5. Leg DVT signs + chest/SOB combo        → dvt_chest_combo_detected=True
                                              (priority_mapper bumps one tier)

Rules 1–4 set a priority_floor; the highest floor across all fired rules is
returned. Rule 5 is a separate flag handled by priority_mapper.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from clinical_nlp.phrase_matcher import AnnotatedEntity, get_severity
from clinical_nlp.schemas.output import Severity
from clinical_nlp.rules_engine.entity_scorer import canonical_group

# ── Priority tier constants (mirrors escalation_rules.py) ────────────────────
IMMEDIATE   = "IMMEDIATE"    # 0 min  — RED
VERY_URGENT = "VERY_URGENT"  # 10 min — ORANGE
URGENT      = "URGENT"       # 60 min — YELLOW

# Tier ordering — higher index = more urgent
_TIER_ORDER = {None: 0, URGENT: 1, VERY_URGENT: 2, IMMEDIATE: 3}


def _higher(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Return whichever tier is more urgent."""
    return a if _TIER_ORDER.get(a, 0) >= _TIER_ORDER.get(b, 0) else b


@dataclass
class SymptomFlagResult:
    """Output of the Layer 2 symptom escalation check."""

    triggered: bool
    """True if any symptom escalation rule fired."""

    priority_floor: Optional[str] = None
    """Minimum priority tier enforced by symptom flags.
    IMMEDIATE | VERY_URGENT | URGENT, or None if no rule fired."""

    priority_basis: str = ""
    """Human-readable explanation of which rules triggered."""

    dvt_chest_combo_detected: bool = False
    """True when both leg DVT signs AND a chest/SOB symptom are present
    (non-negated). Signals priority_mapper to bump the final tier up one level,
    on top of any floor already set by other rules."""


def apply_symptom_flags(entities: list[AnnotatedEntity]) -> SymptomFlagResult:
    """Evaluate Layer 2 symptom escalators against the supplied entity list.

    Only non-negated entities are considered. The entity list is not modified.

    Args:
        entities: Annotated entities from the existing NLP pipeline (read-only).

    Returns:
        SymptomFlagResult describing any symptom-driven escalation.
    """
    # Pre-compute canonical groups for all non-negated entities once
    active = [
        (ent, canonical_group(ent.text))
        for ent in entities
        if not ent.is_negated
    ]

    active_groups = {grp for _, grp in active}

    floor: Optional[str] = None
    reasons: list[str] = []

    # ── Rule 1: Haemoptysis ───────────────────────────────────────────────────
    if "haemoptysis" in active_groups:
        floor = _higher(floor, VERY_URGENT)
        reasons.append("Haemoptysis detected — minimum Very Urgent (10 min).")

    # ── Rule 2: Syncope / collapse ────────────────────────────────────────────
    if "syncope_collapse" in active_groups:
        floor = _higher(floor, VERY_URGENT)
        reasons.append("Syncope/collapse detected — minimum Very Urgent (10 min).")

    # ── Rule 3: Sudden-onset SOB (severity = SEVERE) ──────────────────────────
    for ent, grp in active:
        if grp == "shortness_of_breath" and get_severity(ent) == Severity.SEVERE:
            floor = _higher(floor, URGENT)
            reasons.append(
                f"Sudden-onset shortness of breath detected (\"{ent.text}\") "
                "— minimum Urgent (60 min)."
            )
            break  # one match is sufficient

    # ── Rule 4: Pleuritic chest pain ──────────────────────────────────────────
    for ent, grp in active:
        if grp == "chest_pain" and "pleuritic" in ent.text.lower():
            floor = _higher(floor, URGENT)
            reasons.append(
                "Pleuritic chest pain detected — minimum Urgent (60 min)."
            )
            break

    # ── Rule 5: Leg DVT signs + chest or SOB combo ───────────────────────────
    CHEST_SOB_GROUPS = {"chest_pain", "shortness_of_breath"}
    dvt_combo = (
        "leg_dvt_signs" in active_groups
        and bool(active_groups & CHEST_SOB_GROUPS)
    )
    if dvt_combo:
        reasons.append(
            "Leg DVT signs combined with chest/respiratory symptoms — "
            "priority bumped one tier by priority_mapper."
        )

    triggered = floor is not None or dvt_combo

    return SymptomFlagResult(
        triggered=triggered,
        priority_floor=floor,
        priority_basis=" ".join(reasons),
        dvt_chest_combo_detected=dvt_combo,
    )
