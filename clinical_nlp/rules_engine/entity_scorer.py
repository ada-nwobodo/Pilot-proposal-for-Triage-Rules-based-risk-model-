from __future__ import annotations
from clinical_nlp.phrase_matcher import AnnotatedEntity

# ── Synonym / canonical groups ────────────────────────────────────────────────
# Each group contributes AT MOST 1 point to the total score, regardless of
# how many synonymous phrases appear in the note.  Any entity text not listed
# here maps to its own group (1 point if present and not negated).

SYNONYM_GROUPS: dict[str, set[str]] = {
    # All chest-pain variants (including pleuritic, inspiratory, tightness,
    # pressure, heaviness, discomfort) = 1 feature — regardless of which
    # combination appears in the note, only 1 point is ever awarded.
    "chest_pain": {
        "chest pain",
        "pleuritic chest pain",
        "chest pain worse on inspiration",
        "chest pain worse on breathing in",
        # Tightness variants
        "chest tightness",
        "tight chest",
        "tightness in chest",
        "tightness in the chest",
        # Pressure variants
        "chest pressure",
        "pressure in chest",
        "pressure in the chest",
        # Heaviness variants
        "chest heaviness",
        "heavy chest",
        "heaviness in chest",
        # General discomfort
        "chest discomfort",
    },
    # Shortness of breath and abbreviations = 1 feature
    "shortness_of_breath": {
        "shortness of breath",
        "sob",
        "breathlessness",
    },
    # Haemoptysis and synonyms = 1 feature
    "haemoptysis": {
        "haemoptysis",
        "hemoptysis",
        "coughing up blood",
        "coughing blood",
        "spitting blood",
        "blood in sputum",
    },
    # Collapse, syncope, faint, dizziness = 1 feature
    "syncope_collapse": {
        "collapse",
        "collapsed",
        "syncope",
        "pre-syncope",
        "faint",
        "fainting",
        "dizzy spells",
        "dizziness",
    },
    # Lower limb DVT signs — lateralised and non-lateralised = 1 feature.
    # Wildcard-matched texts (e.g. "R leg pain", "left swollen calf") are
    # caught by the canonical_group() suffix fallback below.
    "leg_dvt_signs": {
        # Swelling
        "leg swelling",
        "calf swelling",
        "right leg swelling",
        "left leg swelling",
        "right calf swelling",
        "left calf swelling",
        "bilateral leg swelling",
        "bilateral calf swelling",
        # Tenderness
        "leg tenderness",
        "calf tenderness",
        "right leg tenderness",
        "left leg tenderness",
        "right calf tenderness",
        "left calf tenderness",
        # Pain
        "leg pain",
        "calf pain",
        "right leg pain",
        "left leg pain",
        "right calf pain",
        "left calf pain",
        # Adjective-first swollen
        "swollen leg",
        "swollen calf",
        "right swollen leg",
        "left swollen leg",
        "right swollen calf",
        "left swollen calf",
        # Hot / warm
        "hot leg",
        "warm leg",
        "hot calf",
        "warm calf",
        "hot swollen leg",
        "hot swollen calf",
        "warm swollen leg",
        "warm swollen calf",
        # Lower limb
        "lower limb swelling",
        "lower limb tenderness",
        "lower limb pain",
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
    # Recent surgery / postoperative — includes named procedures.
    # Wildcard-matched texts (e.g. "recent abdominal surgery") are caught by
    # canonical_group() keyword fallback below.
    "surgery": {
        "recent surgery",
        "post operative",
        "postoperative",
        # Named high-risk procedures
        "cholecystectomy",
        "laparoscopy",
        "laparotomy",
        "appendicectomy",
        "appendectomy",
        "hysterectomy",
        "hip replacement",
        "knee replacement",
        "caesarean section",
        "c - section",
        "c section",
        "craniotomy",
        "thoracotomy",
        "colectomy",
        "nephrectomy",
        "prostatectomy",
    },
    # Long-haul travel — flight, train, and car variants = 1 feature.
    # Wildcard-matched and variant texts are caught by canonical_group() below.
    "long_haul_travel": {
        "recent long haul travel",
        "recent long - haul travel",
        "long haul flight",
        "long - haul flight",
        "recent flight",
        "long haul plane",
        "long - haul plane",
        # Train
        "long haul train",
        "long - haul train",
        "long train journey",
        "long distance train",
        # Car
        "long haul car",
        "long - haul car",
        "long car journey",
        "long distance driving",
        "long distance drive",
    },
    # Immobilisation variants = 1 feature.
    # Recent hospitalisation is included as a proxy for immobility — a patient
    # who was recently admitted is likely to have had a period of reduced
    # mobility.  Any combination of these phrases in one note scores only 1 pt.
    "immobilisation": {
        "recent immobilisation",
        "recent immobilization",
        "prolonged immobility",
        "bed rest",
        # Hospitalisation / admission variants
        "recent hospitalisation",
        "recent hospitalization",
        "recent hospital admission",
        "recent admission",
        "recent inpatient admission",
        "recent inpatient stay",
        "recently hospitalised",
        "recently hospitalized",
        "prolonged hospitalisation",
        "prolonged hospitalization",
    },
    # Oral contraceptive / hormonal = 1 feature
    "ocp": {
        "oral contraceptive",
        "oral contraceptive pill",
        "ocp",
        "combined pill",
        "contraceptive pill",
    },
    # Hormone replacement therapy = 1 feature
    "hrt": {
        "hrt",
        "hormone replacement therapy",
    },
    # Active cancer / palliative cancer / treatment = 1 feature
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
    # Central venous access = 1 feature
    "central_line": {
        "central line",
        "central venous catheter",
        "cvc",
        "picc line",
        "picc",
    },
    # IV drug use = 1 feature
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

    Checks the explicit synonym-group lookup first, then applies keyword
    fallbacks for wildcard-matched entity texts (e.g. "recent abdominal
    surgery", "right leg swelling") that won't appear verbatim in
    SYNONYM_GROUPS.  Falls back to the entity text itself so that any
    entity not covered by a group remains its own 1-point feature.
    """
    text = entity_text.lower()

    # Fast path: exact match in synonym table
    if text in _ENTITY_TO_GROUP:
        return _ENTITY_TO_GROUP[text]

    # Wildcard surgery: "recent [modifier] surgery / operation"
    if text.endswith(("surgery", "operation")):
        return "surgery"

    # Lateralised / qualified lower-limb DVT signs.
    # Covers wildcard-matched texts such as "R leg pain", "left swollen calf",
    # "unilateral leg swelling", "lower limb tenderness" etc.
    for _suffix in (
        "leg swelling",
        "calf swelling",
        "leg tenderness",
        "calf tenderness",
        "leg pain",
        "calf pain",
        "swollen leg",
        "swollen calf",
        "hot leg",
        "warm leg",
        "hot calf",
        "warm calf",
        "hot swollen leg",
        "hot swollen calf",
        "warm swollen leg",
        "warm swollen calf",
        "limb swelling",        # catches "lower limb swelling"
        "limb tenderness",      # catches "lower limb tenderness"
        "limb pain",            # catches "lower limb pain"
    ):
        if text.endswith(_suffix):
            return "leg_dvt_signs"

    # Long-haul travel variants (train, car, plane, hyphenated)
    if any(
        kw in text
        for kw in (
            "long haul",
            "long - haul",
            "long distance",
            "long train",
            "long car",
        )
    ):
        return "long_haul_travel"

    # Default: entity is its own group
    return text


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
