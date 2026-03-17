from __future__ import annotations
from fastapi import APIRouter
from clinical_nlp.adapters import SyntheticDataAdapter
from clinical_nlp.config import settings

router = APIRouter()


@router.get("/examples")
async def get_examples():
    adapter = SyntheticDataAdapter()
    try:
        cases = adapter.load_cases(settings.synthetic_data_path)
        return [c.model_dump() for c in cases[:10]]
    except FileNotFoundError:
        return []
