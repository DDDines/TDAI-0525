"""Tests for the import_review router — covers quarantine listing, item approval, and batch approval."""

from __future__ import annotations

import os
os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "admin@example.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "password")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "password")

from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from Backend.main import app
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.routers import auth_utils as auth_utils_module


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fake_user(user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        is_active=True,
        is_superuser=False,
        email="test@example.com",
    )


def _fake_catalog_file(fornecedor_id: int = 5, result_summary=None):
    return SimpleNamespace(
        id=1,
        fornecedor_id=fornecedor_id,
        result_summary=result_summary or {},
    )


def _fake_session():
    session = MagicMock()
    session.commit.return_value = None
    session.refresh.return_value = None
    return session


def _fake_produto_db():
    from datetime import datetime
    return SimpleNamespace(
        id=99,
        nome_base="Produto Aprovado",
        user_id=1,
        sku=None,
        ean=None,
        descricao_original=None,
        descricao_chat_api=None,
        nome_chat_api=None,
        marca=None,
        categoria_original=None,
        dados_brutos_web=None,
        dynamic_attributes=None,
        fornecedor_id=5,
        product_type_id=None,
        import_quality_score=None,
        titulos_sugeridos=None,
        fornecedor=None,
        product_type=None,
        log_enriquecimento_web=None,
        preco_original=None,
        imagem_url_original=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# Disable heavy startup events
app.router.on_startup.clear()

_fake_user_instance = _fake_user()

_AUTH_DEP = auth_utils_module._AuthUtilsActiveUserDependency.get_current_active_user
_SESSION_DEP = ServiceContainerDependencySupport.get_request_db_session


import pytest


@pytest.fixture(autouse=True)
def _override_deps():
    """Apply test-scoped dependency overrides and clean up after each test."""
    app.dependency_overrides[_AUTH_DEP] = lambda: _fake_user_instance
    app.dependency_overrides[_SESSION_DEP] = _fake_session
    yield
    app.dependency_overrides.pop(_AUTH_DEP, None)
    app.dependency_overrides.pop(_SESSION_DEP, None)


client = TestClient(app)


class _TopLevelFunctionSurface:
    """Centralize all import_review router test functions as static methods."""

    def test_listar_quarentena_arquivo_nao_encontrado_retorna_404():
        """When catalog file is not found, GET quarentena returns 404."""
        with patch(
            "Backend.routers.import_review.CatalogFileRepository"
        ) as MockRepo:
            instance = MagicMock()
            instance.get_catalog_file_for_user.return_value = None
            MockRepo.return_value = instance

            response = client.get("/api/v1/importacoes/999/quarentena")

        assert response.status_code == 404

    def test_listar_quarentena_retorna_lista():
        """When catalog file exists with quarantined items, returns 200 with data."""
        quarantine_items = [
            {
                "linha_sanitizada": {"nome_base": "Produto X", "sku_original": "P001"},
                "qualidade_score": 55.0,
                "motivo_descarte": "score baixo",
            }
        ]
        catalog_file = _fake_catalog_file(
            result_summary={"quarantine_non_critical": quarantine_items}
        )

        with (
            patch("Backend.routers.import_review.CatalogFileRepository") as MockRepo,
            patch("Backend.routers.import_review.ImportValidationMemoryService") as MockSvc,
        ):
            repo_instance = MagicMock()
            repo_instance.get_catalog_file_for_user.return_value = catalog_file
            MockRepo.return_value = repo_instance

            svc_instance = MagicMock()
            svc_instance.get_quarantine_items.return_value = quarantine_items
            MockSvc.return_value = svc_instance

            response = client.get("/api/v1/importacoes/1/quarentena")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["nome_base"] == "Produto X"

    def test_aprovar_item_arquivo_nao_encontrado_retorna_404():
        """When catalog file is not found, POST aprovar returns 404."""
        with patch("Backend.routers.import_review.CatalogFileRepository") as MockRepo:
            instance = MagicMock()
            instance.get_catalog_file_for_user.return_value = None
            MockRepo.return_value = instance

            response = client.post(
                "/api/v1/importacoes/999/quarentena/0/aprovar",
                json={"remember": False},
            )

        assert response.status_code == 404

    def test_aprovar_item_retorna_produto():
        """When approve_item returns a product, POST aprovar returns 200."""
        from Backend import schemas as _schemas

        catalog_file = _fake_catalog_file()
        produto_response = _schemas.ProdutoResponse(
            id=99,
            nome_base="Produto Aprovado",
            user_id=1,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        with (
            patch("Backend.routers.import_review.CatalogFileRepository") as MockRepo,
            patch("Backend.routers.import_review.ImportValidationMemoryService") as MockSvc,
            patch("Backend.routers.import_review.ProductRepository"),
            patch.object(
                _schemas.ProdutoResponse,
                "model_validate",
                return_value=produto_response,
            ),
        ):
            repo_instance = MagicMock()
            repo_instance.get_catalog_file_for_user.return_value = catalog_file
            MockRepo.return_value = repo_instance

            svc_instance = MagicMock()
            # approve_item returns a non-None value
            svc_instance.approve_item.return_value = MagicMock()
            MockSvc.return_value = svc_instance

            response = client.post(
                "/api/v1/importacoes/1/quarentena/0/aprovar",
                json={"remember": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 99

    def test_aprovar_item_indice_invalido_retorna_404():
        """When approve_item returns None, POST aprovar returns 404."""
        catalog_file = _fake_catalog_file()

        with (
            patch("Backend.routers.import_review.CatalogFileRepository") as MockRepo,
            patch("Backend.routers.import_review.ImportValidationMemoryService") as MockSvc,
            patch("Backend.routers.import_review.ProductRepository"),
        ):
            repo_instance = MagicMock()
            repo_instance.get_catalog_file_for_user.return_value = catalog_file
            MockRepo.return_value = repo_instance

            svc_instance = MagicMock()
            svc_instance.approve_item.return_value = None
            MockSvc.return_value = svc_instance

            response = client.post(
                "/api/v1/importacoes/1/quarentena/99/aprovar",
                json={"remember": False},
            )

        assert response.status_code == 404

    def test_aprovar_lote_retorna_count():
        """Batch approve endpoint returns count of approved items."""
        quarantine_items = [
            {"linha_sanitizada": {"nome_base": "A"}, "qualidade_score": 80.0},
            {"linha_sanitizada": {"nome_base": "B"}, "qualidade_score": 50.0},
        ]
        catalog_file = _fake_catalog_file(
            result_summary={"quarantine_non_critical": quarantine_items}
        )

        with (
            patch("Backend.routers.import_review.CatalogFileRepository") as MockRepo,
            patch("Backend.routers.import_review.ImportValidationMemoryService") as MockSvc,
            patch("Backend.routers.import_review.ProductRepository"),
        ):
            repo_instance = MagicMock()
            repo_instance.get_catalog_file_for_user.return_value = catalog_file
            MockRepo.return_value = repo_instance

            svc_instance = MagicMock()
            svc_instance.get_quarantine_items.return_value = quarantine_items
            # Both items approved
            svc_instance.approve_item.side_effect = [
                SimpleNamespace(id=1),
                SimpleNamespace(id=2),
            ]
            MockSvc.return_value = svc_instance

            response = client.post(
                "/api/v1/importacoes/1/quarentena/aprovar-lote",
                json={"min_quality_score": 45.0, "remember": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["aprovados"] == 2
        assert data["threshold_score"] == 45.0


test_listar_quarentena_arquivo_nao_encontrado_retorna_404 = _TopLevelFunctionSurface.test_listar_quarentena_arquivo_nao_encontrado_retorna_404
test_listar_quarentena_retorna_lista = _TopLevelFunctionSurface.test_listar_quarentena_retorna_lista
test_aprovar_item_arquivo_nao_encontrado_retorna_404 = _TopLevelFunctionSurface.test_aprovar_item_arquivo_nao_encontrado_retorna_404
test_aprovar_item_retorna_produto = _TopLevelFunctionSurface.test_aprovar_item_retorna_produto
test_aprovar_item_indice_invalido_retorna_404 = _TopLevelFunctionSurface.test_aprovar_item_indice_invalido_retorna_404
test_aprovar_lote_retorna_count = _TopLevelFunctionSurface.test_aprovar_lote_retorna_count
