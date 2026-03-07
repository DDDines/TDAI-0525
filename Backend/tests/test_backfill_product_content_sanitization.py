"""Tests for maintenance backfill sanitation workflows."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)
from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)
from scripts import backfill_product_content_sanitization as backfill_script


class _FakeColumn:
    """Minimal SQLAlchemy-like column stub for backfill query flow tests."""

    def __gt__(self, other):
        """Represent greater-than expressions without relying on SQLAlchemy internals."""
        return ("gt", other)

    def __eq__(self, other):
        """Represent equality expressions without relying on SQLAlchemy internals."""
        return ("eq", other)

    def asc(self):
        """Represent ``order_by(column.asc())`` without SQLAlchemy."""
        return self


class _FakeQuery:
    """Minimal chained query object for backfill batch iteration tests."""

    def __init__(self, session):
        """Store shared fake session state."""
        self._session = session

    def filter(self, *_args, **_kwargs):
        """Ignore filters while keeping the fluent API shape."""
        return self

    def order_by(self, *_args, **_kwargs):
        """Ignore ordering while keeping the fluent API shape."""
        return self

    def limit(self, *_args, **_kwargs):
        """Ignore limits while keeping the fluent API shape."""
        return self

    def all(self):
        """Return one batch and then terminate iteration."""
        if self._session._served:
            return []
        self._session._served = True
        return self._session._batch


class _FakeSession:
    """Fake session to verify flush/expunge ordering in the backfill script."""

    def __init__(self, batch):
        """Initialize fake session state for one backfill run."""
        self._batch = batch
        self._served = False
        self.events = []

    def query(self, _model):
        """Return a chained fake query object."""
        return _FakeQuery(self)

    def flush(self):
        """Record pending-change flushes before expunge."""
        self.events.append("flush")

    def expunge_all(self):
        """Record detachment operations."""
        self.events.append("expunge_all")

    def commit(self):
        """Record commits performed by the workflow."""
        self.events.append("commit")

    def rollback(self):
        """Record rollbacks performed by the workflow."""
        self.events.append("rollback")

    def close(self):
        """Record session close."""
        self.events.append("close")


class _TopLevelFunctionSurface:
    """Surface helpers for backfill tests."""

    @staticmethod
    def test_sanitize_product_payload_rebuilds_generated_content():
        """Rebuild legacy generated titles/descriptions using the current basic generator rules."""
        produto = SimpleNamespace(
            id=2558,
            nome_base="Reservatório de AR 20 Litros",
            nome_chat_api="Reservatório de Ar 20 Litros ROCHEPECAS 3084307005",
            descricao_original=(
                "Reservatório de Ar 20 Litros ROCHEPECAS 3084307005 para Mercedes Benz. "
                "Se surgirem dúvidas, entre em contato conosco pelo telefone 11 2206-5000."
            ),
            descricao_chat_api=(
                "Reservatório de AR 20 Litros, marca Mercadocar. "
                "Criptografia e segurança para garantir tranquilidade. "
                "Política de troca e devolução simples e transparente."
            ),
            marca="Mercadocar",
            modelo="",
            sku="987 308 430 7005",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={
                "titulo_auto": "Reservatório de Ar 20 Litros - ROCHEPECAS 3084307005",
                "Material": "Metálico",
            },
            dados_brutos_web={
                "descricao_curta": (
                    "Reservatório de ar para Mercedes Benz. "
                    "Se surgirem dúvidas, entre em contato conosco pelo telefone 11 2206-5000."
                ),
                "descricao_detalhada_seo": (
                    "Reservatório de ar para Mercedes Benz com alta performance. "
                    "Criptografia e segurança para garantir tranquilidade. "
                    "Política de troca e devolução simples e transparente."
                ),
                "texto_relevante_coletado": (
                    "Reservatório de ar ROCHEPECAS para Mercedes Benz com aplicação em freios e suspensão."
                ),
                "descricao_gerada": (
                    "Reservatório de AR 20 Litros, marca Mercadocar. "
                    "Sua compra online protegida. Criptografia e segurança para garantir tranquilidade."
                ),
                "titulos_sugeridos_gerados": [
                    "Reservatório de AR 20 Litros Mercadocar 987 308 430 7005 seguran",
                    "Reservatório de AR 20 Litros Mercadocar 987 308 430 7005 pol",
                    "Reservatório de AR 20 Litros Mercadocar 987 308 430 7005 criptografia",
                ],
                "palavras_chave_seo_relevantes_lista": ["seguran", "pol", "sua"],
                "especificacoes_tecnicas_dict": {
                    "Aplicação": "Mercedes Benz",
                    "Material": "Metálico",
                },
            },
        )
        sanitizer = CatalogImportSanitizationService(CatalogImportQualityService())
        basic_generation_service = BasicContentGenerationService()

        changed, fields = backfill_script._TopLevelFunctionSurface._sanitize_product_payload(
            produto,
            sanitizer=sanitizer,
            basic_generation_service=basic_generation_service,
        )

        assert changed is True
        assert "dados_brutos_web.titulos_sugeridos_gerados" in fields
        assert "descricao_chat_api" in fields
        titles = produto.dados_brutos_web["titulos_sugeridos_gerados"]
        assert titles
        assert any("rochepecas" in title.lower() for title in titles)
        assert all("mercadocar" not in title.lower() for title in titles)
        assert all("seguran" not in title.lower() for title in titles)
        assert all("criptografia" not in title.lower() for title in titles)
        assert "mercadocar" not in produto.descricao_chat_api.lower()
        assert "telefone" not in produto.descricao_chat_api.lower()
        assert "criptografia" not in produto.descricao_chat_api.lower()
        assert "política de troca" not in produto.descricao_chat_api.lower()
        assert "rochepecas" in produto.descricao_chat_api.lower()

    @staticmethod
    def test_sanitize_product_payload_substitui_nome_base_lixo_por_placeholder_tecnico():
        """Replace obvious import garbage labels when no meaningful product identity exists."""
        produto = SimpleNamespace(
            id=999,
            nome_base="Acesse nosso",
            nome_chat_api=None,
            descricao_original="",
            descricao_chat_api=None,
            marca=None,
            modelo=None,
            sku=None,
            ean=None,
            categoria_original=None,
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={},
        )
        sanitizer = CatalogImportSanitizationService(CatalogImportQualityService())
        basic_generation_service = BasicContentGenerationService()

        changed, _fields = backfill_script._TopLevelFunctionSurface._sanitize_product_payload(
            produto,
            sanitizer=sanitizer,
            basic_generation_service=basic_generation_service,
        )

        assert changed is True
        assert produto.nome_base == "Produto 999"

    @staticmethod
    def test_run_backfill_flushes_pending_changes_before_expunge(monkeypatch):
        """Flush pending updates before ``expunge_all`` so final commits are not silently lost."""
        fake_produto = SimpleNamespace(id=1, user_id=99)
        fake_session = _FakeSession([fake_produto])
        fake_models = SimpleNamespace(
            Produto=SimpleNamespace(id=_FakeColumn(), user_id=_FakeColumn())
        )

        monkeypatch.setattr(backfill_script, "SessionLocal", lambda: fake_session)
        monkeypatch.setattr(backfill_script, "models", fake_models)
        monkeypatch.setattr(
            backfill_script._TopLevelFunctionSurface,
            "_sanitize_product_payload",
            staticmethod(
                lambda produto, *, sanitizer, basic_generation_service: (
                    True,
                    Counter({"descricao_chat_api": 1}),
                )
            ),
        )

        exit_code = backfill_script._TopLevelFunctionSurface.run_backfill(
            apply_changes=True,
            limit=1,
            user_id=None,
            produto_id=None,
            commit_every=200,
            verbose=False,
        )

        assert exit_code == 0
        assert "flush" in fake_session.events
        assert "expunge_all" in fake_session.events
        assert fake_session.events.index("flush") < fake_session.events.index("expunge_all")
        assert fake_session.events.count("commit") == 1


test_sanitize_product_payload_rebuilds_generated_content = (
    _TopLevelFunctionSurface.test_sanitize_product_payload_rebuilds_generated_content
)
test_sanitize_product_payload_substitui_nome_base_lixo_por_placeholder_tecnico = (
    _TopLevelFunctionSurface.test_sanitize_product_payload_substitui_nome_base_lixo_por_placeholder_tecnico
)
test_run_backfill_flushes_pending_changes_before_expunge = (
    _TopLevelFunctionSurface.test_run_backfill_flushes_pending_changes_before_expunge
)
