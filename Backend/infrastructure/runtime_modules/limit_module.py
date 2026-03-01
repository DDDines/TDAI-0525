from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from Backend import models
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository


class _LimitRuntime:
    """Runtime OO para regras de limite e credito."""

    def __init__(
        self,
        *,
        uso_ia_workflow=None,
        user_workflow=None,
        logger_factory=get_logger,
        crud_module=None,
        crud_users_module=None,
    ) -> None:
        # Backward-compatible constructor names while migration tests settle.
        self._uso_ia_workflow = uso_ia_workflow or crud_module
        self._user_workflow = user_workflow or crud_users_module
        self._logger = logger_factory(__name__)

    @staticmethod
    def _resolve_uso_ia_accessor(uso_ia_workflow, db: Session):
        if uso_ia_workflow is None:
            return RegistroUsoIARepository(db)
        if callable(uso_ia_workflow):
            return uso_ia_workflow(db)
        return uso_ia_workflow

    @staticmethod
    def _call_count_by_prefix(uso_ia_accessor, db: Session, *, user_id: int, tipo_geracao_prefix: str):
        method = uso_ia_accessor.count_usos_ia_by_user_and_type_no_mes_corrente
        try:
            return method(user_id=user_id, tipo_geracao_prefix=tipo_geracao_prefix)
        except TypeError:
            return method(db, user_id=user_id, tipo_geracao_prefix=tipo_geracao_prefix)

    @staticmethod
    def _call_count_monthly(uso_ia_accessor, db: Session, *, user_id: int):
        method = uso_ia_accessor.get_geracoes_ia_count_no_mes_corrente
        try:
            return method(user_id=user_id)
        except TypeError:
            return method(db, user_id=user_id)

    @staticmethod
    def _resolve_user_accessor(user_workflow, db: Session):
        if user_workflow is None:
            return UserRepository(db)
        if callable(user_workflow):
            return user_workflow(db)
        return user_workflow

    @staticmethod
    def _call_get_user(user_accessor, db: Session, *, user_id: int):
        method = user_accessor.get_user
        try:
            return method(user_id=user_id)
        except TypeError:
            return method(db, user_id=user_id)

    def verificar_limite_uso(
        self,
        db: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Valida limite mensal de geracao e retorna saldo restante.

        Retorna ``-1`` quando o usuario possui uso ilimitado.
        Lanca ``HTTPException`` quando o limite ja foi atingido.
        """

        if not user.plano:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Funcionalidade nao disponivel. Usuario nao possui "
                    "plano de assinatura ativo ou configurado."
                ),
            )

        if tipo_geracao_principal not in {"descricao", "titulo"}:
            self._logger.warning(
                "Tentativa de verificar limite para tipo de geracao desconhecido: %s",
                tipo_geracao_principal,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Tipo de geracao '{tipo_geracao_principal}' nao e valido "
                    "para verificacao de limite."
                ),
            )

        limite_mensal = user.plano.limite_geracao_ia
        if limite_mensal is None or limite_mensal <= 0:
            self._logger.info(
                "Usuario %s possui geracao ilimitada para %s.",
                user.id,
                tipo_geracao_principal,
            )
            return -1

        uso_ia_accessor = self._resolve_uso_ia_accessor(self._uso_ia_workflow, db)
        usos_no_mes = self._call_count_by_prefix(
            uso_ia_accessor,
            db,
            user_id=user.id,
            tipo_geracao_prefix=tipo_geracao_principal,
        )
        remaining = limite_mensal - usos_no_mes

        if remaining <= 0:
            if tipo_geracao_principal == "descricao":
                mensagem_limite = (
                    f"Limite mensal de {limite_mensal} descrições atingido. "
                    f"Você utilizou {usos_no_mes} e não possui descrições restantes."
                )
            else:
                mensagem_limite = (
                    f"Limite mensal de {limite_mensal} títulos atingido. "
                    f"Você utilizou {usos_no_mes} e não possui títulos restantes."
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=mensagem_limite,
            )

        self._logger.info(
            "Verificacao de limite para usuario %s (%s): %s/%s usos (%s restantes).",
            user.id,
            tipo_geracao_principal,
            usos_no_mes,
            limite_mensal,
            remaining,
        )
        return remaining

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        db: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Verifica se o usuario possui credito mensal disponivel para IA."""

        user_accessor = self._resolve_user_accessor(self._user_workflow, db)
        user = self._call_get_user(user_accessor, db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario nao encontrado",
            )

        limite_mensal = user.limite_geracao_ia
        if limite_mensal in (None, 0) and user.plano:
            limite_mensal = user.plano.limite_geracao_ia

        if limite_mensal is None or limite_mensal <= 0:
            return True

        uso_ia_accessor = self._resolve_uso_ia_accessor(self._uso_ia_workflow, db)
        usos_no_mes = self._call_count_monthly(
            uso_ia_accessor,
            db,
            user_id=user_id,
        )
        return usos_no_mes + creditos_necessarios <= limite_mensal

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        db: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Valida disponibilidade de credito; consumo e registrado por uso."""

        return await self.verificar_creditos_disponiveis_geracao_ia(
            db=db,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )


class _LimitWorkflow:
    """Workflow OO para regras de limite e credito."""

    def __init__(self, runtime: Optional[_LimitRuntime] = None) -> None:
        self._runtime = runtime or _LimitRuntime(
            uso_ia_workflow=lambda db: RegistroUsoIARepository(db),
            user_workflow=lambda db: UserRepository(db),
            logger_factory=get_logger,
        )

    def verificar_limite_uso(
        self,
        db: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        return self._runtime.verificar_limite_uso(
            db=db,
            user=user,
            tipo_geracao_principal=tipo_geracao_principal,
        )

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        db: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        return await self._runtime.verificar_creditos_disponiveis_geracao_ia(
            db=db,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        db: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        return await self._runtime.verificar_e_consumir_creditos_geracao_ia(
            db=db,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )


LimitWorkflow = _LimitWorkflow




