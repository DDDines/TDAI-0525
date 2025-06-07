
import asyncio
import pytest
from fastapi.testclient import TestClient

from Backend.main import health_check, app


# Disable heavy startup events for testing
app.router.on_startup.clear()


def test_health_check_direct():
    result = asyncio.run(health_check())
    assert result == {"status": "ok"}


pytest.importorskip("sqlalchemy")

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

