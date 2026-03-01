import pytest
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import MainBootstrapWorkflow, app
from Backend.database import Base, get_db
from Backend import schemas, models
from Backend.initial_data import InitialDataWorkflow
from Backend.core.config import settings
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository

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

    def get_user_headers():
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "user2@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_historico_created_on_product_crud():
        headers = get_user_headers()
        # create
        resp = client.post("/api/v1/produtos/", json={"nome_base": "HistProd"}, headers=headers)
        assert resp.status_code == 201
        produto_id = resp.json()["id"]
        # update
        resp = client.put(f"/api/v1/produtos/{produto_id}", json={"nome_base": "HistProd2"}, headers=headers)
        assert resp.status_code == 200
        # delete
        resp = client.delete(f"/api/v1/produtos/{produto_id}", headers=headers)
        assert resp.status_code == 200
        with TestingSessionLocal() as db:
            logs = db.query(models.RegistroHistorico).filter(models.RegistroHistorico.entity_id == produto_id).all()
            actions = [log.acao for log in logs]
            assert models.TipoAcaoSistemaEnum.CRIACAO in actions
            assert models.TipoAcaoSistemaEnum.ATUALIZACAO in actions
            assert models.TipoAcaoSistemaEnum.DELECAO in actions

    def test_list_historico_endpoint():
        headers = get_user_headers()
        # cria um registro para garantir algum resultado
        with TestingSessionLocal() as db:
            HistoricoRepository(db).create_registro_historico(
                registro_in=schemas.RegistroHistoricoCreate(
                    user_id=normal_user.id,
                    entidade="Teste",
                    acao=models.TipoAcaoSistemaEnum.CRIACAO,
                    entity_id=123,
                ),
            )
    
        resp = client.get("/api/v1/historico/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_tipos_acao_endpoint():
        headers = get_user_headers()
        resp = client.get("/api/v1/historico/tipos", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
    
        resp = client.get("/api/v1/historico/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1

override_get_db = _TopLevelFunctionSurface.override_get_db
get_user_headers = _TopLevelFunctionSurface.get_user_headers
test_historico_created_on_product_crud = _TopLevelFunctionSurface.test_historico_created_on_product_crud
test_list_historico_endpoint = _TopLevelFunctionSurface.test_list_historico_endpoint
test_get_tipos_acao_endpoint = _TopLevelFunctionSurface.test_get_tipos_acao_endpoint

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

initial_data_workflow = InitialDataWorkflow()

with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)
    user_in = schemas.UserCreate(email="user2@example.com", password="secret", nome_completo="Normal User")
    normal_user = MainBootstrapWorkflow().create_new_user(user_in=user_in, session=db)









