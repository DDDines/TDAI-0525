import os
import pytest

pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient

# Configure an in-memory SQLite database for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from Backend.database import Base, engine, SessionLocal, get_db
from Backend.main import app
from Backend import crud, schemas

# Disable heavy startup events
app.router.on_startup.clear()

# Create all tables
Base.metadata.create_all(bind=engine)

# Dependency override to use the test DB

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_user_registration_and_login():
    # Ensure required Role and Plano exist
    with SessionLocal() as db:
        if not crud.get_role_by_name(db, "user"):
            crud.create_role(db, schemas.RoleCreate(name="user", description="User"))
        if not crud.get_plano_by_name(db, "Gratuito"):
            crud.create_plano(
                db,
                schemas.PlanoCreate(
                    nome="Gratuito",
                    descricao="Plano gratuito",
                    preco_mensal=0.0,
                    limite_produtos=10,
                    limite_enriquecimento_web=10,
                    limite_geracao_ia=10,
                    permite_api_externa=False,
                    suporte_prioritario=False,
                ),
            )

    user_data = {
        "email": "test@example.com",
        "password": "secret",
        "nome_completo": "Test User",
    }
    resp = client.post("/api/v1/users/", json=user_data)
    assert resp.status_code == 201
    assert resp.json()["email"] == user_data["email"]

    login_data = {"username": user_data["email"], "password": user_data["password"]}
    resp = client.post("/api/v1/auth/token", data=login_data)
    assert resp.status_code == 200
    assert "access_token" in resp.json()
