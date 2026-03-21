from __future__ import annotations
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
import httpx
from clinical_nlp.schemas.decision import DecisionPayload
from clinical_nlp.config import supabase_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/decisions", status_code=201)
async def save_decision(payload: DecisionPayload) -> dict:
    """
    Persist a completed PE assessment and the clinician's decision to Supabase.
    Calls the Supabase REST API directly via httpx — no supabase-py package needed.
    SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are read from backend env vars only;
    the service role key is never returned to the frontend.
    """
    if not supabase_settings.url or not supabase_settings.service_role_key:
        logger.error(
            "Supabase env vars missing: url=%r service_role_key set=%s",
            supabase_settings.url,
            bool(supabase_settings.service_role_key),
        )
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )

    row = {
        **payload.model_dump(),
        # Timestamp is set server-side — never trusted from the browser.
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    rest_url = f"{supabase_settings.url.rstrip('/')}/rest/v1/assessments"
    headers = {
        "apikey": supabase_settings.service_role_key,
        "Authorization": f"Bearer {supabase_settings.service_role_key}",
        "Content-Type": "application/json",
        # Return the inserted row so we can extract the generated id.
        "Prefer": "return=representation",
    }

    logger.info("POST %s", rest_url)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(rest_url, json=row, headers=headers)
        except Exception as exc:
            logger.error("Network error reaching Supabase: %s", exc)
            raise HTTPException(status_code=502, detail=f"Database write failed: {exc}")

    logger.info("Supabase responded: HTTP %s", resp.status_code)
    if not resp.is_success:
        logger.error("Supabase insert error body: %s", resp.text)
        raise HTTPException(
            status_code=502,
            detail=f"Database write failed: {resp.status_code} {resp.text}",
        )

    data = resp.json()
    saved_id = data[0].get("id") if isinstance(data, list) and data else None
    logger.info("Row saved, id=%s", saved_id)
    return {"status": "saved", "id": saved_id}
