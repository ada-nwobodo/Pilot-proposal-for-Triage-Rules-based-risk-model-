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

    if nlp is None:
        raise RuntimeError(
            f"Could not load spaCy model '{model_name}' via any strategy. "
            f"task_root={_task_root!r}, sys.path[:4]={sys.path[:4]}"
        )

    ruler = nlp.add_pipe(
        "entity_ruler",
        before="senter" if "senter" in nlp.pipe_names else None,
    )
    ruler.add_patterns(ALL_PATTERNS)
    return nlp
