"""Tests for ImportValidationMemoryService — covers rule resolution, quarantine review, and rule persistence."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from Backend.application.services.import_validation_memory_service import ImportValidationMemoryService

_SELECT_TARGET = "Backend.application.services.import_validation_memory_service.select"


def _make_rule(*, action="accept", min_quality_score=None, fornecedor_id=None, user_id=1, rule_id=10):
    """Build a minimal rule SimpleNamespace."""
    return SimpleNamespace(
        id=rule_id,
        action=action,
        min_quality_score=min_quality_score,
        fornecedor_id=fornecedor_id,
        user_id=user_id,
        times_applied=0,
    )


def _make_db_with_rules(rules):
    """Build a minimal DB stub that returns the given rules from execute().scalars().all()."""
    scalars_stub = MagicMock()
    scalars_stub.all.return_value = rules
    scalars_stub.first.return_value = rules[0] if rules else None

    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_stub

    db = MagicMock()
    db.execute.return_value = execute_result
    return db


def _make_models():
    """Build a minimal models namespace with a fake ImportValidationRule class."""
    class FakeRule:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        user_id = MagicMock()
        fornecedor_id = MagicMock()
        action = None
        min_quality_score = None
        times_applied = 0
        id = None
        created_at = MagicMock()

    return SimpleNamespace(ImportValidationRule=FakeRule)


class _TopLevelFunctionSurface:
    """Centralize all ImportValidationMemoryService test functions as static methods."""

    def test_should_auto_accept_sem_regras_retorna_false():
        """With an empty rules list, should_auto_accept returns False."""
        db = _make_db_with_rules([])
        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            result = svc.should_auto_accept(quality_score=80.0, user_id=1, fornecedor_id=None)

        assert result is False

    def test_should_auto_accept_com_regra_sem_score_retorna_true():
        """Rule with action=accept and min_quality_score=None always returns True."""
        rule = _make_rule(action="accept", min_quality_score=None)
        db = _make_db_with_rules([rule])
        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            result = svc.should_auto_accept(quality_score=10.0, user_id=1, fornecedor_id=None)

        assert result is True

    def test_should_auto_accept_com_regra_score_suficiente_retorna_true():
        """Rule with min_quality_score=60.0 and quality_score=80.0 returns True."""
        rule = _make_rule(action="accept", min_quality_score=60.0)
        db = _make_db_with_rules([rule])
        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            result = svc.should_auto_accept(quality_score=80.0, user_id=1, fornecedor_id=None)

        assert result is True

    def test_should_auto_accept_com_regra_score_insuficiente_retorna_false():
        """Rule with min_quality_score=60 and quality_score=40 returns False."""
        rule = _make_rule(action="accept", min_quality_score=60.0)
        db = _make_db_with_rules([rule])
        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            result = svc.should_auto_accept(quality_score=40.0, user_id=1, fornecedor_id=None)

        assert result is False

    def test_get_quarantine_items_retorna_lista_do_result_summary():
        """get_quarantine_items returns the quarantine_non_critical list from result_summary."""
        quarantine_items = [{"nome_base": "X", "qualidade_score": 55.0}]
        catalog_file = SimpleNamespace(
            result_summary={"quarantine_non_critical": quarantine_items}
        )
        db = MagicMock()
        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        result = svc.get_quarantine_items(catalog_file=catalog_file)

        assert result == quarantine_items

    def test_approve_item_cria_produto():
        """approve_item calls product_store.create_produto with the correct data."""
        item = {
            "linha_sanitizada": {
                "nome_base": "Produto Aprovado",
                "sku_original": "SKU-001",
            },
            "qualidade_score": 70.0,
        }
        catalog_file = SimpleNamespace(
            result_summary={"quarantine_non_critical": [item]},
            fornecedor_id=5,
        )
        current_user = SimpleNamespace(id=1)

        class FakeProdutoCreate:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_produto_db = SimpleNamespace(id=99)
        product_store = MagicMock()
        product_store.create_produto.return_value = fake_produto_db

        db = MagicMock()
        models = _make_models()
        schemas = SimpleNamespace(ProdutoCreate=FakeProdutoCreate)

        svc = ImportValidationMemoryService(
            db=db, models=models, schemas=schemas, product_store=product_store
        )
        result = svc.approve_item(
            catalog_file=catalog_file,
            item_index=0,
            current_user=current_user,
            remember=False,
        )

        assert result is fake_produto_db
        product_store.create_produto.assert_called_once()
        call_kwargs = product_store.create_produto.call_args
        assert call_kwargs.kwargs["user_id"] == 1

    def test_approve_item_indice_invalido_retorna_none():
        """approve_item with an out-of-range index returns None."""
        catalog_file = SimpleNamespace(
            result_summary={"quarantine_non_critical": []},
            fornecedor_id=5,
        )
        current_user = SimpleNamespace(id=1)
        db = MagicMock()
        models = _make_models()
        schemas = SimpleNamespace()
        product_store = MagicMock()

        svc = ImportValidationMemoryService(
            db=db, models=models, schemas=schemas, product_store=product_store
        )
        result = svc.approve_item(
            catalog_file=catalog_file,
            item_index=5,
            current_user=current_user,
        )

        assert result is None

    def test_save_acceptance_rule_cria_nova_regra():
        """save_acceptance_rule creates a new rule when none exists."""
        # Simulate no existing rule
        scalars_stub = MagicMock()
        scalars_stub.first.return_value = None
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_stub

        added = []

        db = MagicMock()
        db.execute.return_value = execute_result
        db.add.side_effect = lambda obj: added.append(obj)

        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            svc.save_acceptance_rule(user_id=1, fornecedor_id=5, min_quality_score=50.0)

        assert len(added) == 1
        assert added[0].action == "accept"
        assert added[0].min_quality_score == 50.0
        db.flush.assert_called()

    def test_delete_rule_existente_retorna_true():
        """delete_rule returns True when the rule is found and deleted."""
        rule = _make_rule(rule_id=10, user_id=1)
        scalars_stub = MagicMock()
        scalars_stub.first.return_value = rule
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_stub

        db = MagicMock()
        db.execute.return_value = execute_result

        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            result = svc.delete_rule(rule_id=10, user_id=1)

        assert result is True
        db.delete.assert_called_once_with(rule)
        db.flush.assert_called()

    def test_delete_rule_inexistente_retorna_false():
        """delete_rule returns False when the rule is not found."""
        scalars_stub = MagicMock()
        scalars_stub.first.return_value = None
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_stub

        db = MagicMock()
        db.execute.return_value = execute_result

        models = _make_models()
        schemas = SimpleNamespace()

        svc = ImportValidationMemoryService(db=db, models=models, schemas=schemas)
        with patch(_SELECT_TARGET):
            result = svc.delete_rule(rule_id=999, user_id=1)

        assert result is False
        db.delete.assert_not_called()


test_should_auto_accept_sem_regras_retorna_false = _TopLevelFunctionSurface.test_should_auto_accept_sem_regras_retorna_false
test_should_auto_accept_com_regra_sem_score_retorna_true = _TopLevelFunctionSurface.test_should_auto_accept_com_regra_sem_score_retorna_true
test_should_auto_accept_com_regra_score_suficiente_retorna_true = _TopLevelFunctionSurface.test_should_auto_accept_com_regra_score_suficiente_retorna_true
test_should_auto_accept_com_regra_score_insuficiente_retorna_false = _TopLevelFunctionSurface.test_should_auto_accept_com_regra_score_insuficiente_retorna_false
test_get_quarantine_items_retorna_lista_do_result_summary = _TopLevelFunctionSurface.test_get_quarantine_items_retorna_lista_do_result_summary
test_approve_item_cria_produto = _TopLevelFunctionSurface.test_approve_item_cria_produto
test_approve_item_indice_invalido_retorna_none = _TopLevelFunctionSurface.test_approve_item_indice_invalido_retorna_none
test_save_acceptance_rule_cria_nova_regra = _TopLevelFunctionSurface.test_save_acceptance_rule_cria_nova_regra
test_delete_rule_existente_retorna_true = _TopLevelFunctionSurface.test_delete_rule_existente_retorna_true
test_delete_rule_inexistente_retorna_false = _TopLevelFunctionSurface.test_delete_rule_inexistente_retorna_false
