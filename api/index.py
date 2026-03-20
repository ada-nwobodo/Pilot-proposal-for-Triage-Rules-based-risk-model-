from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from clinical_nlp.pipeline import ClinicalRiskOrchestrator
from clinical_nlp.config import settings, supabase_settings
from api.routes import assess, health, examples, decisions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.pipeline = ClinicalRiskOrchestrator()
        logger.info("Pipeline initialised successfully.")
    except Exception as exc:
        logger.error("Pipeline startup failed: %s", exc, exc_info=True)
        app.state.pipeline = None   # health endpoint will report model_loaded=false
    yield


app = FastAPI(
    title="Clinical Risk Stratification API",
    description="Rules-based NLP risk engine for clinical triage",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Origins are controlled by RISK_ENGINE_ALLOWED_ORIGINS (comma-separated).
# Default: localhost only. Set to your deployed frontend URL in production.
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(assess.router)
app.include_router(examples.router)
app.include_router(decisions.router)

# ── Frontend static files ─────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if (frontend_path / "static").exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Clinical Risk Stratification API", "docs": "/docs"}


# ── Runtime config endpoint ────────────────────────────────────────────────────
# Returns only public-safe values (never the service-role key).
# The frontend fetches this once on load to discover its runtime config.
@app.get("/config", include_in_schema=False)
async def get_config():
    return {
        "supabase_url":      supabase_settings.url,
        "supabase_anon_key": supabase_settings.anon_key,
    }
