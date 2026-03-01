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
from Backend.main import create_new_user
from Backend.core.config import settings
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)

# disable heavy startup events
app.router.on_startup.clear()

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# override dependency

class _TopLevelFunctionSurface:

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_admin_headers():
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def get_user_headers():
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "user@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_admin_can_view_usos_ia_of_other_user_product():
        headers = get_admin_headers()
        # get product id created earlier
        with TestingSessionLocal() as db:
            produto = db.query(models.Produto).filter(models.Produto.nome_base == "TesteProd").first()
        resp = client.get(f"/api/v1/uso-ia/por-produto/{produto.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(item["produto_id"] == produto.id for item in data)

    def test_product_creation_creates_uso_ia_record():
        headers = get_user_headers()
        resp = client.post(
            "/api/v1/produtos/",
            json={"nome_base": "Novo Produto"},
            headers=headers,
        )
        assert resp.status_code == 201
        produto_id = resp.json()["id"]
        with TestingSessionLocal() as db:
            registros = (
                db.query(models.RegistroUsoIA)
                .filter(
                    models.RegistroUsoIA.produto_id == produto_id,
                    models.RegistroUsoIA.tipo_acao == models.TipoAcaoEnum.CRIACAO_PRODUTO,
                )
                .all()
            )
            assert len(registros) == 1

    def test_pagination_returns_1_based_page_for_uso_ia():
        headers = get_user_headers()
        resp = client.get("/api/v1/uso-ia", params={"skip": 0, "limit": 10}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
    
        resp = client.get("/api/v1/uso-ia", params={"skip": 10, "limit": 10}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2

    def test_first_page_number_for_uso_ia():
        headers = get_user_headers()
        resp = client.get("/api/v1/uso-ia", params={"skip": 0, "limit": 5}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1

override_get_db = _TopLevelFunctionSurface.override_get_db
get_admin_headers = _TopLevelFunctionSurface.get_admin_headers
get_user_headers = _TopLevelFunctionSurface.get_user_headers
test_admin_can_view_usos_ia_of_other_user_product = _TopLevelFunctionSurface.test_admin_can_view_usos_ia_of_other_user_product
test_product_creation_creates_uso_ia_record = _TopLevelFunctionSurface.test_product_creation_creates_uso_ia_record
test_pagination_returns_1_based_page_for_uso_ia = _TopLevelFunctionSurface.test_pagination_returns_1_based_page_for_uso_ia
test_first_page_number_for_uso_ia = _TopLevelFunctionSurface.test_first_page_number_for_uso_ia

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

initial_data_workflow = get_initial_data_workflow()

# setup initial data
with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)
    user_in = schemas.UserCreate(
        email="user@example.com",
        password="secret",
        nome_completo="Normal User",
    )
    normal_user = create_new_user(user_in=user_in, db=db)
    produto = ProductRepository(db).create_produto(
        produto=schemas.ProdutoCreate(nome_base="TesteProd"),
        user_id=normal_user.id,
    )
    RegistroUsoIARepository(db).create_registro_uso_ia(
        registro_uso=schemas.RegistroUsoIACreate(
            user_id=normal_user.id,
            produto_id=produto.id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        ),
    )
    # create extra registros for pagination tests
    for i in range(15):
        RegistroUsoIARepository(db).create_registro_uso_ia(
            registro_uso=schemas.RegistroUsoIACreate(
                user_id=normal_user.id,
                produto_id=produto.id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
            ),
        )












