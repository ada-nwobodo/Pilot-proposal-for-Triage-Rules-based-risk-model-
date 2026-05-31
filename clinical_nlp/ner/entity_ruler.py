from __future__ import annotations
import spacy
from spacy.language import Language

# ── PE-only entity patterns ───────────────────────────────────────────────────
# Two labels are used:
#   PE_SYMPTOM     – presenting symptoms and clinical signs of PE
#   PE_RISK_FACTOR – predisposing risk factors for PE
#
# Wildcard tokens
#   {"OP": "?"}  matches 0 or 1 token — used to capture optional modifiers
#   e.g. "recent surgery" and "recent abdominal surgery" both match the same
#   pattern; "leg swelling" and "right leg swelling" likewise.
#
#   Where the wildcard appears as the FIRST token in a pattern it MUST carry
#   a NOT_IN constraint (_LAT_NOT_IN below) so that negation words such as
#   "no" and "nil" are never swallowed into the entity span.  Without this,
#   "no leg swelling" matches as the single entity [no leg swelling], leaving
#   nothing before the span for the negation detector to act on.
#
# Synonym deduplication
#   entity_scorer.SYNONYM_GROUPS + canonical_group() ensure that different
#   surface forms of the same clinical feature count as only 1 point.

# Negation words that must never be captured as the optional laterality prefix
# in lower-limb patterns.  Mirrors PRE_NEGATION_TRIGGERS in negation.py.
_LAT_NOT_IN: list[str] = [
    "no", "not", "nil", "none", "without",
    "denies", "deny", "denying",
    "neg", "never",
    "absent", "negative", "free", "unlikely",
    "absence",
]

PE_SYMPTOM_PATTERNS = [
    # ── Pleuritic chest pain and variants ────────────────────────────────────
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "pleuritic"}, {"LOWER": "chest"}, {"LOWER": "pain"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "pain"}, {"LOWER": "worse"},
        {"LOWER": "on"}, {"LOWER": "inspiration"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "pain"}, {"LOWER": "worse"},
        {"LOWER": "on"}, {"LOWER": "breathing"}, {"LOWER": "in"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "pain"}]},

    # ── Chest tightness, pressure, heaviness, discomfort ─────────────────────
    # Treated as variants of chest pain — grouped under "chest_pain" canonical
    # group in entity_scorer.py so they never double-count alongside chest pain.
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "tightness"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "tight"}, {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "tightness"}, {"LOWER": "in"}, {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "tightness"}, {"LOWER": "in"}, {"LOWER": "the"},
        {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "pressure"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "pressure"}, {"LOWER": "in"}, {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "pressure"}, {"LOWER": "in"}, {"LOWER": "the"},
        {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "heaviness"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "heavy"}, {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "heaviness"}, {"LOWER": "in"}, {"LOWER": "chest"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "chest"}, {"LOWER": "discomfort"}]},

    # ── Shortness of breath ───────────────────────────────────────────────────
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "shortness"}, {"LOWER": "of"}, {"LOWER": "breath"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "sob"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "breathlessness"}]},

    # ── Haemoptysis and synonyms ──────────────────────────────────────────────
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "haemoptysis"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "hemoptysis"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "coughing"}, {"LOWER": "up"}, {"LOWER": "blood"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "coughing"}, {"LOWER": "blood"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "blood"}, {"LOWER": "in"}, {"LOWER": "sputum"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "spitting"}, {"LOWER": "blood"}]},

    # ── Collapse / syncope ────────────────────────────────────────────────────
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "collapse"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "collapsed"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "syncope"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "pre-syncope"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "faint"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "fainting"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "dizzy"}, {"LOWER": "spells"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "dizziness"}]},

    # ── Lower limb DVT signs — optional lateral prefix (right/left/bilateral/R/L)
    # The wildcard carries _LAT_NOT_IN so negation words ("no", "nil" etc.)
    # are never swallowed into the span — they remain in the pre-window where
    # the negation detector can act on them.
    # canonical_group() maps any text ending in a leg-sign suffix to the
    # "leg_dvt_signs" group so all variants share 1 point.
    #
    # Swelling and tenderness
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "calf"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "leg"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "calf"}, {"LOWER": "tenderness"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "leg"}, {"LOWER": "tenderness"}]},

    # Pain — leg pain and calf pain are common clinical descriptions of DVT
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "leg"}, {"LOWER": "pain"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "calf"}, {"LOWER": "pain"}]},

    # Adjective-first: "swollen leg", "swollen calf", "left swollen calf"
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "swollen"}, {"LOWER": "leg"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "swollen"}, {"LOWER": "calf"}]},

    # Hot / warm leg or calf — classic DVT inflammatory descriptors
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "hot"}, {"LOWER": "leg"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "warm"}, {"LOWER": "leg"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "hot"}, {"LOWER": "calf"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?", "LOWER": {"NOT_IN": _LAT_NOT_IN}},
        {"LOWER": "warm"}, {"LOWER": "calf"}]},
    # Combined: "hot swollen leg / calf", "warm swollen leg / calf"
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "hot"}, {"LOWER": "swollen"}, {"LOWER": "leg"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "hot"}, {"LOWER": "swollen"}, {"LOWER": "calf"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "warm"}, {"LOWER": "swollen"}, {"LOWER": "leg"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "warm"}, {"LOWER": "swollen"}, {"LOWER": "calf"}]},

    # Lower limb — two-token prefix means the single wildcard can't handle it
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "lower"}, {"LOWER": "limb"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "lower"}, {"LOWER": "limb"}, {"LOWER": "tenderness"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "lower"}, {"LOWER": "limb"}, {"LOWER": "pain"}]},
]

