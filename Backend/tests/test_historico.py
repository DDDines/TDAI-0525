import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app, create_new_user
from Backend.database import Base, get_db
from Backend import crud, schemas

# Disable heavy startup events so tests run faster
app.router.on_startup.clear()

# In-memory SQLite for isolated tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency override

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Prepare initial data
with TestingSessionLocal() as db:
    crud.create_initial_data(db)
    user_in = schemas.UserCreate(
        email="user@example.com",
        password="secret",
        nome_completo="Normal User",
    )
    create_new_user(user_in=user_in, db=db)


def get_user_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "user@example.com", "password": "secret"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_historico_records_product_creation():
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
