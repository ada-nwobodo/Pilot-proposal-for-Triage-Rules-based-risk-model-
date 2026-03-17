import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_assess_low_risk(client):
    payload = {
        "note_text": "Patient denies chest pain. No shortness of breath. Routine visit.",
        "vitals": {"heart_rate": 72, "systolic_bp": 118, "spo2": 99}
    }
    response = await client.post("/assess", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_level" in data
    assert "reasoning_text" in data


async def test_assess_critical_risk(client):
    payload = {
        "note_text": "Patient is unresponsive. Cardiac arrest suspected.",
        "vitals": {"heart_rate": 0, "systolic_bp": 60, "spo2": 80, "gcs": 3}
    }
    response = await client.post("/assess", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "CRITICAL"


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_missing_note_text_returns_422(client):
    response = await client.post("/assess", json={"vitals": {}})
    assert response.status_code == 422
