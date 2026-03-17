from __future__ import annotations
import spacy
from spacy.language import Language
from pathlib import Path

# Inline patterns — no external files required
SYMPTOM_PATTERNS = [
    {"label": "SYMPTOM", "pattern": [{"LOWER": "chest"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "chest"}, {"LOWER": "tightness"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "shortness"}, {"LOWER": "of"}, {"LOWER": "breath"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "dyspnea"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "difficulty"}, {"LOWER": "breathing"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "diaphoresis"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "diaphoretic"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "sweating"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "palpitations"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "syncope"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "near"}, {"LOWER": "syncope"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "loss"}, {"LOWER": "of"}, {"LOWER": "consciousness"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "altered"}, {"LOWER": "consciousness"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "confusion"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "altered"}, {"LOWER": "mental"}, {"LOWER": "status"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "fever"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "febrile"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "hypotension"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "tachycardia"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "bradycardia"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "tachypnea"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "nausea"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "vomiting"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "nausea"}, {"LOWER": "and"}, {"LOWER": "vomiting"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "headache"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "dizziness"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "lightheadedness"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "fatigue"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "weakness"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "leg"}, {"LOWER": "swelling"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "edema"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "peripheral"}, {"LOWER": "edema"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "cough"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "hemoptysis"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "pleuritic"}, {"LOWER": "chest"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "unresponsive"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "abdominal"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "back"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "jaw"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "arm"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "radiating"}, {"LOWER": "pain"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "rigors"}]},
    {"label": "SYMPTOM", "pattern": [{"LOWER": "chills"}]},
]

DIAGNOSIS_PATTERNS = [
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "myocardial"}, {"LOWER": "infarction"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "mi"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "stemi"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "nstemi"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "acs"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "acute"}, {"LOWER": "coronary"}, {"LOWER": "syndrome"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "sepsis"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "septic"}, {"LOWER": "shock"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "pneumonia"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "pulmonary"}, {"LOWER": "embolism"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "pe"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "dvt"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "deep"}, {"LOWER": "vein"}, {"LOWER": "thrombosis"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "stroke"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "anaphylaxis"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "anaphylactic"}, {"LOWER": "shock"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "cardiac"}, {"LOWER": "arrest"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "respiratory"}, {"LOWER": "failure"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "heart"}, {"LOWER": "failure"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "chf"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "copd"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "asthma"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "hypertension"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "diabetes"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "diabetic"}, {"LOWER": "ketoacidosis"}]},
    {"label": "DIAGNOSIS", "pattern": [{"LOWER": "dka"}]},
]

SEVERITY_PATTERNS = [
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "severe"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "severe"}, {"LOWER": "acute"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "moderate"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "mild"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "worsening"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "progressive"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "acute"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "chronic"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "sudden"}, {"LOWER": "onset"}]},
    {"label": "SEVERITY_MODIFIER", "pattern": [{"LOWER": "sudden"}]},
]

ALL_PATTERNS = SYMPTOM_PATTERNS + DIAGNOSIS_PATTERNS + SEVERITY_PATTERNS


def build_spacy_pipeline(model_name: str = "en_core_web_sm") -> Language:
    nlp = spacy.load(model_name, exclude=["ner"])
    ruler = nlp.add_pipe("entity_ruler", before="senter" if "senter" in nlp.pipe_names else None)
    ruler.add_patterns(ALL_PATTERNS)
    return nlp
