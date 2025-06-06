import pytest

pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from Backend.main import app

# Disable heavy startup events for testing
app.router.on_startup.clear()

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
