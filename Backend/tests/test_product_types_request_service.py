"""Behavioral tests for product type request service error handling and permissions."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import models, schemas
from Backend.routers.product_types import ProductTypesRequestService, ReorderRequest


class _FakeProductTypeRepo:
    """Fake product type repository for request service tests."""

    def __init__(self):
        self.calls = []
        self.by_id = {}
        self.by_key = {}
        self.attribute_by_id = {}
        self.attribute_by_key = {}
        self.reorder_result = None
        self.created = None
        self.deleted = None
        self.updated = None

    def get_product_type_by_key_name(self, *, key_name, user_id=None):
        self.calls.append(("get_product_type_by_key_name", key_name, user_id))
        return self.by_key.get((key_name, user_id))

    def create_product_type(self, *, product_type_create, user_id=None):
        self.calls.append(("create_product_type", product_type_create.key_name, user_id))
        self.created = SimpleNamespace(id=91, user_id=user_id, key_name=product_type_create.key_name)
        return self.created

    def get_product_type(self, *, product_type_id):
        self.calls.append(("get_product_type", product_type_id))
        return self.by_id.get(product_type_id)

    def update_product_type(self, *, db_product_type, product_type_update):
        self.calls.append(("update_product_type", db_product_type.id))
        self.updated = SimpleNamespace(id=db_product_type.id, **product_type_update.model_dump(exclude_unset=True))
        return self.updated

    def delete_product_type(self, *, db_product_type):
        self.calls.append(("delete_product_type", db_product_type.id))
        self.deleted = db_product_type
        return db_product_type

    def get_attribute_template(self, *, attribute_template_id):
        self.calls.append(("get_attribute_template", attribute_template_id))
        return self.attribute_by_id.get(attribute_template_id)

    def get_attribute_template_by_key(self, *, product_type_id, attribute_key, exclude_attribute_id=None):
        self.calls.append(("get_attribute_template_by_key", product_type_id, attribute_key, exclude_attribute_id))
        return self.attribute_by_key.get((product_type_id, attribute_key, exclude_attribute_id))

    def create_attribute_template(self, *, attr_template_create, product_type_id):
        self.calls.append(("create_attribute_template", product_type_id, attr_template_create.attribute_key))
        return SimpleNamespace(id=701, product_type_id=product_type_id, **attr_template_create.model_dump())

    def update_attribute_template(self, *, db_attr_template, attr_template_update):
        self.calls.append(("update_attribute_template", db_attr_template.id))
        return SimpleNamespace(id=db_attr_template.id, product_type_id=db_attr_template.product_type_id, **attr_template_update.model_dump(exclude_unset=True))

    def delete_attribute_template(self, *, db_attr_template):
        self.calls.append(("delete_attribute_template", db_attr_template.id))
        return db_attr_template

    def reorder_attribute_template(self, *, attribute_id, direction):
        self.calls.append(("reorder_attribute_template", attribute_id, direction))
        return self.reorder_result


class _FakeHistoricoRepo:
    """Fake historico repository for request service tests."""

    def __init__(self):
        self.entries = []

    def create_registro_historico(self, *, registro_in):
        self.entries.append(registro_in)
        return registro_in


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""

    @staticmethod
    def _build_service():
        service = ProductTypesRequestService(session="db")
        service._product_type_repo = _FakeProductTypeRepo()
        service._historico_repo = _FakeHistoricoRepo()
        return service

    @staticmethod
    def test_create_product_type_rejects_duplicate_scope():
        """Reject creation when the key already exists in the visible scope."""
        service = _TopLevelFunctionSurface._build_service()
        service._product_type_repo.by_key[("pesados", 7)] = SimpleNamespace(id=11, user_id=7)
        current_user = SimpleNamespace(id=7, is_superuser=False)

        with pytest.raises(HTTPException) as exc_info:
            service.create_product_type(
                product_type_in=schemas.ProductTypeCreate(key_name="pesados", friendly_name="Pesados"),
                current_user=current_user,
            )

        assert exc_info.value.status_code == 400
        assert "ja existe" in exc_info.value.detail.lower()

    @staticmethod
    @pytest.mark.asyncio
    async def test_read_product_type_details_falls_back_to_global_key():
        """Return a global product type when no user-specific key exists."""
        service = _TopLevelFunctionSurface._build_service()
        global_type = SimpleNamespace(id=31, key_name="freios", user_id=None)
        service._product_type_repo.by_key[("freios", None)] = global_type
        current_user = SimpleNamespace(id=9, is_superuser=False)

        result = await service.read_product_type_details(identifier="freios", current_user=current_user)

        assert result is global_type

    @staticmethod
    @pytest.mark.asyncio
    async def test_read_product_type_details_rejects_access_from_other_user():
        """Reject reading a private type owned by another user."""
        service = _TopLevelFunctionSurface._build_service()
        private_type = SimpleNamespace(id=41, key_name="privado", user_id=22)
        service._product_type_repo.by_id[41] = private_type
        current_user = SimpleNamespace(id=9, is_superuser=False)

        with pytest.raises(HTTPException) as exc_info:
            await service.read_product_type_details(identifier="41", current_user=current_user)

        assert exc_info.value.status_code == 403

    @staticmethod
    def test_add_attribute_rejects_duplicate_key():
        """Reject duplicate attribute keys inside one product type."""
        service = _TopLevelFunctionSurface._build_service()
        service._product_type_repo.attribute_by_key[(55, "material", None)] = SimpleNamespace(id=88)

        with pytest.raises(HTTPException) as exc_info:
            service.add_attribute_to_product_type(
                type_id=55,
                attribute_in=schemas.AttributeTemplateCreate(
                    attribute_key="material",
                    label="Material",
                    field_type=models.AttributeFieldTypeEnum.TEXT,
                ),
            )

        assert exc_info.value.status_code == 400

    @staticmethod
    def test_update_attribute_rejects_mismatched_type():
        """Reject updating an attribute that does not belong to the target type."""
        service = _TopLevelFunctionSurface._build_service()
        service._product_type_repo.attribute_by_id[10] = SimpleNamespace(id=10, product_type_id=99, attribute_key="cor")

        with pytest.raises(HTTPException) as exc_info:
            service.update_attribute_for_product_type(
                type_id=55,
                attribute_id=10,
                attribute_in=schemas.AttributeTemplateUpdate(label="Cor Principal"),
            )

        assert exc_info.value.status_code == 404

    @staticmethod
    def test_remove_attribute_rejects_missing_resource():
        """Reject removing an attribute that does not exist in the type."""
        service = _TopLevelFunctionSurface._build_service()

        with pytest.raises(HTTPException) as exc_info:
            service.remove_attribute_from_product_type(type_id=55, attribute_id=999)

        assert exc_info.value.status_code == 404

    @staticmethod
    def test_reorder_attribute_requires_owner_or_superuser():
        """Reject reorder attempts from users that do not own the type."""
        service = _TopLevelFunctionSurface._build_service()
        service._product_type_repo.by_id[55] = SimpleNamespace(id=55, user_id=200)
        current_user = SimpleNamespace(id=7, is_superuser=False)

        with pytest.raises(HTTPException) as exc_info:
            service.reorder_attribute(
                type_id=55,
                attribute_id=11,
                reorder_request=ReorderRequest(direction="up"),
                current_user=current_user,
            )

        assert exc_info.value.status_code == 403

    @staticmethod
    def test_reorder_attribute_returns_not_found_when_repository_cannot_move():
        """Translate invalid moves into a 404 API response."""
        service = _TopLevelFunctionSurface._build_service()
        service._product_type_repo.by_id[55] = SimpleNamespace(id=55, user_id=7)
        current_user = SimpleNamespace(id=7, is_superuser=False)

        with pytest.raises(HTTPException) as exc_info:
            service.reorder_attribute(
                type_id=55,
                attribute_id=11,
                reorder_request=ReorderRequest(direction="down"),
                current_user=current_user,
            )

        assert exc_info.value.status_code == 404


test_create_product_type_rejects_duplicate_scope = (
    _TopLevelFunctionSurface.test_create_product_type_rejects_duplicate_scope
)
test_read_product_type_details_falls_back_to_global_key = (
    _TopLevelFunctionSurface.test_read_product_type_details_falls_back_to_global_key
)
test_read_product_type_details_rejects_access_from_other_user = (
    _TopLevelFunctionSurface.test_read_product_type_details_rejects_access_from_other_user
)
test_add_attribute_rejects_duplicate_key = (
    _TopLevelFunctionSurface.test_add_attribute_rejects_duplicate_key
)
test_update_attribute_rejects_mismatched_type = (
    _TopLevelFunctionSurface.test_update_attribute_rejects_mismatched_type
)
test_remove_attribute_rejects_missing_resource = (
    _TopLevelFunctionSurface.test_remove_attribute_rejects_missing_resource
)
test_reorder_attribute_requires_owner_or_superuser = (
    _TopLevelFunctionSurface.test_reorder_attribute_requires_owner_or_superuser
)
test_reorder_attribute_returns_not_found_when_repository_cannot_move = (
    _TopLevelFunctionSurface.test_reorder_attribute_returns_not_found_when_repository_cannot_move
)
