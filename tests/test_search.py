import pytest
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import schemas, models
from Backend.initial_data import get_initial_data_workflow
from Backend.core.config import settings
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.user_repository import UserRepository

app.router.on_startup.clear()

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


class _TopLevelFunctionSurface:

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_headers():
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_search_endpoint_returns_results():
        headers = get_headers()
        resp = client.get("/api/v1/search", params={"q": "Test"}, headers=headers)
        assert resp.status_code == 200
        assert "results" in resp.json()
        assert len(resp.json()["results"]) > 0

    def test_search_endpoint_returns_recent_results_without_query():
        headers = get_headers()
        resp = client.get("/api/v1/search", headers=headers)
        assert resp.status_code == 200
        assert "results" in resp.json()
        assert len(resp.json()["results"]) > 0

override_get_db = _TopLevelFunctionSurface.override_get_db
get_headers = _TopLevelFunctionSurface.get_headers
test_search_endpoint_returns_results = _TopLevelFunctionSurface.test_search_endpoint_returns_results
test_search_endpoint_returns_recent_results_without_query = _TopLevelFunctionSurface.test_search_endpoint_returns_recent_results_without_query

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

initial_data_workflow = get_initial_data_workflow()

# Prepare sample data
with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)
    admin = UserRepository(db).get_user_by_email(email=settings.FIRST_SUPERUSER_EMAIL)
    ProductRepository(db).create_produto(
        produto=schemas.ProdutoCreate(nome_base="BuscaTest"),
        user_id=admin.id,
    )
    FornecedorRepository(db).create_fornecedor(
        fornecedor=schemas.FornecedorCreate(nome="FornecedorTeste"),
        user_id=admin.id,
    )