PE_RISK_FACTOR_PATTERNS = [
    # ── Previous DVT / PE (personal history) ─────────────────────────────────
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "pulmonary"}, {"LOWER": "embolism"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "deep"}, {"LOWER": "vein"},
        {"LOWER": "thrombosis"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "history"}, {"LOWER": "of"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "history"}, {"LOWER": "of"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "history"}, {"LOWER": "of"}, {"LOWER": "vte"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prior"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prior"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prior"}, {"LOWER": "vte"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "vte"}]},

    # ── Temporal date-referenced DVT / PE / VTE ───────────────────────────────
    # Handles: "DVT in 1994", "PE in 2010", "VTE in 2005", etc.
    # LIKE_NUM matches any number-like token (years, digits) without
    # needing to hardcode every possible year.
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "dvt"}, {"LOWER": "in"}, {"LIKE_NUM": True}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "pe"}, {"LOWER": "in"}, {"LIKE_NUM": True}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "vte"}, {"LOWER": "in"}, {"LIKE_NUM": True}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "deep"}, {"LOWER": "vein"}, {"LOWER": "thrombosis"},
        {"LOWER": "in"}, {"LIKE_NUM": True}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "pulmonary"}, {"LOWER": "embolism"},
        {"LOWER": "in"}, {"LIKE_NUM": True}]},

    # Handles: "DVT 5 years ago", "PE 2 years ago", "DVT 1 year ago"
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "dvt"}, {"LIKE_NUM": True}, {"LOWER": "years"}, {"LOWER": "ago"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "dvt"}, {"LIKE_NUM": True}, {"LOWER": "year"}, {"LOWER": "ago"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "pe"}, {"LIKE_NUM": True}, {"LOWER": "years"}, {"LOWER": "ago"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "pe"}, {"LIKE_NUM": True}, {"LOWER": "year"}, {"LOWER": "ago"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "vte"}, {"LIKE_NUM": True}, {"LOWER": "years"}, {"LOWER": "ago"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "vte"}, {"LIKE_NUM": True}, {"LOWER": "year"}, {"LOWER": "ago"}]},

    # Handles: "DVT last year", "PE last year"
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "dvt"}, {"LOWER": "last"}, {"LOWER": "year"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "pe"}, {"LOWER": "last"}, {"LOWER": "year"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "vte"}, {"LOWER": "last"}, {"LOWER": "year"}]},

    # ── Alternative history prefixes ──────────────────────────────────────────
    # "past DVT / PE / VTE"
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "vte"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "deep"}, {"LOWER": "vein"},
        {"LOWER": "thrombosis"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "pulmonary"}, {"LOWER": "embolism"}]},

    # "known DVT / PE / VTE" and "known history of ..."
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "vte"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "history"}, {"LOWER": "of"},
        {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "history"}, {"LOWER": "of"},
        {"LOWER": "pe"}]},

    # "hx DVT / PE / VTE" and "hx of DVT / PE / VTE"
    # (clinical shorthand for "history of")
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "of"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "of"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "vte"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "of"}, {"LOWER": "vte"}]},

    # "h/o DVT / PE / VTE" — spaCy tokenises "h/o" as ["h", "/", "o"]
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "h"}, {"LOWER": "/"}, {"LOWER": "o"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "h"}, {"LOWER": "/"}, {"LOWER": "o"}, {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "h"}, {"LOWER": "/"}, {"LOWER": "o"}, {"LOWER": "vte"}]},

    # ── Family history of DVT / PE ────────────────────────────────────────────
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "family"}, {"LOWER": "history"}, {"LOWER": "of"},
        {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "family"}, {"LOWER": "history"}, {"LOWER": "of"},
        {"LOWER": "pe"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "family"}, {"LOWER": "history"}, {"LOWER": "of"},
        {"LOWER": "pulmonary"}, {"LOWER": "embolism"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "family"}, {"LOWER": "history"}, {"LOWER": "of"},
        {"LOWER": "deep"}, {"LOWER": "vein"}, {"LOWER": "thrombosis"}]},

    # ── Surgery / postoperative ───────────────────────────────────────────────
    # Wildcard: {"OP": "?"} allows 0-2 modifier tokens between "recent" and
    # "surgery"/"operation".  Matches: "recent surgery", "recent abdominal
    # surgery", "recent open heart surgery", etc.
    # canonical_group() maps any text ending with "surgery" or "operation"
    # to the "surgery" group so they never double-count.
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"OP": "?"}, {"OP": "?"}, {"LOWER": "surgery"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"OP": "?"}, {"OP": "?"}, {"LOWER": "operation"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "post"}, {"LOWER": "operative"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "postoperative"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "immobilisation"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "immobilization"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prolonged"}, {"LOWER": "immobility"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "bed"}, {"LOWER": "rest"}]},

    # ── Recent hospitalisation / admission (proxy for immobility) ─────────────
    # Grouped under "immobilisation" canonical group in entity_scorer.py
    # so they never double-count alongside bed rest or immobilisation.
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "hospitalisation"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "hospitalization"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "hospital"}, {"LOWER": "admission"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "admission"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "inpatient"}, {"LOWER": "admission"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "inpatient"}, {"LOWER": "stay"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recently"}, {"LOWER": "hospitalised"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recently"}, {"LOWER": "hospitalized"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prolonged"}, {"LOWER": "hospitalisation"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prolonged"}, {"LOWER": "hospitalization"}]},

    # Named high-PE-risk procedures (the word "surgery" may not appear)
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "cholecystectomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "laparoscopy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "laparotomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "appendicectomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "appendectomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "hysterectomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hip"}, {"LOWER": "replacement"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "knee"}, {"LOWER": "replacement"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "caesarean"}, {"LOWER": "section"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "c"}, {"LOWER": "-"}, {"LOWER": "section"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "c"}, {"LOWER": "section"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "craniotomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "thoracotomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "colectomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "nephrectomy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "prostatectomy"}]},

    # ── Long-haul travel — flight, train, car ─────────────────────────────────
    # Flight (existing variants retained; new plane/flight variants added)
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "long"}, {"LOWER": "haul"},
        {"LOWER": "travel"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "long"}, {"LOWER": "-"},
        {"LOWER": "haul"}, {"LOWER": "travel"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "haul"}, {"LOWER": "flight"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "-"}, {"LOWER": "haul"},
        {"LOWER": "flight"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "flight"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "haul"}, {"LOWER": "plane"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "-"}, {"LOWER": "haul"},
        {"LOWER": "plane"}]},
    # Train
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "haul"}, {"LOWER": "train"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "-"}, {"LOWER": "haul"},
        {"LOWER": "train"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "train"}, {"LOWER": "journey"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "distance"}, {"LOWER": "train"}]},
    # Car
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "haul"}, {"LOWER": "car"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "-"}, {"LOWER": "haul"},
        {"LOWER": "car"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "car"}, {"LOWER": "journey"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "distance"}, {"LOWER": "driving"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "long"}, {"LOWER": "distance"}, {"LOWER": "drive"}]},

    # ── Oral contraceptive / hormonal ─────────────────────────────────────────
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "oral"}, {"LOWER": "contraceptive"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "oral"}, {"LOWER": "contraceptive"}, {"LOWER": "pill"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "ocp"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "combined"}, {"LOWER": "pill"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "contraceptive"}, {"LOWER": "pill"}]},

    # ── Hormone replacement therapy ───────────────────────────────────────────
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "hrt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hormone"}, {"LOWER": "replacement"}, {"LOWER": "therapy"}]},

    # ── Cancer / malignancy ───────────────────────────────────────────────────
    # Standalone terms — negation detector handles "no cancer", "no malignancy"
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "carcinoma"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "lymphoma"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "leukaemia"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "leukemia"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "myeloma"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "sarcoma"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "melanoma"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "metastases"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "metastasis"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "metastatic"}, {"OP": "?"}, {"OP": "?"}]},

    # Active / on treatment (existing patterns retained)
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "cancer"}, {"LOWER": "on"}, {"LOWER": "active"},
        {"LOWER": "treatment"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "active"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "active"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "cancer"}, {"LOWER": "with"}, {"LOWER": "palliation"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "palliative"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "palliative"}, {"LOWER": "treatment"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "chemotherapy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "radiotherapy"}]},

    # History prefixes — "history of cancer", "previous malignancy", etc.
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "history"}, {"LOWER": "of"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "history"}, {"LOWER": "of"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "previous"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "past"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "known"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "background"}, {"LOWER": "of"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "background"}, {"LOWER": "of"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "of"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "hx"}, {"LOWER": "of"}, {"LOWER": "malignancy"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "h"}, {"LOWER": "/"}, {"LOWER": "o"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "h"}, {"LOWER": "/"}, {"LOWER": "o"}, {"LOWER": "malignancy"}]},

    # Named cancer types — cover common presentations without requiring a prefix
    # (e.g. "breast cancer", "lung cancer", "prostate cancer")
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "breast"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "lung"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "bowel"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "colorectal"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "colon"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prostate"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "ovarian"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "cervical"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "pancreatic"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "bladder"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "renal"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "kidney"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "thyroid"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "uterine"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "endometrial"}, {"LOWER": "cancer"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "skin"}, {"LOWER": "cancer"}]},

    # ── Central venous access ─────────────────────────────────────────────────
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "central"}, {"LOWER": "line"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "central"}, {"LOWER": "venous"}, {"LOWER": "catheter"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "cvc"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "picc"}, {"LOWER": "line"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "picc"}]},

    # ── IV drug use ───────────────────────────────────────────────────────────
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "iv"}, {"LOWER": "drug"}, {"LOWER": "use"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "intravenous"}, {"LOWER": "drug"}, {"LOWER": "use"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "ivdu"}]},
]

