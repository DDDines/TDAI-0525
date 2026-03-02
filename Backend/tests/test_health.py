"""Module test health.

Contains backend logic related to test health and documents its role in the OOP architecture.
"""

import pytest
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
# Use absolute import so tests run correctly regardless of working directory
from Backend.main import app

client = TestClient(app)

class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_health_endpoint():
        """Run test health endpoint in this workflow."""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

test_health_endpoint = _TopLevelFunctionSurface.test_health_endpoint
