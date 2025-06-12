import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, schemas, models
from Backend.core.config import settings

# disable heavy startup events
app.router.on_startup.clear()

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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

# setup initial data
with TestingSessionLocal() as db:
    crud.create_initial_data(db)


def get_admin_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_importacao_relatorio_de_erros():
    headers = get_admin_headers()
    csv_content = "nome,sku\nProduto Válido,123\n,\n"
    file_bytes = csv_content.encode()
    files = {"file": ("catalogo.csv", io.BytesIO(file_bytes), "text/csv")}
    resp = client.post("/api/v1/produtos/importar-catalogo/1/", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "produtos_criados" in data
    assert "erros" in data
    assert len(data["produtos_criados"]) == 1
    assert len(data["erros"]) == 1
    assert "motivo_descarte" in data["erros"][0]


def test_historico_criado_para_produtos_importados():
    headers = get_admin_headers()
    csv_content = "nome,sku\nProd1,111\nProd2,222\n"
    file_bytes = csv_content.encode()
    files = {"file": ("catalogo.csv", io.BytesIO(file_bytes), "text/csv")}
    resp = client.post("/api/v1/produtos/importar-catalogo/1/", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    created_ids = [prod["id"] for prod in data["produtos_criados"]]
    assert len(created_ids) == 2

    with TestingSessionLocal() as db:
        logs = db.query(models.RegistroHistorico).filter(
            models.RegistroHistorico.entity_id.in_(created_ids),
            models.RegistroHistorico.entidade == "Produto",
            models.RegistroHistorico.acao == models.TipoAcaoSistemaEnum.CRIACAO,
        ).all()
        assert len(logs) == len(created_ids)
