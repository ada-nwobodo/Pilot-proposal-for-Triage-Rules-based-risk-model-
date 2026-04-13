"""Chest pain differential safety screen.

Fires only when chest pain is detected in the triage note AND the PE risk
score is LOW. In that circumstance, even though PE looks unlikely, other
immediately life-threatening causes of chest pain must be screened for before
the presentation can be characterised as truly low risk.

The screen does NOT attempt to diagnose any of the differentials. It flags the
presence of red-flag keyword patterns and adjusts the priority floor and
recommended next steps accordingly.

Conditions screened:
  - Myocardial infarction / ACS
  - Aortic dissection
  - Tension pneumothorax
  - Acute pancreatitis
  - Peptic ulcer disease / perforation
  - Oesophageal rupture (Boerhaave syndrome)

If the screen does not trigger (PE score not LOW, or no chest pain present),
the result carries screen_triggered=False and all other fields are empty /
default — the existing pipeline output is unchanged.

If red flags are detected the priority floor is URGENT and a clinician review
note is appended to next steps. If no red flags are found the floor is
STANDARD with the full cardiac investigation set — chest pain is never
downgraded to NON_URGENT regardless of PE score.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from clinical_nlp.schemas.output import RiskLevel, EntityContribution
from clinical_nlp.rules_engine.entity_scorer import canonical_group

# ── Priority tier constants ───────────────────────────────────────────────────
URGENT   = "URGENT"    # 60 min  — YELLOW
STANDARD = "STANDARD"  # 120 min — GREEN

# ── Next steps when screen fires ──────────────────────────────────────────────
# Full cardiac panel — used whether or not red flags are found.
# (Red-flag path appends an additional clinician review item.)
_CARDIAC_PANEL = [
    "ECG",
    "Insert wide bore cannula (pink)",
    "FBC",
    "U&E",
    "LFT",
    "Troponin",
]
_CLINICIAN_REVIEW = (
    "Clinician review required — alternative serious diagnosis not excluded"
)

# ── Red flag keyword groups ───────────────────────────────────────────────────
# Each entry: (differential_label, list_of_keyword_phrases)
# Matching is case-insensitive substring search on the cleaned note text.
_RED_FLAG_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Possible ACS / Myocardial infarction",
        [
            "crushing",
            "heavy chest",
            "tight chest",
            "pressure in chest",
            "chest pressure",
            "radiating to arm",
            "radiating to left arm",
            "radiating to jaw",
            "left arm pain",
            "left arm heaviness",
            "jaw pain",
            "diaphoresis",
            "profuse sweating",
            "sweating with chest",
            "nausea with chest",
        ],
    ),
    (
        "Possible aortic dissection",
        [
            "tearing pain",
            "ripping pain",
            "tearing to back",
            "radiating to back",
            "pain radiating to back",
            "worst ever pain",
            "sudden severe pain",
            "known hypertension",
            "background hypertension",
            "marfan",
        ],
    ),
    (
        "Possible tension pneumothorax",
        [
            "tracheal deviation",
            "absent breath sounds",
            "sudden onset chest",
            "sudden pleuritic",
        ],
    ),
    (
        "Possible acute pancreatitis",
        [
            "epigastric pain",
            "epigastric discomfort",
            "pain radiating to back",
            "radiates to back",
            "radiating to the back",
            "worse lying flat",
            "worse when lying",
            "alcohol history",
            "heavy alcohol",
            "gallstones",
            "known gallstones",
        ],
    ),
    (
        "Possible peptic ulcer / perforation",
        [
            "epigastric",
            "sudden onset abdominal",
            "nsaid",
            "ibuprofen",
            "naproxen",
            "diclofenac",
            "aspirin use",
            "chronic alcohol",
        ],
    ),
    (
        "Possible oesophageal rupture",
        [
            "vomiting followed by pain",
            "pain after vomiting",
            "chest pain after vomiting",
            "severe vomiting then",
            "boerhaave",
        ],
    ),
]


@dataclass
class ChestPainSafetyResult:
    """Output of the chest pain differential safety screen."""

    screen_triggered: bool
    """True only when chest pain is present (non-negated) AND PE risk is LOW."""

    red_flags_detected: list[str] = field(default_factory=list)
    """Labels of differentials for which red-flag keywords were found.
    Empty list if screen did not trigger or no keywords matched."""

    recommended_priority_floor: Optional[str] = None
    """URGENT if red flags found; STANDARD if screen triggered but no flags.
    None if screen did not trigger."""

    next_steps: list[str] = field(default_factory=list)
    """Recommended investigations when screen triggers.
    Empty if screen did not trigger (existing PE next steps are unaffected)."""


def apply_chest_pain_safety(
    note_text: str,
    risk_level: RiskLevel,
    entity_contributions: list[EntityContribution],
) -> ChestPainSafetyResult:
    """Run the chest pain differential safety screen.

    The screen only activates when ALL of the following are true:
      1. PE risk level is LOW.
      2. At least one non-negated chest pain entity is present.

    If the screen does not activate, a result with screen_triggered=False is
    returned immediately and nothing downstream is changed.

    Args:
        note_text:            Cleaned free-text triage note.
        risk_level:           PE risk level from the existing rules engine.
        entity_contributions: Entity list from the existing rules engine.

    Returns:
        ChestPainSafetyResult.
    """
    # ── Gate: only fire for LOW PE risk with chest pain present ──────────────
    if risk_level != RiskLevel.LOW:
        return ChestPainSafetyResult(screen_triggered=False)

    chest_pain_present = any(
        not ec.is_negated and canonical_group(ec.text) == "chest_pain"
        for ec in entity_contributions
    )
    if not chest_pain_present:
        return ChestPainSafetyResult(screen_triggered=False)

    # ── Screen: keyword search across all red-flag groups ────────────────────
    text_lower = note_text.lower()
    detected: list[str] = []

    for label, keywords in _RED_FLAG_GROUPS:
        if any(kw in text_lower for kw in keywords):
            detected.append(label)

    # ── Build result ─────────────────────────────────────────────────────────
    if detected:
        steps = _CARDIAC_PANEL + [_CLINICIAN_REVIEW]
        floor = URGENT
    else:
        # No red flags found — all screened causes appear absent from the note.
        # Still warrant full cardiac workup; never downgrade below STANDARD.
        steps = list(_CARDIAC_PANEL)
        floor = STANDARD

    return ChestPainSafetyResult(
        screen_triggered=True,
        red_flags_detected=detected,
        recommended_priority_floor=floor,
        next_steps=steps,
    )
