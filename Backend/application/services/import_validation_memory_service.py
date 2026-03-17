"""Import validation memory service — learns from user review decisions to automate future imports."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select


class ImportValidationMemoryService:
    """Applies learned validation rules and persists user review decisions."""

    def __init__(self, *, db: Any, models: Any, schemas: Any, product_store: Any = None) -> None:
        """Initialize injected dependencies and runtime configuration for Import Validation Memory Service."""
        self._db = db
        self._models = models
        self._schemas = schemas
        self._product_store = product_store

    # ------------------------------------------------------------------
    # Rule resolution
    # ------------------------------------------------------------------

    def _get_rules(self, *, user_id: int, fornecedor_id: Optional[int]) -> List[Any]:
        """Load active rules for the user, matching this supplier (or global)."""
        Rule = self._models.ImportValidationRule
        stmt = select(Rule).where(Rule.user_id == user_id)
        if fornecedor_id is not None:
            stmt = stmt.where(
                (Rule.fornecedor_id == fornecedor_id) | (Rule.fornecedor_id.is_(None))
            )
        return list(self._db.execute(stmt).scalars().all())

    def should_auto_accept(
        self,
        *,
        quality_score: Optional[float],
        user_id: int,
        fornecedor_id: Optional[int],
    ) -> bool:
        """Return True if a learned rule would auto-accept a product with this score."""
        rules = self._get_rules(user_id=user_id, fornecedor_id=fornecedor_id)
        for rule in rules:
            if rule.action != "accept":
                continue
            if rule.min_quality_score is not None:
                if quality_score is not None and quality_score >= rule.min_quality_score:
                    rule.times_applied = (rule.times_applied or 0) + 1
                    self._db.flush()
                    return True
            else:
                rule.times_applied = (rule.times_applied or 0) + 1
                self._db.flush()
                return True
        return False

    # ------------------------------------------------------------------
    # Rule persistence
    # ------------------------------------------------------------------

    def save_acceptance_rule(
        self,
        *,
        user_id: int,
        fornecedor_id: Optional[int],
        min_quality_score: Optional[float],
    ) -> None:
        """Save or update an accept rule for this user+supplier combination."""
        Rule = self._models.ImportValidationRule
        stmt = select(Rule).where(
            Rule.user_id == user_id,
            Rule.fornecedor_id == fornecedor_id,
            Rule.action == "accept",
        )
        existing = self._db.execute(stmt).scalars().first()
        if existing:
            existing.min_quality_score = min_quality_score
            self._db.flush()
        else:
            rule = Rule(
                user_id=user_id,
                fornecedor_id=fornecedor_id,
                action="accept",
                min_quality_score=min_quality_score,
                rule_type="quality_threshold",
            )
            self._db.add(rule)
            self._db.flush()

    # ------------------------------------------------------------------
    # Quarantine review: approve a single item
    # ------------------------------------------------------------------

    def get_quarantine_items(self, *, catalog_file: Any) -> List[Dict[str, Any]]:
        """Return the list of quarantined products from the catalog file result_summary."""
        summary = catalog_file.result_summary or {}
        items = summary.get("quarantine_non_critical") or []
        return list(items) if isinstance(items, list) else []

    def approve_item(
        self,
        *,
        catalog_file: Any,
        item_index: int,
        current_user: Any,
        remember: bool = False,
        min_quality_score: Optional[float] = None,
    ) -> Optional[Any]:
        """Approve a quarantined item, create the product and optionally save a rule."""
        items = self.get_quarantine_items(catalog_file=catalog_file)
        if not (0 <= item_index < len(items)):
            return None

        item = items[item_index]
        cleaned = item.get("linha_sanitizada") or item.get("linha_validada") or item.get("linha_original") or {}
        if not cleaned or not isinstance(cleaned, dict):
            return None

        nome_base = cleaned.get("nome_base") or cleaned.get("sku_original") or "Produto Importado"
        produto_schema = self._schemas.ProdutoCreate(
            nome_base=nome_base,
            sku=cleaned.get("sku_original"),
            ean=cleaned.get("ean_original"),
            descricao_original=cleaned.get("descricao_original"),
            marca=cleaned.get("marca"),
            categoria_original=cleaned.get("categoria_original"),
            dados_brutos_web=cleaned.get("dados_brutos_adicionais") or cleaned.get("dados_brutos_web"),
            dynamic_attributes=cleaned.get("dynamic_attributes"),
            fornecedor_id=catalog_file.fornecedor_id,
            import_quality_score=item.get("qualidade_score"),
        )

        db_produto = self._product_store.create_produto(
            produto=produto_schema,
            user_id=current_user.id,
        )

        if remember and catalog_file.fornecedor_id:
            self.save_acceptance_rule(
                user_id=current_user.id,
                fornecedor_id=catalog_file.fornecedor_id,
                min_quality_score=min_quality_score,
            )

        return db_produto

    def list_rules(self, *, user_id: int) -> List[Any]:
        """List all validation rules for the given user."""
        Rule = self._models.ImportValidationRule
        stmt = select(Rule).where(Rule.user_id == user_id).order_by(Rule.created_at.desc())
        return list(self._db.execute(stmt).scalars().all())

    def delete_rule(self, *, rule_id: int, user_id: int) -> bool:
        """Delete a rule owned by the user. Returns True if deleted."""
        Rule = self._models.ImportValidationRule
        stmt = select(Rule).where(Rule.id == rule_id, Rule.user_id == user_id)
        rule = self._db.execute(stmt).scalars().first()
        if not rule:
            return False
        self._db.delete(rule)
        self._db.flush()
        return True
