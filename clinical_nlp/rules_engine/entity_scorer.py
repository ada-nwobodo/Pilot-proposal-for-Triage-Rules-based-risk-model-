from __future__ import annotations
from clinical_nlp.phrase_matcher import AnnotatedEntity

# ── Synonym / canonical groups ────────────────────────────────────────────────
# Each group contributes AT MOST 1 point to the total score, regardless of
# how many synonymous phrases appear in the note.  Any entity text not listed
# here maps to its own group (1 point if present and not negated).

SYNONYM_GROUPS: dict[str, set[str]] = {
    # All chest-pain variants (including pleuritic, inspiratory) = 1 feature
    "chest_pain": {
        "chest pain",
        "pleuritic chest pain",
        "chest pain worse on inspiration",
        "chest pain worse on breathing in",
    },
    # Haemoptysis and synonym = 1 feature
    "haemoptysis": {
        "haemoptysis",
        "hemoptysis",
        "coughing up blood",
    },
    # Collapse, faint, and dizziness = 1 syncope/collapse feature
    "syncope_collapse": {
        "collapse",
        "collapsed",
        "faint",
        "fainting",
        "dizzy spells",
        "dizziness",
    },
    # Personal history of DVT
    "previous_dvt": {
        "previous dvt",
        "history of dvt",
        "prior dvt",
        "previous deep vein thrombosis",
    },
    # Personal history of PE
    "previous_pe": {
        "previous pe",
        "history of pe",
        "prior pe",
        "previous pulmonary embolism",
    },
    # Family history of DVT
    "family_hx_dvt": {
        "family history of dvt",
        "family history of deep vein thrombosis",
    },
    # Family history of PE
    "family_hx_pe": {
        "family history of pe",
        "family history of pulmonary embolism",
    },
    # Recent surgery / postoperative
    "surgery": {
        "recent surgery",
        "post operative",
        "postoperative",
    },
    # Long-haul travel (with/without hyphen)
    "long_haul_travel": {
        "recent long haul travel",
        "recent long - haul travel",
        "long haul flight",
        "long - haul flight",
    },
    # Immobilisation variants
    "immobilisation": {
        "recent immobilisation",
        "recent immobilization",
        "prolonged immobility",
        "bed rest",
    },
    # Oral contraceptive / hormonal variants
    "ocp": {
        "oral contraceptive",
        "oral contraceptive pill",
        "ocp",
        "combined pill",
        "contraceptive pill",
    },
    # Active cancer / palliative cancer / treatment variants
    "active_cancer": {
        "cancer on active treatment",
        "active cancer",
        "active malignancy",
        "cancer with palliation",
        "palliative cancer",
        "palliative treatment",
        "chemotherapy",
        "radiotherapy",
    },
    # IV drug use
    "iv_drug_use": {
        "iv drug use",
        "intravenous drug use",
        "ivdu",
    },
}

# Reverse lookup: entity text (lowercase) → canonical group name
_ENTITY_TO_GROUP: dict[str, str] = {
    text: group
    for group, texts in SYNONYM_GROUPS.items()
    for text in texts
}


def canonical_group(entity_text: str) -> str:
    """Return the canonical group name for an entity.

    Falls back to the entity text itself so that any entity not in a
    synonym group is its own 1-point feature.
    """
    return _ENTITY_TO_GROUP.get(entity_text.lower(), entity_text.lower())


def deduplicate_and_score(
    entities: list[AnnotatedEntity],
) -> list[tuple[AnnotatedEntity, int]]:
    """Assign each entity a score of 0 or 1.

    Rules:
      - Negated entities → 0 (not counted).
      - First non-negated entity in a canonical group → 1 (counted).
      - Subsequent entities whose group has already been counted → 0
        (still returned so the UI can show them as duplicates).
    """
    seen_groups: set[str] = set()
    result: list[tuple[AnnotatedEntity, int]] = []

    for ent in entities:
        if ent.is_negated:
            result.append((ent, 0))
            continue

        group = canonical_group(ent.text)
        if group in seen_groups:
            result.append((ent, 0))   # duplicate — visible but not scored
        else:
            seen_groups.add(group)
            result.append((ent, 1))   # first occurrence — scored

    return result
