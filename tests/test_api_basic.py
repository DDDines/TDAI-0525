import pytest
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from Backend.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Bem-vindo" in response.json().get("message", "")


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
