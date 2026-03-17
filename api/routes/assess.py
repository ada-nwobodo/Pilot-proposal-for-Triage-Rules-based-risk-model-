from __future__ import annotations
from fastapi import APIRouter, Depends
from clinical_nlp.schemas.input import ClinicalInput
from clinical_nlp.schemas.output import RiskAssessment
from clinical_nlp.pipeline import ClinicalRiskOrchestrator
from api.dependencies import get_pipeline

router = APIRouter()


@router.post("/assess", response_model=RiskAssessment)
async def assess_risk(
    clinical_input: ClinicalInput,
    pipeline: ClinicalRiskOrchestrator = Depends(get_pipeline),
) -> RiskAssessment:
    return pipeline.run(clinical_input)
