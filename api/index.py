from __future__ import annotations
import base64
import logging
import os
import secrets
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


# ── Demo Basic Auth Middleware ─────────────────────────────────────────────────
# Pure ASGI middleware — more reliable than BaseHTTPMiddleware in serverless.
# Activated only when DEMO_PASSWORD environment variable is set.
# Username defaults to "ycdemo" — override with DEMO_USERNAME env var.
# Set both in Vercel Dashboard → Settings → Environment Variables → Production.
# Leave DEMO_PASSWORD unset for local development (auth bypassed entirely).
class BasicAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only intercept HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        demo_password = os.environ.get("DEMO_PASSWORD", "")
        if not demo_password:
            # Auth disabled — pass straight through
            await self.app(scope, receive, send)
            return

        demo_username = os.environ.get("DEMO_USERNAME", "ycdemo")
        authenticated = False

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth_header = headers.get(b"authorization", b"").decode("utf-8")

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

        if authenticated:
            await self.app(scope, receive, send)
            return

        # Return 401 — browser will show native login dialog
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"www-authenticate", b'Basic realm="PE Triage Demo"'],
                [b"content-type", b"text/plain; charset=utf-8"],
                [b"content-length", b"48"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"Authentication required. Please enter credentials.",
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.pipeline = ClinicalRiskOrchestrator()
        logger.info("Pipeline initialised successfully.")
    except Exception as exc:
        logger.error("Pipeline startup failed: %s", exc, exc_info=True)
        app.state.pipeline = None   # health endpoint will report model_loaded=false
    yield


_fastapi = FastAPI(
    title="Clinical Risk Stratification API",
    description="Rules-based NLP risk engine for clinical triage",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_origins = list({
    o.strip()
    for o in settings.allowed_origins.split(",")
    if o.strip()
} | {"https://pilot-frontend.vercel.app"})

_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
_fastapi.include_router(health.router)
_fastapi.include_router(assess.router)
_fastapi.include_router(examples.router)
_fastapi.include_router(decisions.router)

# ── Frontend static files ─────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if (frontend_path / "static").exists():
    _fastapi.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")


@_fastapi.get("/", include_in_schema=False)
async def serve_frontend():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Clinical Risk Stratification API", "docs": "/docs"}


@_fastapi.get("/config", include_in_schema=False)
async def get_config():
    return {
        "supabase_url":      supabase_settings.url,
        "supabase_anon_key": supabase_settings.anon_key,
    }


# ── Basic Auth wrapper ────────────────────────────────────────────────────────
# Vercel calls whatever variable is named `app` as the ASGI entry point.
# Wrapping _fastapi here means every request — before anything else —
# passes through BasicAuthMiddleware. No middleware registration needed.
app = BasicAuthMiddleware(_fastapi)
