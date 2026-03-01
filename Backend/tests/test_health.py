import pytest
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
# Use absolute import so tests run correctly regardless of working directory
from Backend.main import app

client = TestClient(app)

class _TopLevelFunctionSurface:

    def test_health_endpoint():
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

test_health_endpoint = _TopLevelFunctionSurface.test_health_endpoint
