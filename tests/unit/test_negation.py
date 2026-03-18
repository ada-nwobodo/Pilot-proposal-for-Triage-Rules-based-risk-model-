import pytest
from clinical_nlp.ner.entity_ruler import build_spacy_pipeline
from clinical_nlp.phrase_matcher.negation import detect_negation


@pytest.fixture(scope="module")
def nlp():
    return build_spacy_pipeline()


NEGATION_CASES = [
    # (text, expected_is_negated_for_first_entity)
    ("Patient denies chest pain.", True),
    ("No shortness of breath reported.", True),
    ("Patient without haemoptysis.", True),
    ("No evidence of pleuritic chest pain.", True),
    ("Ruled out previous DVT.", True),
    ("Patient has chest pain.", False),
    ("Pleuritic chest pain present.", False),
    ("Patient presents with shortness of breath.", False),
    # Pseudo-negation: "no change in chest pain" — chest pain is still present
    ("No change in chest pain severity.", False),
]


@pytest.mark.parametrize("text,expected_negated", NEGATION_CASES)
def test_negation_detection(nlp, text, expected_negated):
    doc = nlp(text)
    entities = detect_negation(doc)
    if entities:
        assert entities[0].is_negated == expected_negated, (
            f"Expected is_negated={expected_negated} for '{text}', "
            f"got {entities[0].is_negated} (entity: '{entities[0].text}')"
        )
