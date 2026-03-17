from __future__ import annotations
from dataclasses import dataclass, field
from spacy.tokens import Doc, Span
from .context_window import scope_broken

PRE_NEGATION_TRIGGERS = {
    "no", "not", "without", "denies", "deny",
    "absent", "negative", "free", "unlikely",
    "rules", "ruled",  # "ruled out"
    "absence",         # "absence of"
}

POST_NEGATION_TRIGGERS = {
    "absent", "negative", "unlikely",
}

# Multi-token triggers (checked as phrase)
PRE_NEGATION_PHRASES = {
    "no evidence of", "no signs of", "no history of",
    "not present", "not observed", "not detected",
    "ruled out", "no evidence",
}

# These look like negations but aren't targeting the entity
PSEUDO_NEGATION_PHRASES = {
    "no change", "no improvement", "no worsening",
    "no relief", "no response", "not improved",
}


@dataclass
class AnnotatedEntity:
    text: str
    label: str
    start: int          # token index in doc
    end: int            # token index in doc (exclusive)
    is_negated: bool = False
    severity_text: str = ""
    char_start: int = 0
    char_end: int = 0


def detect_negation(doc: Doc, pre_window: int = 5, post_window: int = 3) -> list[AnnotatedEntity]:
    """
    Run negation detection on all entities in doc.
    Returns AnnotatedEntity list with is_negated set.
    """
    entities: list[AnnotatedEntity] = []

    for ent in doc.ents:
        if ent.label_ not in ("SYMPTOM", "DIAGNOSIS"):
            continue

        ae = AnnotatedEntity(
            text=ent.text,
            label=ent.label_,
            start=ent.start,
            end=ent.end,
            char_start=ent.start_char,
            char_end=ent.end_char,
        )

        ae.is_negated = _check_negation(doc, ent, pre_window, post_window)
        entities.append(ae)

    return entities


def _check_negation(doc: Doc, ent: Span, pre_window: int, post_window: int) -> bool:
    sent = ent.sent

    # --- Pre-entity window ---
    look_back_start = max(sent.start, ent.start - pre_window)
    pre_tokens = [doc[i] for i in range(look_back_start, ent.start)]

    # Check phrase triggers in the pre window text
    pre_text = " ".join(t.lower_ for t in pre_tokens)
    if _text_contains_pseudo(pre_text):
        return False

    if _text_contains_negation_phrase(pre_text):
        # Verify scope isn't broken
        if not scope_broken(doc, look_back_start, ent.start):
            return True

    # Check single token triggers
    for i, tok in enumerate(pre_tokens):
        if tok.lower_ in PRE_NEGATION_TRIGGERS:
            tok_idx = look_back_start + i
            if not scope_broken(doc, tok_idx, ent.start):
                return True

    # --- Post-entity window ---
    look_ahead_end = min(sent.end, ent.end + post_window)
    post_tokens = [doc[i] for i in range(ent.end, look_ahead_end)]
    post_text = " ".join(t.lower_ for t in post_tokens)

    if _text_contains_negation_phrase(post_text):
        if not scope_broken(doc, ent.end, look_ahead_end):
            return True

    for i, tok in enumerate(post_tokens):
        if tok.lower_ in POST_NEGATION_TRIGGERS:
            tok_idx = ent.end + i
            if not scope_broken(doc, ent.end, tok_idx):
                return True

    return False


def _text_contains_negation_phrase(text: str) -> bool:
    return any(phrase in text for phrase in PRE_NEGATION_PHRASES)


def _text_contains_pseudo(text: str) -> bool:
    return any(phrase in text for phrase in PSEUDO_NEGATION_PHRASES)
