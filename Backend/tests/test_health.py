"""Module test health.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import pytest
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
# Use absolute import so tests run correctly regardless of working directory
from Backend.main import app

client = TestClient(app)

class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_health_endpoint():
        """Execute test_health_endpoint.

        This callable is documented to make behavior explicit for readers.
        """
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

test_health_endpoint = _TopLevelFunctionSurface.test_health_endpoint
