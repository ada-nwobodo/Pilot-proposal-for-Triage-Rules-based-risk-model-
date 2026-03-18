import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from clinical_nlp.pipeline import ClinicalRiskOrchestrator


@pytest.fixture(scope="module")
async def client():
    # Lifespan events don't fire via ASGITransport — seed app.state manually.
    app.state.pipeline = ClinicalRiskOrchestrator()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_assess_low_risk(client):
    payload = {
        "note_text": (
            "Patient denies chest pain. No shortness of breath. "
            "No haemoptysis. Routine visit."
        ),
        "vitals": {"heart_rate": 72, "systolic_bp": 118, "spo2": 99},
    }
    response = await client.post("/assess", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "LOW"
    assert data["suggested_diagnosis"] is None
    assert data["next_steps"] == []
    assert "Not suggestive of PE" in data["reasoning_text"]


async def test_acceptance_criterion_note(client):
    """The exact acceptance criterion note must detect all three features."""
    payload = {
        "note_text": (
            "Pt presents with 3 day history of pleuritic chest pain, "
            "shortness of breath and haemoptysis."
        ),
    }
    response = await client.post("/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    active_texts = {
        c["text"].lower()
        for c in data["entity_contributions"]
        if not c["is_negated"]
    }
    assert "pleuritic chest pain" in active_texts
    assert "shortness of breath" in active_texts
    assert "haemoptysis" in active_texts

    assert data["risk_level"] != "LOW"
    assert data["suggested_diagnosis"] is not None
    assert "Pulmonary Embolism" in data["suggested_diagnosis"]

    required = {"ECG", "Insert wide bore cannula (pink)", "FBC", "U&E", "Clotting", "D-dimer"}
    assert required.issubset(set(data["next_steps"]))


async def test_pe_positive_has_next_steps(client):
    payload = {
        "note_text": "Sudden onset pleuritic chest pain and haemoptysis. Previous DVT.",
        "vitals": {"heart_rate": 115, "spo2": 91},
    }
    response = await client.post("/assess", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] in ("MEDIUM", "HIGH", "CRITICAL")
    required = {"ECG", "Insert wide bore cannula (pink)", "FBC", "U&E", "Clotting", "D-dimer"}
    assert required.issubset(set(data["next_steps"]))


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_missing_note_text_returns_422(client):
    response = await client.post("/assess", json={"vitals": {}})
    assert response.status_code == 422
