import pytest
import spacy
from clinical_nlp.ner.entity_ruler import build_spacy_pipeline
from clinical_nlp.phrase_matcher.negation import detect_negation


@pytest.fixture(scope="module")
def nlp():
    return build_spacy_pipeline()


NEGATION_CASES = [
    ("Patient denies chest pain.", True),
    ("No shortness of breath reported.", True),
    ("Patient without fever.", True),
    ("No evidence of sepsis.", True),
    ("Ruled out myocardial infarction.", True),
    ("Patient has chest pain.", False),
    ("Chest pain present and worsening.", False),
    ("Patient presents with fever and tachycardia.", False),
    # "no change in chest pain" — pseudo-negation should not negate the entity
    # chest pain is still present, just unchanged
    ("No change in chest pain severity.", False),
]


@pytest.mark.parametrize("text,expected_negated", NEGATION_CASES)
def test_negation_detection(nlp, text, expected_negated):
    doc = nlp(text)
    entities = detect_negation(doc)
    if entities:
        # Check primary entity negation
        assert entities[0].is_negated == expected_negated, (
            f"Expected is_negated={expected_negated} for '{text}', "
            f"got {entities[0].is_negated} (entity: '{entities[0].text}')"
        )
