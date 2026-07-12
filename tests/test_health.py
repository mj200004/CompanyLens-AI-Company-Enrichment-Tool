from __future__ import annotations


def test_health_endpoint_returns_200(client):
    response = client.get("/health")

    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["service"] == "companylens"
    assert payload["database"] == "ok"
    assert "time" in payload
