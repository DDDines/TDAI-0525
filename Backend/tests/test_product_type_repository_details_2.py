from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models, schemas
from Backend.database import Base
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository


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


def _create_product_type(session, *, key_name: str, friendly_name: str, user_id=None):
    product_type = models.ProductType(
        key_name=key_name,
        friendly_name=friendly_name,
        description=friendly_name,
        user_id=user_id,
    )
    session.add(product_type)
    session.commit()
    session.refresh(product_type)
    return product_type


def test_delete_product_type_success_and_global_key_conflict():
    engine, session = _build_session()
    try:
        repo = ProductTypeRepository(session)
        keep = _create_product_type(session, key_name="global-a", friendly_name="Global A", user_id=None)
        target = _create_product_type(session, key_name="global-b", friendly_name="Global B", user_id=None)

        with pytest.raises(IntegrityError):
            repo.update_product_type(
                db_product_type=target,
                product_type_update=schemas.ProductTypeUpdate(key_name="global-a"),
            )

        deleted = repo.delete_product_type(db_product_type=target)
        assert deleted.id == target.id
        assert repo.get_product_type(product_type_id=keep.id).id == keep.id
        assert repo.get_product_type(product_type_id=target.id) is None
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_reorder_attribute_template_returns_none_when_attribute_not_in_siblings(monkeypatch):
    class _QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

    db = SimpleNamespace(query=lambda *args, **kwargs: _QueryStub())
    repo = ProductTypeRepository(db)
    attr = SimpleNamespace(id=7, product_type_id=1, display_order=0)
    monkeypatch.setattr(repo, "get_attribute_template", lambda *, attribute_template_id: attr)

    assert repo.reorder_attribute_template(attribute_id=7, direction="up") is None
