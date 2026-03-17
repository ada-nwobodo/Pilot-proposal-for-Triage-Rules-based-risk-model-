from clinical_nlp.preprocessing.text_cleaner import TextCleaner


def test_abbreviation_expansion():
    cleaner = TextCleaner()
    result = cleaner.clean("Patient c/o sob and cp.")
    assert "complains of" in result
    assert "shortness of breath" in result
    assert "chest pain" in result


def test_whitespace_normalization():
    cleaner = TextCleaner()
    result = cleaner.clean("Patient   has   fever\n\n\n\nand cough.")
    assert "  " not in result
    assert result.count("\n") <= 2


def test_clean_returns_stripped():
    cleaner = TextCleaner()
    result = cleaner.clean("   fever   ")
    assert result == result.strip()
