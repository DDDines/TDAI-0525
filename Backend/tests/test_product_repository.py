"""Risk-focused coverage for the product repository."""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models, schemas
from Backend.database import Base
from Backend.infrastructure.repositories import product_repository as product_repository_module
from Backend.infrastructure.repositories.product_repository import ProductRepository


def _build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    return engine, session


def _create_user(session, *, email: str):
    user = models.User(
        email=email,
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_fornecedor(session, *, user_id: int, nome: str = "Fornecedor Base"):
    fornecedor = models.Fornecedor(nome=nome, user_id=user_id)
    session.add(fornecedor)
    session.commit()
    session.refresh(fornecedor)
    return fornecedor


def _create_product_type(session, *, key_name: str = "tipo-base", friendly_name: str = "Tipo Base"):
    product_type = models.ProductType(
        key_name=key_name,
        friendly_name=friendly_name,
        description=friendly_name,
    )
    session.add(product_type)
    session.commit()
    session.refresh(product_type)
    return product_type


def _create_attribute_template(session, *, product_type_id: int, attribute_key: str = "cor"):
    attribute = models.AttributeTemplate(
        product_type_id=product_type_id,
        attribute_key=attribute_key,
        label=attribute_key.title(),
        field_type=models.AttributeFieldTypeEnum.TEXT,
        display_order=0,
    )
    session.add(attribute)
    session.commit()
    session.refresh(attribute)
    return attribute


def _create_product(
    session,
    *,
    user_id: int,
    nome_base: str,
    sku: str | None = None,
    ean: str | None = None,
    fornecedor_id: int | None = None,
    product_type_id: int | None = None,
    categoria_original: str | None = None,
    status_enriquecimento_web=models.StatusEnriquecimentoEnum.NAO_INICIADO,
    status_titulo_ia=models.StatusGeracaoIAEnum.NAO_INICIADO,
    status_descricao_ia=models.StatusGeracaoIAEnum.NAO_INICIADO,
):
    product = models.Produto(
        user_id=user_id,
        nome_base=nome_base,
        sku=sku,
        ean=ean,
        fornecedor_id=fornecedor_id,
        product_type_id=product_type_id,
        categoria_original=categoria_original,
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


class _UploadFileStub:
    def __init__(self, *, filename: str | None, content: bytes = b"data", error: Exception | None = None):
        self.filename = filename
        self._content = content
        self._error = error
        self.closed = False

    async def read(self):
        if self._error:
            raise self._error
        return self._content

    async def close(self):
        self.closed = True


class _PayloadWithDump:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self, **_kwargs):
        return dict(self._payload)

    def __getattr__(self, item):
        return self._payload.get(item)


def test_product_repository_create_and_bulk_paths_cover_json_and_duplicates():
    engine, session = _build_session()
    try:
        user = _create_user(session, email="owner@example.com")
        repo = ProductRepository(session)
        existing_sku = _create_product(
            session,
            user_id=user.id,
            nome_base="Produto SKU",
            sku="SKU-001",
        )
        existing_ean = _create_product(
            session,
            user_id=user.id,
            nome_base="Produto EAN",
            ean="1234567890123",
        )

        created = repo.create_produto(
            produto=_PayloadWithDump(
                {
                    "nome_base": "Produto JSON",
                    "sku": "SKU-JSON",
                    "ean": "",
                    "dynamic_attributes": '{"cor":"azul"}',
                    "dados_brutos_web": '{"origem":"web"}',
                    "log_enriquecimento_web": '{"historico_mensagens":["inicio"]}',
                }
            ),
            user_id=user.id,
        )
        assert created.sku == "SKU-JSON"
        assert created.ean is None
        assert created.dynamic_attributes == {"cor": "azul"}
        assert created.dados_brutos_web == {"origem": "web"}
        assert created.log_enriquecimento_web == {"historico_mensagens": ["inicio"]}

        with pytest.raises(ValueError):
            repo.create_produto(
                produto=_PayloadWithDump(
                    {
                        "nome_base": "Produto Invalido",
                        "dynamic_attributes": "{invalido",
                    }
                ),
                user_id=user.id,
            )

        with pytest.raises(HTTPException) as sku_error:
            repo.create_produto(
                produto=schemas.ProdutoCreate(nome_base="Duplicado", sku="SKU-001"),
                user_id=user.id,
            )
        assert sku_error.value.status_code == 409

        with pytest.raises(HTTPException) as ean_error:
            repo.create_produto(
                produto=schemas.ProdutoCreate(nome_base="Duplicado EAN", ean="1234567890123"),
                user_id=user.id,
            )
        assert ean_error.value.status_code == 409

        created_bulk, updated_bulk, errors = repo.create_produtos_bulk(
            produtos=[
                schemas.ProdutoCreate(nome_base="Novo Bulk", sku="SKU-BULK"),
                schemas.ProdutoCreate(nome_base="Atualiza SKU", sku="SKU-001"),
                schemas.ProdutoCreate(nome_base="Atualiza EAN", ean="1234567890123"),
                schemas.ProdutoCreate(nome_base="Duplicado no Lote", sku="SKU-BULK"),
                _PayloadWithDump(
                    {
                        "nome_base": "Com JSON",
                        "ean": "9999999999999",
                        "dados_brutos_web": '{"fonte":"batch"}',
                    }
                ),
            ],
            user_id=user.id,
        )

        assert [item.nome_base for item in created_bulk] == ["Novo Bulk", "Com JSON"]
        assert {item.id for item in updated_bulk} == {existing_sku.id, existing_ean.id}
        assert existing_sku.nome_base == "Atualiza SKU"
        assert existing_ean.nome_base == "Atualiza EAN"
        assert created_bulk[1].dados_brutos_web == {"fonte": "batch"}
        assert errors == [
            {
                "motivo_descarte": "Produto duplicado por SKU ou EAN",
                "linha_original": {"nome_base": "Duplicado no Lote", "sku": "SKU-BULK"},
                "duplicado": True,
            }
        ]
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_product_repository_listing_filters_search_status_and_admin_guards():
    engine, session = _build_session()
    try:
        owner = _create_user(session, email="owner@example.com")
        other = _create_user(session, email="other@example.com")
        fornecedor = _create_fornecedor(session, user_id=owner.id, nome="Fornecedor Freios")
        product_type = _create_product_type(session, key_name="freios", friendly_name="Freios")
        _create_attribute_template(session, product_type_id=product_type.id)
        product = _create_product(
            session,
            user_id=owner.id,
            nome_base="Pastilha Premium",
            sku="A-001",
            fornecedor_id=fornecedor.id,
            product_type_id=product_type.id,
            categoria_original="Freios",
            status_enriquecimento_web=models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO,
            status_titulo_ia=models.StatusGeracaoIAEnum.CONCLUIDO,
            status_descricao_ia=models.StatusGeracaoIAEnum.EM_PROGRESSO,
        )
        product.nome_chat_api = "Pastilha de Freio Premium"
        product.descricao_original = "Linha para freios"
        product.marca = "Marca X"
        product.modelo = "Modelo Pro"
        product.log_enriquecimento_web = {"historico_mensagens": ["inicio"]}
        session.commit()
        _create_product(
            session,
            user_id=other.id,
            nome_base="Produto de Outro Usuario",
            sku="B-001",
            categoria_original="Outro",
        )
        repo = ProductRepository(session)

        loaded = repo.get_produto(produto_id=product.id)
        assert loaded is not None
        assert loaded.fornecedor.nome == "Fornecedor Freios"
        assert loaded.product_type.friendly_name == "Freios"
        assert len(loaded.product_type.attribute_templates) == 1

        updated_status = repo.set_web_enrichment_status(
            produto_id=product.id,
            status=models.StatusEnriquecimentoEnum.FALHOU,
            log_message="falhou",
        )
        assert updated_status.status_enriquecimento_web == models.StatusEnriquecimentoEnum.FALHOU
        assert updated_status.log_enriquecimento_web == {"historico_mensagens": ["inicio", "falhou"]}
        assert repo.set_web_enrichment_status(
            produto_id=99999,
            status=models.StatusEnriquecimentoEnum.CONCLUIDO,
        ) is None

        assert repo.get_produto_for_update(produto_id=product.id).id == product.id

        filtered = repo.get_produtos_by_user(
            user_id=owner.id,
            is_admin=False,
            sort_by="nome_base",
            sort_order="desc",
            search="premium",
            fornecedor_id=fornecedor.id,
            product_type_id=product_type.id,
            categoria="freios",
            status_enriquecimento_web=models.StatusEnriquecimentoEnum.FALHOU,
            status_titulo_ia=models.StatusGeracaoIAEnum.CONCLUIDO,
            status_descricao_ia=models.StatusGeracaoIAEnum.EM_PROGRESSO,
        )
        assert [item.id for item in filtered] == [product.id]
        assert repo.count_produtos_by_user(
            user_id=owner.id,
            is_admin=False,
            search="premium",
            fornecedor_id=fornecedor.id,
            product_type_id=product_type.id,
            categoria="freios",
            status_enriquecimento_web=models.StatusEnriquecimentoEnum.FALHOU,
            status_titulo_ia=models.StatusGeracaoIAEnum.CONCLUIDO,
            status_descricao_ia=models.StatusGeracaoIAEnum.EM_PROGRESSO,
        ) == 1
        assert repo.set_web_enrichment_status(
            produto_id=product.id,
            status=models.StatusEnriquecimentoEnum.CONCLUIDO,
        ).status_enriquecimento_web == models.StatusEnriquecimentoEnum.CONCLUIDO
        assert [item.id for item in repo.get_produtos_by_user(user_id=owner.id, is_admin=False, sort_by="nome_base")] == [product.id]
        assert [item.id for item in repo.get_produtos_by_user(user_id=owner.id, is_admin=False, sort_by="inexistente")] == [product.id]
        assert repo.get_produtos_by_user(user_id=None, is_admin=False) == []
        assert repo.count_produtos_by_user(user_id=None, is_admin=False) == 0

        rows_for_index = repo.search_produtos_for_index(
            query_text="pastilha",
            limit=5,
            user_id=owner.id,
            is_admin=False,
        )
        assert [(row.id, row.nome_base) for row in rows_for_index] == [(product.id, "Pastilha Premium")]
        assert repo.search_produtos_for_index(
            query_text=None,
            limit=5,
            user_id=None,
            is_admin=False,
        ) == []
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_product_repository_update_delete_get_or_create_and_scalar_none():
    engine, session = _build_session()
    try:
        user = _create_user(session, email="owner@example.com")
        product_type = _create_product_type(session, key_name="suspensao", friendly_name="Suspensao")
        _create_attribute_template(session, product_type_id=product_type.id, attribute_key="material")
        repo = ProductRepository(session)
        product = _create_product(
            session,
            user_id=user.id,
            nome_base="Amortecedor",
            sku="AM-1",
            product_type_id=product_type.id,
        )

        updated = repo.update_produto(
            db_produto=product,
            produto_update=_PayloadWithDump(
                {
                    "nome_base": "Amortecedor Atualizado",
                    "imagens_secundarias_urls": '["/a.png","/b.png"]',
                    "dados_brutos_web": '{"seo":"ok"}',
                }
            ),
        )
        assert updated.nome_base == "Amortecedor Atualizado"
        assert updated.imagens_secundarias_urls == ["/a.png", "/b.png"]
        assert updated.dados_brutos_web == {"seo": "ok"}
        assert updated.product_type.attribute_templates[0].attribute_key == "material"

        reused = repo.get_or_create_produto(
            produto=schemas.ProdutoCreate(nome_base="Amortecedor Reusado", sku="AM-1"),
            user_id=user.id,
        )
        assert reused.id == product.id
        assert reused.nome_base == "Amortecedor Reusado"

        reused_by_ean = repo.get_or_create_produto(
            produto=schemas.ProdutoCreate(nome_base="Amortecedor via EAN", ean="2222222222222"),
            user_id=user.id,
        )
        assert reused_by_ean.id != product.id

        created = repo.get_or_create_produto(
            produto=schemas.ProdutoCreate(nome_base="Atualiza via EAN", ean="2222222222222"),
            user_id=user.id,
        )
        assert created.id == reused_by_ean.id
        assert created.nome_base == "Atualiza via EAN"

        deleted = repo.delete_produto(db_produto=created)
        assert deleted.id == created.id
        assert repo.get_produto(produto_id=created.id) is None

        class _QueryStub:
            def filter(self, *_args, **_kwargs):
                return self

            def scalar(self):
                return None

        class _SessionStub:
            def query(self, *_args, **_kwargs):
                return _QueryStub()

        assert ProductRepository(_SessionStub()).count_produtos_by_user(
            user_id=1,
            is_admin=True,
        ) == 0
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_product_repository_save_image_and_non_sqlite_lock_path(monkeypatch, tmp_path):
    class _LockedQuery:
        def __init__(self):
            self.locked = False

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return "plain"

        def with_for_update(self):
            self.locked = True
            return self

    class _SessionLockStub:
        def __init__(self):
            self.query_obj = _LockedQuery()

        def query(self, *_args, **_kwargs):
            return self.query_obj

        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    assert ProductRepository(_SessionLockStub()).get_produto_for_update(produto_id=1) == "plain"

    repo = ProductRepository(SimpleNamespace())
    relative_upload_dir = f"tmp_uploads_{tmp_path.name}"
    resolved_root = Path(product_repository_module.__file__).resolve().parents[2] / relative_upload_dir
    monkeypatch.setattr(product_repository_module.settings, "UPLOAD_DIRECTORY", relative_upload_dir, raising=False)
    monkeypatch.setattr(product_repository_module.uuid, "uuid4", lambda: SimpleNamespace(hex="arquivo-fixo"))

    try:
        saved_path = await repo.save_produto_image(
            produto_id=1,
            file=_UploadFileStub(filename="foto.png", content=b"png-data"),
        )
        assert saved_path == f"/{relative_upload_dir}/arquivo-fixo.png"
        assert (resolved_root / "arquivo-fixo.png").read_bytes() == b"png-data"

        with pytest.raises(ValueError):
            await repo.save_produto_image(produto_id=1, file=_UploadFileStub(filename=None))

        broken_file = _UploadFileStub(filename="falha.png", error=RuntimeError("disk full"))
        with pytest.raises(IOError):
            await repo.save_produto_image(produto_id=1, file=broken_file)
        assert broken_file.closed is True
    finally:
        shutil.rmtree(resolved_root, ignore_errors=True)

    absolute_repo = ProductRepository(SimpleNamespace())
    absolute_dir = tmp_path / "absolute-uploads"
    monkeypatch.setattr(product_repository_module.settings, "UPLOAD_DIRECTORY", str(absolute_dir), raising=False)
    monkeypatch.setattr(product_repository_module.uuid, "uuid4", lambda: SimpleNamespace(hex="arquivo-abs"))
    saved_absolute = await absolute_repo.save_produto_image(
        produto_id=1,
        file=_UploadFileStub(filename="foto.jpg", content=b"jpg-data"),
    )
    assert saved_absolute == f"/{absolute_dir.as_posix()}/arquivo-abs.jpg"
