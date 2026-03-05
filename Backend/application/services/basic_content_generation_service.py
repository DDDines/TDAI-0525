"""Servicos de geracao basica de conteudo para modo sem IA externa."""

from __future__ import annotations

from typing import Any, List

from fastapi import HTTPException, status

from Backend.infrastructure.repositories.product_repository import ProductRepository


class BasicContentGenerationService:
    """Gera titulos e descricoes basicas usando apenas dados internos do produto."""

    def __init__(self, *, product_repository_factory: Any = ProductRepository) -> None:
        """Initialize injected dependencies and runtime configuration for Basic Content Generation Service."""
        self._product_repository_factory = product_repository_factory

    @staticmethod
    def _normalize_space(value: Any) -> str:
        """Normalize spacing and coerce arbitrary values to safe strings."""
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _unique_keep_order(values: List[str]) -> List[str]:
        """Deduplicate candidate values while preserving their original order."""
        seen = set()
        unique_values: List[str] = []
        for value in values:
            normalized = value.lower()
            if not value or normalized in seen:
                continue
            seen.add(normalized)
            unique_values.append(value)
        return unique_values

    def _load_produto(self, *, session: Any, produto_id: int) -> Any:
        """Load and validate product existence for basic content generation."""
        product_repository = self._product_repository_factory(session)
        produto = product_repository.get_produto(produto_id=produto_id)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado",
            )
        return produto

    def _build_title_candidates(self, *, produto: Any) -> List[str]:
        """Build title candidates from product identity and technical hints."""
        nome_base = self._normalize_space(getattr(produto, "nome_base", ""))
        marca = self._normalize_space(getattr(produto, "marca", ""))
        modelo = self._normalize_space(getattr(produto, "modelo", ""))
        sku = self._normalize_space(getattr(produto, "sku", ""))
        ean = self._normalize_space(getattr(produto, "ean", ""))
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )

        fornecedor_nome = ""
        fornecedor = getattr(produto, "fornecedor", None)
        if fornecedor is not None:
            fornecedor_nome = self._normalize_space(getattr(fornecedor, "nome", ""))

        candidates = [
            self._normalize_space(" ".join(part for part in [marca, nome_base, modelo, sku] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, marca, ean] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria, sku] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, fornecedor_nome] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, modelo] if part)),
        ]
        candidates = [item[:120] for item in self._unique_keep_order(candidates) if item]
        if candidates:
            return candidates
        fallback = self._normalize_space(f"Produto {getattr(produto, 'id', '')}")
        return [fallback or "Produto"]

    def _build_basic_description(self, *, produto: Any, tamanho_palavras: int) -> str:
        """Compose a concise basic description from product and dynamic attributes."""
        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or "Produto"
        marca = self._normalize_space(getattr(produto, "marca", ""))
        modelo = self._normalize_space(getattr(produto, "modelo", ""))
        sku = self._normalize_space(getattr(produto, "sku", ""))
        ean = self._normalize_space(getattr(produto, "ean", ""))
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )

        intro_parts = [nome_base]
        if marca:
            intro_parts.append(f"marca {marca}")
        if modelo:
            intro_parts.append(f"modelo {modelo}")
        if categoria:
            intro_parts.append(f"categoria {categoria}")
        descricao = f"{', '.join(intro_parts)}."

        specs: List[str] = []
        if sku:
            specs.append(f"SKU: {sku}")
        if ean:
            specs.append(f"EAN: {ean}")

        dynamic_attributes = getattr(produto, "dynamic_attributes", None)
        if isinstance(dynamic_attributes, dict):
            for key, value in dynamic_attributes.items():
                key_clean = self._normalize_space(key)
                value_clean = self._normalize_space(value)
                if key_clean and value_clean:
                    specs.append(f"{key_clean}: {value_clean}")
                if len(specs) >= 12:
                    break

        if specs:
            descricao = f"{descricao}\n\n" + "\n".join(specs)

        max_words = max(40, int(tamanho_palavras or 150))
        words = descricao.split()
        if len(words) <= max_words:
            return descricao
        return " ".join(words[:max_words]).strip() + "..."

    async def gerar_titulos_basicos(
        self,
        *,
        session: Any,
        produto_id: int,
        user: Any,
        num_titulos: int = 3,
    ) -> List[str]:
        """Generate title suggestions without external IA providers."""
        _ = user
        produto = self._load_produto(session=session, produto_id=produto_id)
        candidates = self._build_title_candidates(produto=produto)
        max_titles = max(1, min(int(num_titulos or 3), 10))
        return candidates[:max_titles]

    async def gerar_descricao_basica(
        self,
        *,
        session: Any,
        produto_id: int,
        user: Any,
        tamanho_palavras: int = 150,
    ) -> str:
        """Generate a basic product description without external IA providers."""
        _ = user
        produto = self._load_produto(session=session, produto_id=produto_id)
        return self._build_basic_description(
            produto=produto,
            tamanho_palavras=tamanho_palavras,
        )

