from __future__ import annotations
from fastapi import Request
from clinical_nlp.pipeline import ClinicalRiskOrchestrator


def get_pipeline(request: Request) -> ClinicalRiskOrchestrator:
    return request.app.state.pipeline
