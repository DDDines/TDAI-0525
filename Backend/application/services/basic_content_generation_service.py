"""Servicos de geracao basica de conteudo para modo sem IA externa."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from fastapi import HTTPException, status

from Backend.infrastructure.repositories.product_repository import ProductRepository


class BasicContentGenerationService:
    """Gera titulos e descricoes basicas usando apenas dados internos do produto."""

    _KEYWORD_STOPWORDS = {
        "com",
        "para",
        "sem",
        "dos",
        "das",
        "nos",
        "nas",
        "uma",
        "uns",
        "umas",
        "que",
        "por",
        "mais",
        "menos",
        "sobre",
        "produto",
        "produtos",
        "peca",
        "pecas",
        "item",
        "itens",
        "tecnica",
        "tecnicas",
        "ficha",
    }
    _COMPANY_TIMELINE_HINTS = (
        "iniciou suas atividades",
        "iniciou as atividades",
        "fundada em",
        "fundado em",
        "anos de mercado",
        "no mercado desde",
        "atuando desde",
        "historia da empresa",
    )
    _COMPANY_TIMELINE_PATTERN = re.compile(
        r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|iniciou\s+suas?\s+atividades(?:\s+no?\s+ano\s+de\s+(?:19|20)\d{2})?)\b",
        re.IGNORECASE,
    )
    _COMPANY_ENTITY_HINT_PATTERN = re.compile(
        r"\b(?:empresa|marca|fabricante|industria|loja|grupo|nos|nossa|historia|tradicao|mercado)\b",
        re.IGNORECASE,
    )

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

    @staticmethod
    def _coerce_list(value: Any) -> List[str]:
        """Normalize scalar/list payloads into a compact string list."""
        if isinstance(value, list):
            iterable = value
        elif value is None:
            iterable = []
        else:
            iterable = [value]
        normalized: List[str] = []
        for item in iterable:
            clean = " ".join(str(item or "").strip().split())
            if clean:
                normalized.append(clean)
        return normalized

    @staticmethod
    def _coerce_dict(value: Any) -> Dict[str, str]:
        """Normalize dict payload with string keys and values."""
        if not isinstance(value, dict):
            return {}
        parsed: Dict[str, str] = {}
        for key, raw_value in value.items():
            key_clean = " ".join(str(key or "").strip().split())
            value_clean = " ".join(str(raw_value or "").strip().split())
            if key_clean and value_clean:
                parsed[key_clean] = value_clean
        return parsed

    def _extract_keywords_from_texts(self, *, texts: List[str], limit: int = 8) -> List[str]:
        """Generate compact keyword hints from text snippets."""
        scores: Dict[str, int] = {}
        for text in texts:
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9./-]{2,}", text or ""):
                token_clean = token.strip(".,;:()[]{}<>\"'").lower()
                if len(token_clean) < 3:
                    continue
                if token_clean in self._KEYWORD_STOPWORDS:
                    continue
                if token_clean.startswith("http"):
                    continue
                if token_clean.isdigit() and len(token_clean) < 4:
                    continue
                scores[token_clean] = scores.get(token_clean, 0) + 1
        ranked = sorted(scores.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
        return [token for token, _ in ranked[:limit]]

    @classmethod
    def _looks_like_company_timeline_claim(cls, text: str) -> bool:
        """Detect company-history claims that should not be inferred from web snippets."""
        compact = " ".join(str(text or "").strip().split())
        if not compact:
            return False

        lowered = compact.lower()
        if any(hint in lowered for hint in cls._COMPANY_TIMELINE_HINTS):
            return True

        if not cls._COMPANY_TIMELINE_PATTERN.search(compact):
            return False

        return bool(cls._COMPANY_ENTITY_HINT_PATTERN.search(compact))

    @classmethod
    def _sanitize_description_context(cls, raw_text: Any) -> str:
        """Drop unsupported company timeline sentences from source descriptions."""
        text = " ".join(str(raw_text or "").strip().split())
        if not text:
            return ""

        chunks = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
        filtered_chunks: List[str] = []
        for chunk in chunks:
            normalized_chunk = " ".join(str(chunk or "").strip().split())
            if not normalized_chunk:
                continue
            if cls._looks_like_company_timeline_claim(normalized_chunk):
                continue
            filtered_chunks.append(normalized_chunk)

        if filtered_chunks:
            return " ".join(filtered_chunks).strip()
        return text

    def _extract_web_context(self, *, produto: Any) -> Dict[str, Any]:
        """Read normalized web enrichment context from dados_brutos_web."""
        raw = getattr(produto, "dados_brutos_web", None)
        if not isinstance(raw, dict):
            return {
                "nome": "",
                "descricao": "",
                "bullets": [],
                "keywords": [],
                "specs": {},
            }

        nome = self._normalize_space(
            raw.get("nome_sugerido_seo") or raw.get("nome")
        )
        descricao = self._normalize_space(
            raw.get("descricao_detalhada_seo")
            or raw.get("descricao_curta")
            or raw.get("texto_relevante_coletado")
        )
        bullets = self._coerce_list(raw.get("lista_caracteristicas_beneficios_bullets"))
        keywords = self._coerce_list(raw.get("palavras_chave_seo_relevantes_lista"))
        specs = self._coerce_dict(raw.get("especificacoes_tecnicas_dict"))

        if not descricao:
            fontes = raw.get("fontes_web_coletadas")
            if isinstance(fontes, list):
                desc_parts = []
                for source in fontes:
                    if not isinstance(source, dict):
                        continue
                    source_desc = self._normalize_space(source.get("descricao_curta"))
                    if source_desc and not self._looks_like_company_timeline_claim(source_desc):
                        desc_parts.append(source_desc)
                descricao = self._normalize_space(" ".join(desc_parts))

        descricao = self._sanitize_description_context(descricao)
        bullets = [
            item
            for item in bullets
            if not self._looks_like_company_timeline_claim(item)
        ]

        if not keywords:
            keywords = self._extract_keywords_from_texts(
                texts=[
                    nome,
                    descricao,
                    " ".join(bullets),
                    " ".join(f"{key} {value}" for key, value in specs.items()),
                ],
                limit=8,
            )

        return {
            "nome": nome,
            "descricao": descricao,
            "bullets": bullets[:6],
            "keywords": keywords[:8],
            "specs": specs,
        }

    def _ensure_minimum_title_candidates(
        self,
        *,
        candidates: List[str],
        produto: Any,
        minimum_count: int,
        web_context: Dict[str, Any],
    ) -> List[str]:
        """Ensure enough fallback titles for downstream generators."""
        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or self._normalize_space(
            web_context.get("nome")
        ) or "Produto"
        marca = self._normalize_space(getattr(produto, "marca", ""))
        sku = self._normalize_space(getattr(produto, "sku", ""))
        modelo = self._normalize_space(getattr(produto, "modelo", ""))
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )
        keyword_seed = self._coerce_list(web_context.get("keywords"))

        patterns = [
            self._normalize_space(" ".join(part for part in [nome_base, marca, sku] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria, sku] if part)),
            self._normalize_space(" ".join(part for part in [marca, nome_base, modelo] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, sku, "peca automotiva"] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria, modelo] if part)),
        ]
        for keyword in keyword_seed[:4]:
            patterns.append(
                self._normalize_space(" ".join(part for part in [nome_base, keyword, sku] if part))
            )

        combined = self._unique_keep_order([*candidates, *patterns])
        while len(combined) < minimum_count:
            option_index = len(combined) + 1
            combined.append(self._normalize_space(f"{nome_base} opcao {option_index}"))
            combined = self._unique_keep_order(combined)
        return combined

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
        web_context = self._extract_web_context(produto=produto)

        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or self._normalize_space(
            web_context.get("nome")
        )
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

        keywords = self._coerce_list(web_context.get("keywords"))
        specs = self._coerce_dict(web_context.get("specs"))
        nome_web = self._normalize_space(web_context.get("nome"))

        candidates: List[str] = [
            self._normalize_space(" ".join(part for part in [marca, nome_base, modelo, sku] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, marca, ean] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria, sku] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, fornecedor_nome] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, modelo] if part)),
            self._normalize_space(" ".join(part for part in [nome_web, sku] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria, modelo] if part)),
        ]

        for keyword in keywords[:5]:
            candidates.append(
                self._normalize_space(" ".join(part for part in [nome_base, keyword, sku] if part))
            )
        for _, spec_value in list(specs.items())[:4]:
            candidates.append(
                self._normalize_space(" ".join(part for part in [nome_base, spec_value, sku] if part))
            )

        candidates = [item[:120] for item in self._unique_keep_order(candidates) if item]
        candidates = self._ensure_minimum_title_candidates(
            candidates=candidates,
            produto=produto,
            minimum_count=5,
            web_context=web_context,
        )
        if candidates:
            return candidates
        fallback = self._normalize_space(f"Produto {getattr(produto, 'id', '')}")
        return [fallback or "Produto"]

    def _build_basic_description(self, *, produto: Any, tamanho_palavras: int) -> str:
        """Compose a concise basic description from product and dynamic attributes."""
        web_context = self._extract_web_context(produto=produto)
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

        descricao_web = self._normalize_space(web_context.get("descricao"))
        if descricao_web:
            descricao = f"{descricao}\n\n{descricao_web}"

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

        web_specs = self._coerce_dict(web_context.get("specs"))
        if web_specs:
            specs.extend(
                [
                    f"{self._normalize_space(key)}: {self._normalize_space(value)}"
                    for key, value in list(web_specs.items())[:8]
                    if self._normalize_space(key) and self._normalize_space(value)
                ]
            )

        specs = self._unique_keep_order(specs)

        if specs:
            descricao = f"{descricao}\n\n" + "\n".join(specs)

        bullets = self._coerce_list(web_context.get("bullets"))
        if bullets:
            descricao = f"{descricao}\n\nDestaques:\n" + "\n".join(
                f"- {item}" for item in bullets[:5]
            )

        keywords = self._coerce_list(web_context.get("keywords"))
        if keywords:
            descricao = f"{descricao}\n\nPalavras-chave: {', '.join(keywords[:8])}"

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
        num_titulos: int = 5,
    ) -> List[str]:
        """Generate title suggestions without external IA providers."""
        _ = user
        produto = self._load_produto(session=session, produto_id=produto_id)
        candidates = self._build_title_candidates(produto=produto)
        max_titles = max(1, min(int(num_titulos or 5), 10))
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
