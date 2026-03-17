import pytest
from clinical_nlp.adapters.base import DataAdapter
from clinical_nlp.adapters.synthetic import SyntheticDataAdapter
from clinical_nlp.schemas.input import ClinicalInput


def test_synthetic_adapter_implements_interface():
    adapter = SyntheticDataAdapter()
    assert isinstance(adapter, DataAdapter)


def test_synthetic_adapter_load_cases(tmp_path):
    note_file = tmp_path / "notes.jsonl"
    note_file.write_text(
        '{"patient_id": "T1", "note_text": "Patient has fever.", "vitals": {"heart_rate": 100}}\n'
    )
    adapter = SyntheticDataAdapter()
    cases = adapter.load_cases(str(note_file))
    assert len(cases) == 1
    assert isinstance(cases[0], ClinicalInput)
    assert cases[0].patient_id == "T1"


def test_synthetic_adapter_validate_schema():
    adapter = SyntheticDataAdapter()
    raw = {"patient_id": "T2", "note_text": "Chest pain present."}
    result = adapter.validate_schema(raw)
    assert isinstance(result, ClinicalInput)
    assert result.vitals is None
