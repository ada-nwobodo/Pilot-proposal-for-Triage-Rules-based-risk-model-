from __future__ import annotations
from spacy.tokens import Doc
from clinical_nlp.schemas.output import Severity
from .negation import AnnotatedEntity

SEVERITY_MAP: dict[str, Severity] = {
    "severe": Severity.SEVERE,
    "severe acute": Severity.SEVERE,
    "worsening": Severity.SEVERE,
    "progressive": Severity.SEVERE,
    "sudden onset": Severity.SEVERE,
    "sudden": Severity.SEVERE,
    "acute": Severity.MODERATE,
    "moderate": Severity.MODERATE,
    "mild": Severity.MILD,
    "chronic": Severity.MILD,
}

SEVERITY_ORDER = {
    Severity.UNKNOWN: 0,
    Severity.MILD: 1,
    Severity.MODERATE: 2,
    Severity.SEVERE: 3,
}


def annotate_severity(
    entities: list[AnnotatedEntity],
    doc: Doc,
    window: int = 3,
) -> list[AnnotatedEntity]:
    """Link severity modifiers to each entity via a left-context window."""
    for ent in entities:
        best = Severity.UNKNOWN
        look_back = max(0, ent.start - window)
        context_tokens = [doc[i] for i in range(look_back, ent.start)]
        context_text = " ".join(t.lower_ for t in context_tokens)

        for phrase, sev in SEVERITY_MAP.items():
            if phrase in context_text:
                if SEVERITY_ORDER[sev] > SEVERITY_ORDER[best]:
                    best = sev
                    ent.severity_text = phrase

        # Also check right context (e.g., "pain severe")
        look_ahead = min(len(doc), ent.end + window)
        right_tokens = [doc[i] for i in range(ent.end, look_ahead)]
        right_text = " ".join(t.lower_ for t in right_tokens)
        for phrase, sev in SEVERITY_MAP.items():
            if phrase in right_text:
                if SEVERITY_ORDER[sev] > SEVERITY_ORDER[best]:
                    best = sev
                    ent.severity_text = phrase

        ent._severity = best  # type: ignore[attr-defined]

    return entities


def get_severity(entity: AnnotatedEntity) -> Severity:
    return getattr(entity, "_severity", Severity.UNKNOWN)
