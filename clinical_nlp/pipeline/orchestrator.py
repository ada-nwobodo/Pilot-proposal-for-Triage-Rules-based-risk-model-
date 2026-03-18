from __future__ import annotations
from spacy.language import Language
from clinical_nlp.config import Settings
from clinical_nlp.preprocessing.text_cleaner import TextCleaner
from clinical_nlp.ner.entity_ruler import build_spacy_pipeline
from clinical_nlp.phrase_matcher import detect_negation, annotate_severity
from clinical_nlp.vitals.scorer import score_vitals
from clinical_nlp.rules_engine import assess
from clinical_nlp.schemas.input import ClinicalInput
from clinical_nlp.schemas.output import RiskAssessment


class ClinicalRiskOrchestrator:
    """
    Wires all pipeline stages together.
    Instantiate once at startup; reuse for all requests.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.cleaner = TextCleaner()
        self.nlp: Language = build_spacy_pipeline(self.settings.spacy_model)

    def run(self, clinical_input: ClinicalInput) -> RiskAssessment:
        clean_text = self.cleaner.clean(clinical_input.note_text)
        doc = self.nlp(clean_text)

        entities = detect_negation(
            doc,
            pre_window=self.settings.negation_pre_window,
            post_window=self.settings.negation_post_window,
        )
        entities = annotate_severity(entities, doc, window=self.settings.severity_window)

        vitals_score = score_vitals(clinical_input.vitals)

        return assess(
            entities=entities,
            vitals_score=vitals_score,
            patient_id=clinical_input.patient_id,
        )
