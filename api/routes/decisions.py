from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from clinical_nlp.schemas.decision import DecisionPayload
from clinical_nlp.config import supabase_settings

router = APIRouter()

# Lazy Supabase client — created on first use so the app starts fine
# even when SUPABASE_* env vars are not set (e.g. during local testing).
_supabase_client = None


def _get_client():
    global _supabase_client
    if _supabase_client is None:
        if not supabase_settings.url or not supabase_settings.service_role_key:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Supabase is not configured. "
                    "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
                ),
            )
        from supabase import create_client
        _supabase_client = create_client(
            supabase_settings.url,
            supabase_settings.service_role_key,
        )
    return _supabase_client


@router.post("/decisions", status_code=201)
async def save_decision(payload: DecisionPayload) -> dict:
    """
    Persist a completed PE assessment and the clinician's decision to Supabase.

    The NLP analysis (POST /assess) must be run first; this endpoint only
    stores results — it performs no clinical logic of its own.
    """
    row = {
        **payload.model_dump(),
        # Server-side timestamp — never trusted from the browser
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    client = _get_client()
    try:
        response = client.table("assessments").insert(row).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Database write failed: {exc}",
        )

    saved_id = response.data[0].get("id") if response.data else None
    return {"status": "saved", "id": saved_id}
