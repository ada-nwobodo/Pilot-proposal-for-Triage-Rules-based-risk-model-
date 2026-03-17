from __future__ import annotations
import json
from pathlib import Path
from typing import Iterator
from clinical_nlp.schemas.input import ClinicalInput, VitalSigns
from .base import DataAdapter


class SyntheticDataAdapter(DataAdapter):
    """Loads synthetic clinical notes from a local JSONL file."""

    def load_cases(self, source: str) -> list[ClinicalInput]:
        return list(self.stream_cases(source))

    def stream_cases(self, source: str) -> Iterator[ClinicalInput]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Synthetic data not found: {source}")
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield self.validate_schema(json.loads(line))

    def validate_schema(self, raw: dict) -> ClinicalInput:
        vitals_raw = raw.get("vitals")
        vitals = VitalSigns(**vitals_raw) if vitals_raw else None
        return ClinicalInput(
            note_text=raw["note_text"],
            vitals=vitals,
            patient_id=raw.get("patient_id"),
            case_label=raw.get("case_label"),
        )
