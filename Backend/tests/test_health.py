from fastapi.testclient import TestClient
# Use absolute import so tests run correctly regardless of working directory
from Backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
