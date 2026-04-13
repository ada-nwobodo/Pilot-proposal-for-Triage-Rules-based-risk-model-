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

# ── New priority layer imports (additive — existing pipeline unchanged) ───────
from clinical_nlp.vitals.escalation_rules import apply_escalation_rules
from clinical_nlp.rules_engine.symptom_flags import apply_symptom_flags
from clinical_nlp.rules_engine.chest_pain_safety import apply_chest_pain_safety
from clinical_nlp.rules_engine.priority_mapper import map_priority


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
        # ── Existing pipeline (unchanged) ─────────────────────────────────────
        clean_text = self.cleaner.clean(clinical_input.note_text)
        doc = self.nlp(clean_text)

        entities = detect_negation(
            doc,
            pre_window=self.settings.negation_pre_window,
            post_window=self.settings.negation_post_window,
        )
        entities = annotate_severity(entities, doc, window=self.settings.severity_window)

        vitals_score = score_vitals(clinical_input.vitals)

        assessment = assess(
            entities=entities,
            vitals_score=vitals_score,
            patient_id=clinical_input.patient_id,
        )

        # ── New priority layers (run after existing pipeline, read-only) ──────
        escalation   = apply_escalation_rules(clinical_input.vitals)
        symptom_flags = apply_symptom_flags(entities)
        chest_safety  = apply_chest_pain_safety(
            note_text=clean_text,
            risk_level=assessment.risk_level,
            entity_contributions=assessment.entity_contributions,
        )
        priority = map_priority(
            risk_level=assessment.risk_level,
            combined_score=assessment.combined_score,
            entity_contributions=assessment.entity_contributions,
            escalation=escalation,
            symptom_flags=symptom_flags,
            chest_pain_safety=chest_safety,
        )

        # ── Populate new output fields on a copy of the assessment ────────────
        # All existing fields are preserved identically; only the new Optional
        # fields added in Schema Change 2 are set here.
        update: dict = {
            "priority_tier":          priority.priority_tier,
            "max_wait_minutes":       priority.max_wait_minutes,
            "priority_colour":        priority.priority_colour,
            "priority_basis":         priority.priority_basis,
            "chest_pain_safety_flags": priority.chest_pain_safety_flags,
            "clarification_required": priority.clarification_required,
            "clarification_question": priority.clarification_question,
        }

        # Apply next_steps override only when chest pain safety screen fired
        if priority.next_steps_override is not None:
            update["next_steps"] = priority.next_steps_override

        return assessment.model_copy(update=update)
