"""Limit module.

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from Backend import models
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository


class LimitRuntime:
    """Runtime OO para regras de limite e credito."""

    def __init__(
        self,
        *,
        usage_repository_factory: Callable[[Session], Any] = RegistroUsoIARepository,
        user_repository_factory: Callable[[Session], Any] = UserRepository,
        logger_factory=get_logger,
    ) -> None:
        """Initialize dependencies for LimitRuntime."""
        self._usage_repository_factory = usage_repository_factory
        self._user_repository_factory = user_repository_factory
        self._logger = logger_factory(__name__)

    def _usage_repository(self, db: Session):
        """Usage repository."""
        return self._usage_repository_factory(db)

    def _user_repository(self, db: Session):
        """User repository."""
        return self._user_repository_factory(db)

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

        uso_ia_repo = self._usage_repository(db)
        usos_no_mes = uso_ia_repo.count_usos_ia_by_user_and_type_no_mes_corrente(
            user_id=user.id,
            tipo_geracao_prefix=tipo_geracao_principal,
        )
        remaining = limite_mensal - usos_no_mes

        if remaining <= 0:
            if tipo_geracao_principal == "descricao":
                mensagem_limite = (
                    f"Limite mensal de {limite_mensal} descricoes atingido. "
                    f"Voce utilizou {usos_no_mes} e nao possui descricoes restantes."
                )
            else:
                mensagem_limite = (
                    f"Limite mensal de {limite_mensal} titulos atingido. "
                    f"Voce utilizou {usos_no_mes} e nao possui titulos restantes."
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

        user = self._user_repository(db).get_user(user_id=user_id)
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

        uso_ia_repo = self._usage_repository(db)
        usos_no_mes = uso_ia_repo.get_geracoes_ia_count_no_mes_corrente(user_id=user_id)
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


class LimitWorkflow:
    """Workflow OO para regras de limite e credito."""

    def __init__(self, runtime: Optional[LimitRuntime] = None) -> None:
        """Initialize dependencies for LimitWorkflow."""
        self._runtime = runtime or LimitRuntime(
            usage_repository_factory=RegistroUsoIARepository,
            user_repository_factory=UserRepository,
            logger_factory=get_logger,
        )

    def verificar_limite_uso(
        self,
        db: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Verificar limite uso."""
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
        """Verificar creditos disponiveis geracao ia."""
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
        """Verificar e consumir creditos geracao ia."""
        return await self._runtime.verificar_e_consumir_creditos_geracao_ia(
            db=db,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )
