from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from clinical_nlp.pipeline import ClinicalRiskOrchestrator
from api.routes import assess, health, examples


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline = ClinicalRiskOrchestrator()
    yield
    # cleanup if needed


app = FastAPI(
    title="Clinical Risk Stratification API",
    description="Rules-based NLP risk engine for clinical triage",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(assess.router)
app.include_router(examples.router)

frontend_path = Path(__file__).parent.parent / "frontend"
if (frontend_path / "static").exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Clinical Risk Stratification API", "docs": "/docs"}
