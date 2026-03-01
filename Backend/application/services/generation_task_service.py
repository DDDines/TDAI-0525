from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session


class GenerationTaskService:
    """Servico OO para execucao de tarefas de geracao IA em background."""

    def __init__(
        self,
        *,
        models: Any,
        schemas: Any,
        logger: Any,
        db_session_factory: Any,
        user_repository_cls: Any,
        product_repository_cls: Any,
    ) -> None:
        self._db_session_factory = db_session_factory
        self._user_repository_cls = user_repository_cls
        self._product_repository_cls = product_repository_cls
        self._models = models
        self._schemas = schemas
        self._logger = logger

    def _get_user_access(self, session: Session) -> Any:
        return self._user_repository_cls(session)

    def _get_product_access(self, session: Session) -> Any:
        return self._product_repository_cls(session)

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
        user_id: int,
        produto_id: int,
        tipo_geracao_principal: str,
        funcao_geracao_ia_no_servico: Any,
        num_titulos: int | None = None,
        tamanho_palavras: int | None = None,
    ) -> None:
        """Executa geracao IA e persiste status/log no produto."""
        session: Optional[Session] = None
        db_produto: Optional[Any] = None
        status_field_to_update: Optional[str] = None
        campo_produto_para_atualizar_com_resultado: Optional[str] = None
        log_entry_prefix = f"IA {tipo_geracao_principal.capitalize()}"

        try:
            if self._db_session_factory is None:
                raise ValueError("db_session_factory is required for GenerationTaskService")
            session = self._db_session_factory()

            targets = self._resolve_generation_targets(tipo_geracao_principal)
            if targets is None:
                self._logger.error(
                    "Tarefa Background: Tipo de geracao principal '%s' desconhecido.",
                    tipo_geracao_principal,
                )
                return
            status_field_to_update, campo_produto_para_atualizar_com_resultado = targets

            user_access = self._get_user_access(session)
            product_access = self._get_product_access(session)

            user = user_access.get_user(user_id=user_id)
            if not user:
                self._logger.error(
                    "Tarefa Background %s: Usuario %s nao encontrado.",
                    log_entry_prefix,
                    user_id,
                )
                return

            db_produto = product_access.get_produto(produto_id=produto_id)
            if not db_produto:
                self._logger.error(
                    "Tarefa Background %s: Produto %s nao encontrado.",
                    log_entry_prefix,
                    produto_id,
                )
                return

            if db_produto.user_id != user.id and not user.is_superuser:
                self._logger.warning(
                    "Tarefa Background %s: Usuario %s nao autorizado para produto %s.",
                    log_entry_prefix,
                    user_id,
                    produto_id,
                )
                return

            update_data_progresso = {
                status_field_to_update: self._models.StatusGeracaoIAEnum.EM_PROGRESSO,
                "log_processamento": self._append_process_log(
                    db_produto.log_processamento,
                    f"{log_entry_prefix}: Geracao iniciada.",
                ),
            }
            product_access.update_produto(
                db_produto=db_produto,
                produto_update=self._schemas.ProdutoUpdate(**update_data_progresso),
            )

            self._logger.info(
                "Tarefa Background %s: Chamando servico IA para produto %s.",
                log_entry_prefix,
                produto_id,
            )
            llm_call_payload: Dict[str, Any] = {
                "session": session,
                "produto_id": produto_id,
                "user": user,
            }
            if num_titulos is not None:
                llm_call_payload["num_titulos"] = num_titulos
            if tamanho_palavras is not None:
                llm_call_payload["tamanho_palavras"] = tamanho_palavras

            resultado_ia = await funcao_geracao_ia_no_servico(**llm_call_payload)
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
                update_data_final_dict[campo_produto_para_atualizar_com_resultado] = resultado_ia
                update_data_final_dict[status_field_to_update] = self._models.StatusGeracaoIAEnum.CONCLUIDO
                update_data_final_dict["log_processamento"] = self._append_process_log(
                    db_produto.log_processamento,
                    f"{log_entry_prefix}: Geracao concluida com sucesso.",
                )
            else:
                update_data_final_dict[status_field_to_update] = self._models.StatusGeracaoIAEnum.FALHA
                update_data_final_dict["log_processamento"] = self._append_process_log(
                    db_produto.log_processamento,
                    (
                        f"{log_entry_prefix}: Falha na geracao "
                        "(resultado vazio ou IA nao pode gerar)."
                    ),
                )
                self._logger.warning(
                    "Tarefa Background %s: IA nao retornou resultado valido para produto %s.",
                    log_entry_prefix,
                    produto_id,
                )

            product_access.update_produto(
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
                product_access = self._get_product_access(session)
                product_access.update_produto(
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
                        f"{log_entry_prefix}: Erro critico inesperado - {exc}",
                    ),
                }
                product_access = self._get_product_access(session)
                product_access.update_produto(
                    db_produto=db_produto,
                    produto_update=self._schemas.ProdutoUpdate(**update_data_falha_critica),
                )
        finally:
            self._logger.info(
                "Tarefa Background %s: Finalizando para produto ID: %s",
                log_entry_prefix,
                produto_id,
            )
            if session:
                session.close()
