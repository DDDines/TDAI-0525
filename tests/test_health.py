import pytest
from fastapi.testclient import TestClient

from Backend.main import app


# Disable heavy startup events for testing
app.router.on_startup.clear()


class _TopLevelFunctionSurface:

    def test_health_check_endpoint():
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

test_health_check_endpoint = _TopLevelFunctionSurface.test_health_check_endpoint


pytest.importorskip("sqlalchemy")

client = TestClient(app)



