from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    pipeline_loaded = hasattr(request.app.state, "pipeline")
    return {"status": "ok", "model_loaded": pipeline_loaded}
