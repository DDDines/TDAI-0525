from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from Backend import crud, crud_users, models
from Backend.core.logging_config import get_logger


class _LimitRuntime:
    """Runtime OO para regras de limite e credito."""

    def __init__(self, *, crud_module, crud_users_module, logger_factory) -> None:
        self._crud = crud_module
        self._crud_users = crud_users_module
        self._logger = logger_factory(__name__)

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

        usos_no_mes = self._crud.count_usos_ia_by_user_and_type_no_mes_corrente(
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

        user = self._crud_users.get_user(db, user_id=user_id)
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

        usos_no_mes = self._crud.get_geracoes_ia_count_no_mes_corrente(db, user_id=user_id)
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

    def __init__(self, runtime: _LimitRuntime) -> None:
        self._runtime = runtime

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


_limit_runtime = _LimitRuntime(
    crud_module=crud,
    crud_users_module=crud_users,
    logger_factory=get_logger,
)
_limit_workflow = _LimitWorkflow(_limit_runtime)


def verificar_limite_uso(
    db: Session,
    user: models.User,
    tipo_geracao_principal: str,
) -> int:
    return _limit_workflow.verificar_limite_uso(
        db=db,
        user=user,
        tipo_geracao_principal=tipo_geracao_principal,
    )


async def verificar_creditos_disponiveis_geracao_ia(
    db: Session,
    user_id: int,
    creditos_necessarios: int = 1,
) -> bool:
    return await _limit_workflow.verificar_creditos_disponiveis_geracao_ia(
        db=db,
        user_id=user_id,
        creditos_necessarios=creditos_necessarios,
    )


async def verificar_e_consumir_creditos_geracao_ia(
    db: Session,
    user_id: int,
    creditos_necessarios: int = 1,
) -> bool:
    return await _limit_workflow.verificar_e_consumir_creditos_geracao_ia(
        db=db,
        user_id=user_id,
        creditos_necessarios=creditos_necessarios,
    )


class LimitServiceLegacyService:
    """Camada de compatibilidade para chamadas legadas."""

    def verificar_limite_uso(self, *args, **kwargs):
        return verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args, **kwargs):
        return await verificar_creditos_disponiveis_geracao_ia(*args, **kwargs)

    async def verificar_e_consumir_creditos_geracao_ia(self, *args, **kwargs):
        return await verificar_e_consumir_creditos_geracao_ia(*args, **kwargs)


limit_service_legacy_service = LimitServiceLegacyService()
