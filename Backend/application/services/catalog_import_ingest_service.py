from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from Backend.application.services.repository_runtime_support import (
    call_repository_method,
)


class CatalogImportIngestService:
    """Encapsula a importacao direta de catalogo em servico OO."""

    def __init__(
        self,
        *,
        schemas: Any,
        models: Any,
        file_processing_service: Any,
        normalize_import_issue_item: Any,
        extract_import_error_reason: Any,
        is_non_critical_import_reason: Any,
        sanitize_produto_extraido: Any,
        classificar_qualidade_linha_produto: Any,
        json_module: Any,
        fornecedor_repo: Any | None = None,
        produto_repo: Any | None = None,
        uso_ia_repo: Any | None = None,
        historico_repo: Any | None = None,
    ) -> None:
        self._schemas = schemas
        self._models = models
        self._fornecedor_repo = fornecedor_repo
        self._produto_repo = produto_repo
        self._uso_ia_repo = uso_ia_repo
        self._historico_repo = historico_repo
        self._file_processing_service = file_processing_service
        self._normalize_import_issue_item = normalize_import_issue_item
        self._extract_import_error_reason = extract_import_error_reason
        self._is_non_critical_import_reason = is_non_critical_import_reason
        self._sanitize_produto_extraido = sanitize_produto_extraido
        self._classificar_qualidade_linha_produto = classificar_qualidade_linha_produto
        self._json = json_module

    @staticmethod
    def _repo_session(repo: Any) -> Any:
        return getattr(repo, "_db", None)

    @staticmethod
    def _resolve_repo(
        *,
        repo_name: str,
        configured_repo: Any,
        override_repo: Any | None,
    ) -> Any:
        repo = override_repo if override_repo is not None else configured_repo
        if repo is None:
            raise ValueError(f"{repo_name}_repo is required")
        if inspect.isclass(repo):
            raise ValueError(f"{repo_name}_repo instance is required")
        return repo

    async def importar_catalogo_fornecedor(
        self,
        *,
        fornecedor_id: int,
        file: Any,
        mapeamento_colunas_usuario: Optional[str],
        current_user: Any,
        fornecedor_repo: Any | None = None,
        produto_repo: Any | None = None,
        uso_ia_repo: Any | None = None,
        historico_repo: Any | None = None,
    ) -> Dict[str, Any]:
        """Importa arquivo de catalogo e cria/atualiza produtos do fornecedor."""
        resolved_fornecedor_repo = self._resolve_repo(
            repo_name="fornecedor",
            configured_repo=self._fornecedor_repo,
            override_repo=fornecedor_repo,
        )
        resolved_produto_repo = self._resolve_repo(
            repo_name="produto",
            configured_repo=self._produto_repo,
            override_repo=produto_repo,
        )
        resolved_uso_ia_repo = self._resolve_repo(
            repo_name="uso_ia",
            configured_repo=self._uso_ia_repo,
            override_repo=uso_ia_repo,
        )
        resolved_historico_repo = self._resolve_repo(
            repo_name="historico",
            configured_repo=self._historico_repo,
            override_repo=historico_repo,
        )

        content = await file.read()
        ext = Path(file.filename).suffix.lower()

        mapping_dict = self._resolve_mapping(
            fornecedor_id=fornecedor_id,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            fornecedor_repo=resolved_fornecedor_repo,
        )

        produtos_data = await self._process_file_by_extension(
            content=content,
            ext=ext,
            mapping_dict=mapping_dict,
        )

        produtos_create = []
        erros: List[Dict[str, Any]] = []
        quality_filter_enabled = ext == ".pdf"
        ignored_non_critical: List[Dict[str, Any]] = []
        quarantine_non_critical: List[Dict[str, Any]] = []

        def _append_import_issue(item: Dict[str, Any]) -> None:
            normalized_item = self._normalize_import_issue_item(item)
            reason = self._extract_import_error_reason(normalized_item)
            if self._is_non_critical_import_reason(reason):
                ignored_non_critical.append(normalized_item)
                return
            erros.append(normalized_item)

        def _append_quarantine_issue(item: Dict[str, Any]) -> None:
            normalized_item = self._normalize_import_issue_item(item)
            quarantine_non_critical.append(normalized_item)

        for prod in produtos_data:
            if isinstance(prod, dict) and (
                prod.get("motivo_descarte")
                or any(key.startswith("erro_processamento") for key in prod.keys())
            ):
                _append_import_issue(prod)
                continue

            cleaned_prod = self._sanitize_produto_extraido(prod)
            quality_eval = (
                self._classificar_qualidade_linha_produto(cleaned_prod)
                if quality_filter_enabled
                else {"decision": "accept", "score": 100, "reason": None}
            )
            if quality_eval.get("decision") == "discard":
                _append_import_issue(
                    {
                        "motivo_descarte": quality_eval.get("reason"),
                        "linha_original": prod,
                        "linha_sanitizada": cleaned_prod,
                        "qualidade_score": quality_eval.get("score"),
                    }
                )
                continue
            if quality_eval.get("decision") == "quarantine":
                _append_quarantine_issue(
                    {
                        "motivo_descarte": quality_eval.get("reason"),
                        "linha_original": prod,
                        "linha_sanitizada": cleaned_prod,
                        "qualidade_score": quality_eval.get("score"),
                        "classificacao": "quarentena",
                    }
                )
                continue

            try:
                produto_schema = self._schemas.ProdutoCreate(
                    nome_base=cleaned_prod.get("nome_base")
                    or cleaned_prod.get("sku_original")
                    or "Produto Importado",
                    sku=cleaned_prod.get("sku_original"),
                    ean=cleaned_prod.get("ean_original"),
                    descricao_original=cleaned_prod.get("descricao_original"),
                    marca=cleaned_prod.get("marca"),
                    categoria_original=cleaned_prod.get("categoria_original"),
                    dados_brutos_web=cleaned_prod.get("dados_brutos_adicionais")
                    or cleaned_prod.get("dados_brutos_web"),
                    dynamic_attributes=cleaned_prod.get("dynamic_attributes"),
                    fornecedor_id=fornecedor_id,
                )
                produtos_create.append(produto_schema)
            except Exception as exc:
                _append_import_issue(
                    {
                        "motivo_descarte": f"Erro ao converter linha: {exc}",
                        "linha_original": prod,
                        "linha_sanitizada": cleaned_prod,
                    }
                )

        created: List[Any] = []
        updated: List[Any] = []

        if produtos_create:
            created, updated, dup_errors = call_repository_method(
                resolved_produto_repo,
                "create_produtos_bulk",
                session=self._repo_session(resolved_produto_repo),
                produtos=produtos_create,
                arg_aliases={"produtos": ("produtos_data",)},
                user_id=current_user.id,
            )
            for err in dup_errors:
                _append_import_issue(err)

            for db_produto in created:
                call_repository_method(
                    resolved_uso_ia_repo,
                    "create_registro_uso_ia",
                    session=self._repo_session(resolved_uso_ia_repo),
                    registro_uso=self._schemas.RegistroUsoIACreate(
                        user_id=current_user.id,
                        produto_id=db_produto.id,
                        tipo_acao=self._models.TipoAcaoEnum.CRIACAO_PRODUTO,
                        creditos_consumidos=0,
                    ),
                    arg_aliases={"registro_uso": ("payload",)},
                )
                call_repository_method(
                    resolved_historico_repo,
                    "create_registro_historico",
                    session=self._repo_session(resolved_historico_repo),
                    registro_in=self._schemas.RegistroHistoricoCreate(
                        user_id=current_user.id,
                        entidade="Produto",
                        acao=self._models.TipoAcaoSistemaEnum.CRIACAO,
                        entity_id=db_produto.id,
                    ),
                    arg_aliases={"registro_in": ("payload",)},
                )

        all_issues = erros + ignored_non_critical + quarantine_non_critical
        return {
            "produtos_criados": created,
            "produtos_atualizados": updated,
            "erros": all_issues,
        }

    def _resolve_mapping(
        self,
        *,
        fornecedor_id: int,
        mapeamento_colunas_usuario: Optional[str],
        fornecedor_repo: Any,
    ) -> Optional[Dict[str, Any]]:
        mapping_dict = None
        if mapeamento_colunas_usuario:
            try:
                mapping_dict = self._json.loads(mapeamento_colunas_usuario)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail="mapeamento_colunas_usuario invalido",
                ) from exc
        else:
            fornecedor = call_repository_method(
                fornecedor_repo,
                "get_fornecedor",
                session=self._repo_session(fornecedor_repo),
                fornecedor_id=fornecedor_id,
            )
            if fornecedor and fornecedor.default_column_mapping:
                mapping_dict = fornecedor.default_column_mapping
        return mapping_dict

    async def _process_file_by_extension(
        self,
        *,
        content: bytes,
        ext: str,
        mapping_dict: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if ext in [".xlsx", ".xls"]:
            return await self._file_processing_service.processar_arquivo_excel(
                content,
                mapping_dict,
            )
        if ext == ".csv":
            return await self._file_processing_service.processar_arquivo_csv(
                content,
                mapping_dict,
            )
        if ext == ".pdf":
            return await self._file_processing_service.processar_arquivo_pdf(
                content,
                mapping_dict,
            )
        raise HTTPException(status_code=400, detail="Formato de arquivo nao suportado")
