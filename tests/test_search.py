from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, crud_produtos, crud_fornecedores, schemas, models
from Backend.core.config import settings

app.router.on_startup.clear()

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Prepare sample data
with TestingSessionLocal() as db:
    crud.create_initial_data(db)
    admin = crud.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
    crud_produtos.create_produto(db, schemas.ProdutoCreate(nome_base="BuscaTest"), user_id=admin.id)
    crud_fornecedores.create_fornecedor(db, schemas.FornecedorCreate(nome="FornecedorTeste"), user_id=admin.id)


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
