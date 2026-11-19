from fastapi.testclient import TestClient

from backend.api.app import app


def test_health_and_analysis_endpoints() -> None:
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    response = client.post("/api/analyze", json={"asset": "TEST", "horizon": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"] == "TEST"
    assert len(payload["quantum"]["forecast"]) == 3
    assert 0 <= payload["extreme_events"]["risk_probability"] <= 1


def test_agent_stream_uses_registered_tools() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/agent/stream",
        json={"message": "run a full synthesis", "asset": "TEST", "horizon": 2},
    )
    assert response.status_code == 200
    assert response.text
