from __future__ import annotations
import logging
import secrets
import string
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
import httpx
from clinical_nlp.schemas.decision import DecisionPayload
from clinical_nlp.schemas.outcome import OutcomePayload
from clinical_nlp.config import supabase_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Study code generation ──────────────────────────────────────────────────────

_CODE_ALPHABET = string.ascii_uppercase + string.digits  # A-Z + 0-9, no ambiguous chars


def generate_study_code() -> str:
    """
    Generate a unique server-side study code, e.g. PE-2025-A3F7K2.

    Format: PE-{YEAR}-{6 random uppercase alphanumeric chars}
    36^6 ≈ 2.1 billion combinations — negligible collision risk for a pilot.
    Uses secrets.choice (cryptographically random) to avoid predictable sequences.
    """
    year   = datetime.now(timezone.utc).year
    suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
    return f"PE-{year}-{suffix}"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _rest_url(table: str) -> str:
    return f"{supabase_settings.url.rstrip('/')}/rest/v1/{table}"


def _headers() -> dict:
    return {
        "apikey": supabase_settings.service_role_key,
        "Authorization": f"Bearer {supabase_settings.service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _require_supabase() -> None:
    """Raise 503 if Supabase env vars are missing."""
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


# ── POST /decisions ────────────────────────────────────────────────────────────

@router.post("/decisions", status_code=201)
async def save_decision(payload: DecisionPayload) -> dict:
    """
    Persist a completed PE assessment and the clinician's decision to Supabase.

    The patient_ref (study code) is always generated server-side and returned
    in the response — any value sent by the client is ignored.  This eliminates
    coordination problems when multiple nurses work concurrently.

    Calls the Supabase REST API directly via httpx — no supabase-py needed.
    """
    _require_supabase()

    # Always generate the study code server-side; never trust the client value.
    study_code = generate_study_code()

    row = {
        **payload.model_dump(exclude_none=True),  # omit null optional fields (e.g. new granular feedback cols)
        "patient_ref": study_code,                # overwrite whatever the client sent
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }

    url = _rest_url("assessments")
    logger.info("POST %s  study_code=%s", url, study_code)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=row, headers=_headers())
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

    data     = resp.json()
    saved_id = data[0].get("id") if isinstance(data, list) and data else None
    logger.info("Row saved, id=%s  study_code=%s", saved_id, study_code)

    # Return the study code so the frontend can display it to the clinician.
    return {"status": "saved", "id": saved_id, "study_code": study_code}


# ── GET /decisions/lookup ──────────────────────────────────────────────────────

@router.get("/decisions/lookup")
async def lookup_assessment(
    patient_ref: str = Query(..., min_length=1, description="Study code, e.g. PE-2025-A3F7K2"),
) -> dict:
    """
    Find the most recent assessment for a given study code.
    Returns a summary suitable for the outcome-recording page.
    Returns 404 if no matching assessment is found.
    """
    _require_supabase()

    url = _rest_url("assessments")
    select_cols = (
        "id,created_at,risk_level,score,decision,decision_reason,"
        "clinician_name,patient_ref,suggested_diagnosis,"
        "outcome,confirming_test,outcome_date,outcome_notes,outcome_recorded_at"
    )
    params = {
        "patient_ref": f"eq.{patient_ref}",
        "order":       "created_at.desc",
        "limit":       "1",
        "select":      select_cols,
    }

    read_headers = {
        "apikey":        supabase_settings.service_role_key,
        "Authorization": f"Bearer {supabase_settings.service_role_key}",
        "Content-Type":  "application/json",
    }

    logger.info("GET %s  patient_ref=%r", url, patient_ref)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params, headers=read_headers)
        except Exception as exc:
            logger.error("Network error reaching Supabase: %s", exc)
            raise HTTPException(status_code=502, detail=f"Database lookup failed: {exc}")

    logger.info("Supabase lookup responded: HTTP %s", resp.status_code)
    if not resp.is_success:
        logger.error("Supabase lookup error body: %s", resp.text)
        raise HTTPException(
            status_code=502,
            detail=f"Database lookup failed: {resp.status_code} {resp.text}",
        )

    rows = resp.json()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No assessment found for study code '{patient_ref}'.",
        )

    return rows[0]


# ── PATCH /decisions/{assessment_id}/outcome ───────────────────────────────────

@router.patch("/decisions/{assessment_id}/outcome", status_code=200)
async def record_outcome(assessment_id: str, payload: OutcomePayload) -> dict:
    """
    Record the clinical outcome for a previously saved assessment.
    Patches the outcome columns on the matching row; outcome_recorded_at is
    set server-side.
    """
    _require_supabase()

    update = {
        **payload.model_dump(exclude_none=False),
        "outcome_recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    update = {k: v for k, v in update.items() if v is not None}

    url    = _rest_url("assessments")
    params = {"id": f"eq.{assessment_id}"}

    logger.info("PATCH %s  id=%r  outcome=%r", url, assessment_id, payload.outcome)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.patch(url, json=update, params=params, headers=_headers())
        except Exception as exc:
            logger.error("Network error reaching Supabase: %s", exc)
            raise HTTPException(status_code=502, detail=f"Database update failed: {exc}")

    logger.info("Supabase patch responded: HTTP %s", resp.status_code)
    if not resp.is_success:
        logger.error("Supabase patch error body: %s", resp.text)
        raise HTTPException(
            status_code=502,
            detail=f"Database update failed: {resp.status_code} {resp.text}",
        )

    data = resp.json()
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No assessment found with id '{assessment_id}'.",
        )

    logger.info("Outcome recorded for id=%s", assessment_id)
    return {"status": "outcome_recorded", "id": assessment_id}
