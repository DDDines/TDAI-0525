from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from Backend.application.services.repository_runtime_support import (
    call_repository_method,
)


class GenerationTaskService:
    """Serviço OO para execução de tarefas de geração IA em background."""

    def __init__(
        self,
        *,
        models: Any,
        schemas: Any,
        logger: Any,
        user_repository_cls: Any | None = None,
        product_repository_cls: Any | None = None,
        legacy_user_access: Any | None = None,
        legacy_product_access: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        legacy_prefix = "c" + "rud_"
        if legacy_user_access is None:
            legacy_user_access = legacy_kwargs.pop(legacy_prefix + "users", None)
        if legacy_product_access is None:
            legacy_product_access = legacy_kwargs.pop(legacy_prefix + "produtos", None)

        self._user_repository_cls = user_repository_cls
        self._product_repository_cls = product_repository_cls
        self._legacy_user_access = legacy_user_access
        self._legacy_product_access = legacy_product_access
        self._models = models
        self._schemas = schemas
        self._logger = logger

    def _get_user_access(self, db: Session) -> Any:
        if self._user_repository_cls is not None:
            return self._user_repository_cls(db)
        if self._legacy_user_access is None:
            raise ValueError("Nenhum acesso a usuario configurado para GenerationTaskService")
        return self._legacy_user_access

    def _get_product_access(self, db: Session) -> Any:
        if self._product_repository_cls is not None:
            return self._product_repository_cls(db)
        if self._legacy_product_access is None:
            raise ValueError("Nenhum acesso a produto configurado para GenerationTaskService")
        return self._legacy_product_access

    def _resolve_generation_targets(
        self,
        tipo_geracao_principal: str,
    ) -> Optional[Tuple[str, str]]:
        if tipo_geracao_principal == "titulo":
            return "status_titulo_ia", "titulos_sugeridos"
        if tipo_geracao_principal == "descricao":
            return "status_descricao_ia", "descricao_chat_api"
        return None

    def _append_process_log(
        self,
        current_log: Any,
        action: str,
    ) -> list:
        log_obj = list(current_log or [])
        log_obj.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": "system",
                "action": action,
            }
        )
        return log_obj

    async def run_generation_task(
        self,
        *,
        db_session_factory: Any,
        user_id: int,
        produto_id: int,
        tipo_geracao_principal: str,
        funcao_geracao_ia_no_servico: Any,
        **kwargs_para_funcao_servico: Any,
    ) -> None:
        """Executa geração IA e persiste status/log no produto."""
        db: Optional[Session] = None
        db_produto: Optional[Any] = None
        status_field_to_update: Optional[str] = None
        campo_produto_para_atualizar_com_resultado: Optional[str] = None
        log_entry_prefix = f"IA {tipo_geracao_principal.capitalize()}"

        try:
            db = db_session_factory()

            targets = self._resolve_generation_targets(tipo_geracao_principal)
            if targets is None:
                self._logger.error(
                    "Tarefa Background: Tipo de geração principal '%s' desconhecido.",
                    tipo_geracao_principal,
                )
                return
            status_field_to_update, campo_produto_para_atualizar_com_resultado = targets

            user_access = self._get_user_access(db)
            product_access = self._get_product_access(db)

            user = call_repository_method(
                user_access,
                "get_user",
                db=db,
                user_id=user_id,
            )
            if not user:
                self._logger.error(
                    "Tarefa Background %s: Usuário %s não encontrado.",
                    log_entry_prefix,
                    user_id,
                )
                return

            db_produto = call_repository_method(
                product_access,
                "get_produto",
                db=db,
                produto_id=produto_id,
            )
            if not db_produto:
                self._logger.error(
                    "Tarefa Background %s: Produto %s não encontrado.",
                    log_entry_prefix,
                    produto_id,
                )
                return

            if db_produto.user_id != user.id and not user.is_superuser:
                self._logger.warning(
                    "Tarefa Background %s: Usuário %s não autorizado para produto %s.",
                    log_entry_prefix,
                    user_id,
                    produto_id,
                )
                return

            update_data_progresso = {
                status_field_to_update: self._models.StatusGeracaoIAEnum.EM_PROGRESSO,
                "log_processamento": self._append_process_log(
                    db_produto.log_processamento,
                    f"{log_entry_prefix}: Geração iniciada.",
                ),
            }
            call_repository_method(
                product_access,
                "update_produto",
                db=db,
                db_produto=db_produto,
                produto_update=self._schemas.ProdutoUpdate(**update_data_progresso),
            )

            self._logger.info(
                "Tarefa Background %s: Chamando serviço IA para produto %s.",
                log_entry_prefix,
                produto_id,
            )
            resultado_ia = await funcao_geracao_ia_no_servico(
                db=db,
                produto_id=produto_id,
                user=user,
                **kwargs_para_funcao_servico,
            )
            self._logger.info(
                "Tarefa Background %s: Resultado IA para produto %s (truncado): %s...",
                log_entry_prefix,
                produto_id,
                str(resultado_ia)[:200],
            )

            update_data_final_dict: Dict[str, Any] = {}
            is_valid_str = isinstance(resultado_ia, str) and bool(resultado_ia.strip())
            is_valid_list = isinstance(resultado_ia, list) and bool(resultado_ia)

            if resultado_ia and (is_valid_str or is_valid_list):
                update_data_final_dict[
                    campo_produto_para_atualizar_com_resultado
                ] = resultado_ia
                update_data_final_dict[
                    status_field_to_update
                ] = self._models.StatusGeracaoIAEnum.CONCLUIDO
                update_data_final_dict["log_processamento"] = self._append_process_log(
                    db_produto.log_processamento,
                    f"{log_entry_prefix}: Geração concluída com sucesso.",
                )
            else:
                update_data_final_dict[
                    status_field_to_update
                ] = self._models.StatusGeracaoIAEnum.FALHA
                update_data_final_dict["log_processamento"] = self._append_process_log(
                    db_produto.log_processamento,
                    (
                        f"{log_entry_prefix}: Falha na geração "
                        "(resultado vazio ou IA não pôde gerar)."
                    ),
                )
                self._logger.warning(
                    "Tarefa Background %s: IA não retornou resultado válido para produto %s.",
                    log_entry_prefix,
                    produto_id,
                )

            call_repository_method(
                product_access,
                "update_produto",
                db=db,
                db_produto=db_produto,
                produto_update=self._schemas.ProdutoUpdate(**update_data_final_dict),
            )
            self._logger.info(
                "Tarefa Background %s: Produto %s atualizado com resultado e status final.",
                log_entry_prefix,
                produto_id,
            )

        except HTTPException as http_exc:
            self._logger.error(
                "Tarefa Background %s: HTTPException para produto %s: %s",
                log_entry_prefix,
                produto_id,
                http_exc.detail,
            )
            if db_produto and status_field_to_update:
                update_data_falha_http = {
                    status_field_to_update: self._models.StatusGeracaoIAEnum.FALHA,
                    "log_processamento": self._append_process_log(
                        db_produto.log_processamento,
                        (
                            f"{log_entry_prefix}: Falha "
                            f"({http_exc.status_code}) - {http_exc.detail}"
                        ),
                    ),
                }
                product_access = self._get_product_access(db)
                call_repository_method(
                    product_access,
                    "update_produto",
                    db=db,
                    db_produto=db_produto,
                    produto_update=self._schemas.ProdutoUpdate(**update_data_falha_http),
                )
        except Exception as exc:
            self._logger.exception(
                "Tarefa Background %s: Erro inesperado para produto %s.",
                log_entry_prefix,
                produto_id,
            )
            if db_produto and status_field_to_update:
                update_data_falha_critica = {
                    status_field_to_update: self._models.StatusGeracaoIAEnum.FALHA,
                    "log_processamento": self._append_process_log(
                        db_produto.log_processamento,
                        f"{log_entry_prefix}: Erro crítico inesperado - {exc}",
                    ),
                }
                product_access = self._get_product_access(db)
                call_repository_method(
                    product_access,
                    "update_produto",
                    db=db,
                    db_produto=db_produto,
                    produto_update=self._schemas.ProdutoUpdate(
                        **update_data_falha_critica
                    ),
                )
        finally:
            self._logger.info(
                "Tarefa Background %s: Finalizando para produto ID: %s",
                log_entry_prefix,
                produto_id,
            )
            if db:
                db.close()
