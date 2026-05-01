from __future__ import annotations
import base64
import logging
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pathlib import Path
from clinical_nlp.pipeline import ClinicalRiskOrchestrator
from clinical_nlp.config import settings, supabase_settings
from api.routes import assess, health, examples, decisions

logger = logging.getLogger(__name__)


# ── Demo Basic Auth Middleware ─────────────────────────────────────────────────
# Activated only when the DEMO_PASSWORD environment variable is set.
# Username defaults to "ycdemo" but can be overridden via DEMO_USERNAME.
# Set both variables in Vercel Dashboard → Settings → Environment Variables.
# Leave DEMO_PASSWORD unset for local development (auth is bypassed entirely).
class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        demo_password = os.environ.get("DEMO_PASSWORD", "")
        if not demo_password:
            # Auth disabled — local development or password not yet configured
            return await call_next(request)

        demo_username = os.environ.get("DEMO_USERNAME", "ycdemo")
        authenticated = False

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, _, password = decoded.partition(":")
                username_ok = secrets.compare_digest(
                    username.encode("utf-8"), demo_username.encode("utf-8")
                )
                password_ok = secrets.compare_digest(
                    password.encode("utf-8"), demo_password.encode("utf-8")
                )
                authenticated = username_ok and password_ok
            except Exception:
                pass

        if not authenticated:
            return Response(
                content="Authentication required — please enter the demo credentials.",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="PE Triage Demo"'},
            )

        return await call_next(request)


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

# ── Basic Auth (demo protection) ──────────────────────────────────────────────
app.add_middleware(BasicAuthMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allowed origins come from RISK_ENGINE_ALLOWED_ORIGINS (comma-separated).
# The production frontend URL is always included as a hardcoded fallback so
# CORS works even if the env var is not read correctly on a given cold start.
_origins = list({
    o.strip()
    for o in settings.allowed_origins.split(",")
    if o.strip()
} | {"https://pilot-frontend.vercel.app"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
