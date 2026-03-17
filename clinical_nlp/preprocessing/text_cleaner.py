from __future__ import annotations
import re

# Common clinical abbreviation expansions — extend as needed
ABBREVIATION_MAP: dict[str, str] = {
    r"\bc/o\b": "complains of",
    r"\bs/o\b": "shortness of",
    r"\bsob\b": "shortness of breath",
    r"\bdyspnea\b": "dyspnea",
    r"\bcp\b": "chest pain",
    r"\bha\b": "headache",
    r"\bh/o\b": "history of",
    r"\bw/o\b": "without",
    r"\bwbc\b": "white blood cell count",
    r"\bhr\b": "heart rate",
    r"\bsbp\b": "systolic blood pressure",
    r"\bdbp\b": "diastolic blood pressure",
    r"\brr\b": "respiratory rate",
    r"\btemp\b": "temperature",
    r"\bo2\b": "oxygen",
    r"\bsat\b": "saturation",
    r"\bgcs\b": "glasgow coma scale",
    r"\bpt\b": "patient",
    r"\byo\b": "year old",
    r"\bm\b(?=\s+(?:patient|presents|with|who))": "male",
    r"\bf\b(?=\s+(?:patient|presents|with|who))": "female",
}


class TextCleaner:
    def __init__(self) -> None:
        self._compiled = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in ABBREVIATION_MAP.items()
        ]

    def clean(self, text: str) -> str:
        text = self._normalize_whitespace(text)
        text = self._expand_abbreviations(text)
        return text.strip()

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _expand_abbreviations(self, text: str) -> str:
        for pattern, replacement in self._compiled:
            text = pattern.sub(replacement, text)
        return text
