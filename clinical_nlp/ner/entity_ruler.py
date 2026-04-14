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
# Synonym deduplication
#   entity_scorer.SYNONYM_GROUPS + canonical_group() ensure that different
#   surface forms of the same clinical feature count as only 1 point.

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

    # ── Lower limb DVT signs — optional lateral prefix (right/left/bilateral)
    # {"OP": "?"} captures 0 or 1 token so "leg swelling", "right leg swelling"
    # and "left leg swelling" all match.  canonical_group() maps any text ending
    # in a leg-sign suffix to the "leg_dvt_signs" group so they share 1 point.
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?"}, {"LOWER": "calf"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?"}, {"LOWER": "leg"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?"}, {"LOWER": "calf"}, {"LOWER": "tenderness"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"OP": "?"}, {"LOWER": "leg"}, {"LOWER": "tenderness"}]},
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
        {"LOWER": "prior"}, {"LOWER": "dvt"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "prior"}, {"LOWER": "pe"}]},

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

    # ── Active cancer / palliation ────────────────────────────────────────────
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
