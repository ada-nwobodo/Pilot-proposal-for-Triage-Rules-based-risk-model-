from __future__ import annotations
import spacy
from spacy.language import Language

# ── PE-only entity patterns ───────────────────────────────────────────────────
# Two labels are used:
#   PE_SYMPTOM     – presenting symptoms and clinical signs of PE
#   PE_RISK_FACTOR – predisposing risk factors for PE
#
# Synonym handling
#   "haemoptysis" / "hemoptysis" / "coughing up blood"  → same weight
#   "pleuritic chest pain" / "chest pain worse on inspiration" /
#   "chest pain worse on breathing in"                  → same weight

PE_SYMPTOM_PATTERNS = [
    # Pleuritic chest pain and synonyms (all equivalent PE features)
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

    # Shortness of breath
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "shortness"}, {"LOWER": "of"}, {"LOWER": "breath"}]},

    # Haemoptysis and synonyms (all equivalent PE features)
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "haemoptysis"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "hemoptysis"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "coughing"}, {"LOWER": "up"}, {"LOWER": "blood"}]},

    # Collapse / syncope
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "collapse"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "collapsed"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "faint"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "fainting"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "dizzy"}, {"LOWER": "spells"}]},
    {"label": "PE_SYMPTOM", "pattern": [{"LOWER": "dizziness"}]},

    # Lower limb signs (DVT / PE leg features)
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "calf"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "leg"}, {"LOWER": "swelling"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "calf"}, {"LOWER": "tenderness"}]},
    {"label": "PE_SYMPTOM", "pattern": [
        {"LOWER": "leg"}, {"LOWER": "tenderness"}]},
]

PE_RISK_FACTOR_PATTERNS = [
    # Previous DVT / PE (personal history)
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

    # Family history of DVT / PE
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

    # Recent surgery / immobilisation
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "recent"}, {"LOWER": "surgery"}]},
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

    # Long-haul travel (with and without hyphen)
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

    # Oral contraceptive / hormonal
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "oral"}, {"LOWER": "contraceptive"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "oral"}, {"LOWER": "contraceptive"}, {"LOWER": "pill"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "ocp"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "combined"}, {"LOWER": "pill"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "contraceptive"}, {"LOWER": "pill"}]},

    # Active cancer / palliation
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

    # IV drug use
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "iv"}, {"LOWER": "drug"}, {"LOWER": "use"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [
        {"LOWER": "intravenous"}, {"LOWER": "drug"}, {"LOWER": "use"}]},
    {"label": "PE_RISK_FACTOR", "pattern": [{"LOWER": "ivdu"}]},
]

ALL_PATTERNS = PE_SYMPTOM_PATTERNS + PE_RISK_FACTOR_PATTERNS


def build_spacy_pipeline(model_name: str = "en_core_web_sm") -> Language:
    # Try direct module import first — required on Vercel where spaCy is vendored
    # at /var/task/_vendor/spacy/ and cannot find models via spacy.load() discovery.
    # Falls back to spacy.load() for all other environments.
    try:
        import importlib
        _model_module = importlib.import_module(model_name.replace("-", "_"))
        nlp = _model_module.load(exclude=["ner"])
    except (ImportError, ModuleNotFoundError):
        nlp = spacy.load(model_name, exclude=["ner"])
    ruler = nlp.add_pipe(
        "entity_ruler",
        before="senter" if "senter" in nlp.pipe_names else None,
    )
    ruler.add_patterns(ALL_PATTERNS)
    return nlp
