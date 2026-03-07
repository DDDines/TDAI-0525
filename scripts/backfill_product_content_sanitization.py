"""Backfill sanitation for previously generated/imported product content.

Default mode is dry-run. Use --apply to persist changes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend import models  # noqa: E402
from Backend.application.services.basic_content_generation_service import (  # noqa: E402
    BasicContentGenerationService,
)
from Backend.application.services.catalog_import_quality_service import (  # noqa: E402
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (  # noqa: E402
    CatalogImportSanitizationService,
)
from Backend.database import SessionLocal  # noqa: E402


class _TopLevelFunctionSurface:
    """Surface utilities to keep script flow explicit and testable."""

    _NOISY_IDENTITY_HINT_PATTERNS = (
        re.compile(r"\bacesse\s+noss[oa]\b", re.IGNORECASE),
        re.compile(r"\btodos?\s+os\s+produtos\b", re.IGNORECASE),
        re.compile(r"\bnao\s+se\s+esqueca\b", re.IGNORECASE),
        re.compile(r"\binstalad[oa]\b", re.IGNORECASE),
    )

    @staticmethod
    def _sanitize_identity(
        sanitizer: CatalogImportSanitizationService,
        value: Any,
        *,
        max_len: int,
    ) -> str | None:
        """Normalize + sanitize short identity fields with contact noise removal."""
        normalized = sanitizer._normalize_product_text(value)
        return sanitizer._sanitize_identity_text(
            normalized,
            max_len=max_len,
            cut_on_contact_marker=True,
        )

    @staticmethod
    def _sanitize_description(
        sanitizer: CatalogImportSanitizationService,
        value: Any,
        *,
        max_len: int = 12000,
    ) -> str | None:
        """Normalize + sanitize long description text."""
        normalized = sanitizer._normalize_product_text(value)
        return sanitizer._sanitize_description_text(normalized, max_len=max_len)

    @classmethod
    def _looks_like_noisy_identity_label(cls, value: Any) -> bool:
        """Detect placeholder/promotional strings that should not remain as product names."""
        text = BasicContentGenerationService._normalize_space(value)
        if not text:
            return False

        folded = BasicContentGenerationService._fold_text(text).lower()
        if any(pattern.search(folded) for pattern in cls._NOISY_IDENTITY_HINT_PATTERNS):
            return True
        return BasicContentGenerationService._looks_like_promotional_boilerplate(text)

    @staticmethod
    def _sanitize_title_candidate(value: Any, *, max_len: int = 160) -> str:
        """Reuse basic-generation sanitation to clean title-like values."""
        candidate = BasicContentGenerationService._sanitize_title_fragment(
            value,
            cut_on_contact_marker=True,
            max_len=max_len,
        )
        if not candidate:
            return ""
        if BasicContentGenerationService._is_noisy_title_fragment(candidate):
            return ""
        return candidate

    @staticmethod
    def _looks_like_noisy_generated_title(value: Any) -> bool:
        """Detect legacy generated titles that still carry weak/promotional suffixes."""
        candidate = _TopLevelFunctionSurface._sanitize_title_candidate(value, max_len=160)
        if not candidate:
            return True

        tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                BasicContentGenerationService._fold_text(candidate).lower(),
            )
            if len(token) >= 3
        ]
        if not tokens:
            return True
        return any(BasicContentGenerationService._is_weak_keyword(token) for token in tokens)

    @classmethod
    def _normalize_title_list(cls, value: Any, *, max_titles: int = 10) -> List[str]:
        """Normalize title payloads into a compact, deduplicated list."""
        if isinstance(value, list):
            raw_items = value
        elif value is None:
            raw_items = []
        else:
            raw_items = [value]
        cleaned: List[str] = []
        seen = set()
        for item in raw_items:
            candidate = _TopLevelFunctionSurface._sanitize_title_candidate(item, max_len=160)
            if not candidate:
                continue
            if cls._looks_like_noisy_generated_title(candidate):
                continue
            folded = candidate.lower()
            if folded in seen:
                continue
            seen.add(folded)
            cleaned.append(candidate)
            if len(cleaned) >= max_titles:
                break
        return cleaned

    @staticmethod
    def _rebuild_titles_from_product(
        produto: Any,
        *,
        basic_generation_service: BasicContentGenerationService,
        max_titles: int = 5,
    ) -> List[str]:
        """Regenerate deterministic title suggestions using the current basic generator rules."""
        web_context = basic_generation_service._extract_web_context(produto=produto)
        candidates = basic_generation_service._build_title_candidates(
            produto=produto,
            web_context=web_context,
        )
        candidates = basic_generation_service._ensure_minimum_title_candidates(
            candidates=candidates,
            produto=produto,
            minimum_count=max_titles,
            web_context=web_context,
        )
        return candidates[:max_titles]

    @staticmethod
    def _generated_description_is_noisy(value: Any) -> bool:
        """Detect generated descriptions still polluted by support/policy/store boilerplate."""
        text = BasicContentGenerationService._normalize_space(value)
        if not text:
            return False
        if BasicContentGenerationService._looks_like_promotional_boilerplate(text):
            return True

        chunks = re.split(r"(?<=[.!?;])\s+|[\r\n]+|;\s*", text)
        return any(
            BasicContentGenerationService._looks_like_promotional_boilerplate(chunk)
            for chunk in chunks
            if str(chunk or "").strip()
        )

    @staticmethod
    def _rebuild_generated_description(
        produto: Any,
        *,
        basic_generation_service: BasicContentGenerationService,
        tamanho_palavras: int = 150,
    ) -> str:
        """Rebuild generated description using the current deterministic basic generator."""
        template = basic_generation_service._safe_template(
            None,
            default_template=basic_generation_service._DEFAULT_DESCRIPTION_TEMPLATE,
        )
        return basic_generation_service._build_basic_description(
            produto=produto,
            tamanho_palavras=tamanho_palavras,
            template_descricao=template,
        )

    @staticmethod
    def _sanitize_keywords(value: Any) -> List[str]:
        """Clean keyword lists keeping only meaningful SEO hints."""
        if isinstance(value, list):
            raw_items = value
        elif value is None:
            raw_items = []
        else:
            raw_items = [value]
        cleaned: List[str] = []
        seen = set()
        for item in raw_items:
            candidate = _TopLevelFunctionSurface._sanitize_title_candidate(item, max_len=60)
            if not candidate:
                continue
            folded = candidate.lower()
            if folded in seen:
                continue
            seen.add(folded)
            cleaned.append(candidate)
            if len(cleaned) >= 12:
                break
        return cleaned

    @staticmethod
    def _sanitize_bullets(
        sanitizer: CatalogImportSanitizationService,
        value: Any,
    ) -> List[str]:
        """Clean bullet lists removing contact/institutional snippets."""
        if isinstance(value, list):
            raw_items = value
        elif value is None:
            raw_items = []
        else:
            raw_items = [value]
        cleaned: List[str] = []
        seen = set()
        for item in raw_items:
            bullet = _TopLevelFunctionSurface._sanitize_description(
                sanitizer,
                item,
                max_len=280,
            )
            if not bullet:
                continue
            folded = bullet.lower()
            if folded in seen:
                continue
            seen.add(folded)
            cleaned.append(bullet)
            if len(cleaned) >= 12:
                break
        return cleaned

    @staticmethod
    def _sanitize_source_list(
        sanitizer: CatalogImportSanitizationService,
        value: Any,
    ) -> List[Dict[str, Any]]:
        """Sanitize source metadata list stored in dados_brutos_web."""
        if not isinstance(value, list):
            return []
        cleaned_items: List[Dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            current = dict(item)
            name_clean = _TopLevelFunctionSurface._sanitize_identity(
                sanitizer,
                current.get("nome"),
                max_len=160,
            )
            desc_clean = _TopLevelFunctionSurface._sanitize_description(
                sanitizer,
                current.get("descricao_curta"),
                max_len=320,
            )
            if name_clean is not None:
                current["nome"] = name_clean
            if desc_clean is not None:
                current["descricao_curta"] = desc_clean
            cleaned_items.append(current)
            if len(cleaned_items) >= 20:
                break
        return cleaned_items

    @staticmethod
    def _sanitize_product_payload(
        produto: models.Produto,
        *,
        sanitizer: CatalogImportSanitizationService,
        basic_generation_service: BasicContentGenerationService,
    ) -> Tuple[bool, Counter]:
        """Apply in-memory sanitation to one product, returning change flags."""
        changed = False
        field_counter: Counter = Counter()

        def _update_attr(attr: str, new_value: Any, *, allow_none: bool = True) -> None:
            nonlocal changed
            old_value = getattr(produto, attr, None)
            if new_value is None and not allow_none:
                return
            if old_value == new_value:
                return
            setattr(produto, attr, new_value)
            changed = True
            field_counter[attr] += 1

        nome_base_clean = _TopLevelFunctionSurface._sanitize_identity(
            sanitizer,
            produto.nome_base,
            max_len=255,
        )
        if _TopLevelFunctionSurface._looks_like_noisy_identity_label(nome_base_clean):
            fallback_name = _TopLevelFunctionSurface._sanitize_identity(
                sanitizer,
                getattr(produto, "nome_chat_api", None),
                max_len=255,
            )
            nome_base_clean = fallback_name or f"Produto {getattr(produto, 'id', '')}".strip()
        _update_attr("nome_base", nome_base_clean, allow_none=False)

        nome_chat_clean = _TopLevelFunctionSurface._sanitize_identity(
            sanitizer,
            produto.nome_chat_api,
            max_len=255,
        )
        _update_attr("nome_chat_api", nome_chat_clean, allow_none=True)

        marca_clean = _TopLevelFunctionSurface._sanitize_identity(
            sanitizer,
            produto.marca,
            max_len=100,
        )
        _update_attr("marca", marca_clean, allow_none=True)

        modelo_clean = _TopLevelFunctionSurface._sanitize_identity(
            sanitizer,
            produto.modelo,
            max_len=100,
        )
        _update_attr("modelo", modelo_clean, allow_none=True)

        categoria_clean = _TopLevelFunctionSurface._sanitize_identity(
            sanitizer,
            produto.categoria_original,
            max_len=150,
        )
        _update_attr("categoria_original", categoria_clean, allow_none=True)

        descricao_original_clean = _TopLevelFunctionSurface._sanitize_description(
            sanitizer,
            produto.descricao_original,
            max_len=12000,
        )
        _update_attr("descricao_original", descricao_original_clean, allow_none=True)

        descricao_chat_clean = _TopLevelFunctionSurface._sanitize_description(
            sanitizer,
            produto.descricao_chat_api,
            max_len=12000,
        )
        _update_attr("descricao_chat_api", descricao_chat_clean, allow_none=True)

        raw = dict(produto.dados_brutos_web) if isinstance(produto.dados_brutos_web, dict) else {}
        if raw:
            raw_changed = False

            def _update_raw(key: str, new_value: Any) -> None:
                nonlocal raw_changed
                old_value = raw.get(key)
                if old_value == new_value:
                    return
                raw[key] = new_value
                raw_changed = True
                field_counter[f"dados_brutos_web.{key}"] += 1

            for key in ("nome", "nome_sugerido_seo"):
                clean_value = _TopLevelFunctionSurface._sanitize_identity(
                    sanitizer,
                    raw.get(key),
                    max_len=255,
                )
                if clean_value is not None:
                    _update_raw(key, clean_value)

            for key in ("descricao_curta", "descricao_detalhada_seo", "texto_relevante_coletado", "descricao_gerada"):
                clean_value = _TopLevelFunctionSurface._sanitize_description(
                    sanitizer,
                    raw.get(key),
                    max_len=12000,
                )
                if clean_value is not None:
                    _update_raw(key, clean_value)

            if "titulos_sugeridos_gerados" in raw:
                clean_titles = _TopLevelFunctionSurface._normalize_title_list(
                    raw.get("titulos_sugeridos_gerados"),
                    max_titles=10,
                )
                if not clean_titles:
                    clean_titles = _TopLevelFunctionSurface._rebuild_titles_from_product(
                        produto,
                        basic_generation_service=basic_generation_service,
                        max_titles=5,
                    )
                _update_raw("titulos_sugeridos_gerados", clean_titles)

            if "palavras_chave_seo_relevantes_lista" in raw:
                clean_keywords = _TopLevelFunctionSurface._sanitize_keywords(
                    raw.get("palavras_chave_seo_relevantes_lista")
                )
                _update_raw("palavras_chave_seo_relevantes_lista", clean_keywords)

            if "lista_caracteristicas_beneficios_bullets" in raw:
                clean_bullets = _TopLevelFunctionSurface._sanitize_bullets(
                    sanitizer,
                    raw.get("lista_caracteristicas_beneficios_bullets"),
                )
                _update_raw("lista_caracteristicas_beneficios_bullets", clean_bullets)

            if "fontes_web_coletadas" in raw:
                clean_sources = _TopLevelFunctionSurface._sanitize_source_list(
                    sanitizer,
                    raw.get("fontes_web_coletadas"),
                )
                _update_raw("fontes_web_coletadas", clean_sources)

            if raw_changed:
                _update_attr("dados_brutos_web", raw, allow_none=False)

        generated_description_candidates = [
            getattr(produto, "descricao_chat_api", None),
            raw.get("descricao_gerada") if isinstance(raw, dict) else None,
        ]
        if any(
            _TopLevelFunctionSurface._generated_description_is_noisy(value)
            for value in generated_description_candidates
            if value
        ):
            rebuilt_description = _TopLevelFunctionSurface._rebuild_generated_description(
                produto,
                basic_generation_service=basic_generation_service,
                tamanho_palavras=150,
            )
            if rebuilt_description:
                _update_attr("descricao_chat_api", rebuilt_description, allow_none=True)
                if isinstance(raw, dict) and raw.get("descricao_gerada") != rebuilt_description:
                    raw["descricao_gerada"] = rebuilt_description
                    field_counter["dados_brutos_web.descricao_gerada"] += 1
                    changed = True
                    _update_attr("dados_brutos_web", raw, allow_none=False)

        return changed, field_counter

    @staticmethod
    def run_backfill(
        *,
        apply_changes: bool,
        limit: int | None,
        user_id: int | None,
        produto_id: int | None,
        commit_every: int,
        verbose: bool,
    ) -> int:
        """Execute backfill workflow."""
        session = SessionLocal()
        sanitizer = CatalogImportSanitizationService(CatalogImportQualityService())
        basic_generation_service = BasicContentGenerationService()
        summary = Counter()
        field_summary = Counter()
        changed_since_commit = 0
        scanned_total = 0
        last_id = 0
        fetch_batch_size = 500

        try:
            while True:
                batch_query = (
                    session.query(models.Produto)
                    .filter(models.Produto.id > last_id)
                    .order_by(models.Produto.id.asc())
                )
                if user_id is not None:
                    batch_query = batch_query.filter(models.Produto.user_id == user_id)
                if produto_id is not None:
                    batch_query = batch_query.filter(models.Produto.id == produto_id)

                remaining = None
                if limit is not None and limit > 0:
                    remaining = max(0, limit - scanned_total)
                    if remaining == 0:
                        break
                    batch_query = batch_query.limit(min(fetch_batch_size, remaining))
                else:
                    batch_query = batch_query.limit(fetch_batch_size)

                produtos = batch_query.all()
                if not produtos:
                    break

                for produto in produtos:
                    summary["processed"] += 1
                    scanned_total += 1
                    changed, field_counter = _TopLevelFunctionSurface._sanitize_product_payload(
                        produto,
                        sanitizer=sanitizer,
                        basic_generation_service=basic_generation_service,
                    )
                    if changed:
                        summary["changed_products"] += 1
                        changed_since_commit += 1
                        field_summary.update(field_counter)
                        if verbose:
                            print(
                                f"[changed] produto_id={produto.id} "
                                f"fields={sorted(field_counter.keys())}"
                            )
                    else:
                        summary["unchanged_products"] += 1

                    if apply_changes and changed_since_commit >= max(1, commit_every):
                        session.commit()
                        changed_since_commit = 0

                last_id = produtos[-1].id
                if apply_changes and changed_since_commit > 0:
                    session.flush()
                session.expunge_all()

            if apply_changes:
                session.commit()
            else:
                session.rollback()

        finally:
            session.close()

        mode = "APPLY" if apply_changes else "DRY-RUN"
        print(f"\nBackfill mode: {mode}")
        print(f"Processed products: {summary['processed']}")
        print(f"Changed products: {summary['changed_products']}")
        print(f"Unchanged products: {summary['unchanged_products']}")
        if field_summary:
            print("\nChanged fields:")
            for field_name, count in field_summary.most_common():
                print(f"- {field_name}: {count}")
        else:
            print("\nNo field changes detected.")
        return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill sanitation for existing products (titles/descriptions/imported payload)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. Default is dry-run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of products to inspect.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Restrict backfill to one user_id.",
    )
    parser.add_argument(
        "--produto-id",
        type=int,
        default=None,
        help="Restrict backfill to one produto_id.",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=200,
        help="Commit batch size when --apply is used.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-product changes.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return _TopLevelFunctionSurface.run_backfill(
        apply_changes=bool(args.apply),
        limit=args.limit,
        user_id=args.user_id,
        produto_id=args.produto_id,
        commit_every=max(1, int(args.commit_every or 1)),
        verbose=bool(args.verbose),
    )


if __name__ == "__main__":
    raise SystemExit(main())
