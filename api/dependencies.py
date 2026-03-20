from __future__ import annotations
from fastapi import Request
from clinical_nlp.pipeline import ClinicalRiskOrchestrator


def get_pipeline(request: Request) -> ClinicalRiskOrchestrator:
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Model not loaded — please retry in a moment")
    return pipeline
