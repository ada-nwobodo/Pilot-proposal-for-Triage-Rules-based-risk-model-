from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    pipeline_loaded = getattr(request.app.state, "pipeline", None) is not None
    return {"status": "ok", "model_loaded": pipeline_loaded}
