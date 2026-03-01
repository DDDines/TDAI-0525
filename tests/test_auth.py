import os
import pytest
from uuid import uuid4

# Capture any existing DATABASE_URL so it can be restored later
PREV_DATABASE_URL = os.environ.get("DATABASE_URL")

pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient

# Configure an in-memory SQLite database for tests; this overrides any
# existing value but we'll restore it after the tests finish
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from Backend.database import Base, engine, SessionLocal, get_db
from Backend.main import app
from Backend import schemas
from Backend.infrastructure.repositories.user_repository import UserRepository

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


@pytest.fixture(scope="module", autouse=True)
def restore_database_url():
    """Restore the original DATABASE_URL after the tests in this module."""
    yield
    if PREV_DATABASE_URL is not None:
        os.environ["DATABASE_URL"] = PREV_DATABASE_URL
    else:
        os.environ.pop("DATABASE_URL", None)


def test_user_registration_and_login():
    # Ensure required Role and Plano exist
    with SessionLocal() as db:
        user_repo = UserRepository(db)
        if not user_repo.get_role_by_name(name="user"):
            user_repo.create_role(role=schemas.RoleCreate(name="user", description="User"))
        if not user_repo.get_plano_by_name(nome="Gratuito"):
            user_repo.create_plano(
                plano=schemas.PlanoCreate(
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
        "email": f"test-{uuid4().hex[:12]}@example.com",
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