ALL_PATTERNS = PE_SYMPTOM_PATTERNS + PE_RISK_FACTOR_PATTERNS


def build_spacy_pipeline(model_name: str = "en_core_web_sm") -> Language:
    import sys, os, importlib, glob

    # On Vercel/Lambda, pip-installed packages live at LAMBDA_TASK_ROOT
    # (/var/task by default). Insert it explicitly so importlib can find the
    # model package even when the runtime sys.path doesn't include it yet.
    _task_root = os.environ.get("LAMBDA_TASK_ROOT", "/var/task")
    if _task_root not in sys.path:
        sys.path.insert(0, _task_root)

    _module = model_name.replace("-", "_")
    nlp = None

    # Strategy 1: direct Python package import (fastest, most reliable)
    try:
        _mod = importlib.import_module(_module)
        nlp = _mod.load(exclude=["ner"])
    except Exception:
        pass

    # Strategy 2: spaCy registry lookup (works in standard pip installs)
    if nlp is None:
        try:
            nlp = spacy.load(model_name, exclude=["ner"])
        except Exception:
            pass

    # Strategy 3: load model data from its on-disk path directly.
    # The wheel installs: {task_root}/{module}/{module}-{version}/
    # e.g. /var/task/en_core_web_sm/en_core_web_sm-3.8.0/
    if nlp is None:
        _candidates = glob.glob(
            os.path.join(_task_root, _module, f"{_module}-*")
        )
        for _path in _candidates:
            if os.path.isdir(_path):
                try:
                    nlp = spacy.load(_path, exclude=["ner"])
                    break
                except Exception:
                    pass

    # Strategy 4: blank English pipeline — always available, no download needed.
    # Our entity extraction is fully rule-based so this works correctly.
    # A sentencizer is added so ent.sent is available for negation detection.
    if nlp is None:
        import logging
        logging.getLogger(__name__).warning(
            "Could not load '%s' — falling back to spacy.blank('en') + "
            "sentencizer. Entity extraction will work correctly; statistical "
            "NLP features (POS tags, dependency parse) are unavailable.",
            model_name,
        )
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")

    ruler = nlp.add_pipe(
        "entity_ruler",
        before="senter" if "senter" in nlp.pipe_names else None,
    )
    ruler.add_patterns(ALL_PATTERNS)
    return nlp
