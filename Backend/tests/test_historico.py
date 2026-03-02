"""Module test historico.

Contains backend logic related to test historico and documents its role in the OOP architecture.
"""

import os
os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "admin@example.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "password")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "password")
import pytest
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import MainBootstrapWorkflow, app
from Backend.database import Base, get_db
from Backend import schemas
from Backend.initial_data import InitialDataWorkflow

# Disable heavy startup events so tests run faster
app.router.on_startup.clear()

# In-memory SQLite for isolated tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency override

class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def override_get_db():
        """Run override get db in this workflow."""
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_user_headers():
        """Return user headers for this workflow."""
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "user@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_historico_records_product_creation():
        """Run test historico records product creation in this workflow."""
        headers = get_user_headers()
        # create fornecedor
        resp = client.post(
            "/api/v1/fornecedores/",
            json={"nome": "Fornecedor X"},
            headers=headers,
        )
        assert resp.status_code == 201
        fornecedor_id = resp.json()["id"]
    
        # create product referencing fornecedor
        resp = client.post(
            "/api/v1/produtos/",
            json={"nome_base": "Produto Y", "fornecedor_id": fornecedor_id},
            headers=headers,
        )
        assert resp.status_code == 201
        produto_id = resp.json()["id"]
    
        # fetch historico de uso de IA
        resp = client.get("/api/v1/uso-ia/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] >= 1
        assert any(item["produto_id"] == produto_id for item in data["items"])

    def test_historico_records_bulk_import():
        """Run test historico records bulk import in this workflow."""
        headers = get_user_headers()
    
        resp = client.post(
            "/api/v1/fornecedores/",
            json={"nome": "Fornecedor Bulk"},
            headers=headers,
        )
        assert resp.status_code == 201
        fornecedor_id = resp.json()["id"]
    
        resp = client.get("/api/v1/historico/", headers=headers)
        assert resp.status_code == 200
        before_produto = [h for h in resp.json()["items"] if h["entidade"] == "Produto"]
    
        csv_content = "nome,sku\nProd1,S1\nProd2,S2\n"
        files = {"file": ("catalog.csv", csv_content, "text/csv")}
        resp = client.post(
            f"/api/v1/produtos/importar-catalogo/{fornecedor_id}/",
            files=files,
            headers=headers,
        )
        assert resp.status_code == 200
        created_ids = [p["id"] for p in resp.json()["produtos_criados"]]
        assert len(created_ids) == 2
    
        resp = client.get("/api/v1/historico/", headers=headers)
        assert resp.status_code == 200
        historicos = [
            h
            for h in resp.json()["items"]
            if h["entidade"] == "Produto" and h["acao"] == "CRIACAO"
        ]
        ids_in_hist = [h["entity_id"] for h in historicos if h["entity_id"] in created_ids]
        assert len(ids_in_hist) == len(created_ids)

    def test_fornecedor_mapping_endpoints():
        """Run test fornecedor mapping endpoints in this workflow."""
        headers = get_user_headers()
        resp = client.post(
            "/api/v1/fornecedores/",
            json={"nome": "Map Forn"},
            headers=headers,
        )
        assert resp.status_code == 201
        fornecedor_id = resp.json()["id"]
    
        mapping = {"nome_base": "Nome", "sku": "SKU"}
        resp = client.put(
            f"/api/v1/fornecedores/{fornecedor_id}/mapping",
            json=mapping,
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["default_column_mapping"] == mapping
    
        resp = client.get(
            f"/api/v1/fornecedores/{fornecedor_id}/mapping",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == mapping

override_get_db = _TopLevelFunctionSurface.override_get_db
get_user_headers = _TopLevelFunctionSurface.get_user_headers
test_historico_records_product_creation = _TopLevelFunctionSurface.test_historico_records_product_creation
test_historico_records_bulk_import = _TopLevelFunctionSurface.test_historico_records_bulk_import
test_fornecedor_mapping_endpoints = _TopLevelFunctionSurface.test_fornecedor_mapping_endpoints

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

initial_data_workflow = InitialDataWorkflow()

# Prepare initial data
with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)
    user_in = schemas.UserCreate(
        email="user@example.com",
        password="secret",
        nome_completo="Normal User",
    )
    MainBootstrapWorkflow().create_new_user(user_in=user_in, session=db)









