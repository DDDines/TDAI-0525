"""Camada de transporte HTTP para o dominio 'workspace' (empresa/company)."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.logging_config import get_logger
from Backend.core.rate_limiter import limiter
from . import auth_utils

router = APIRouter()
logger = get_logger(__name__)


class WorkspaceRequestService:
    """Servico request-scoped para operacoes de workspace."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        self._db = session

    def get_company_by_id(self, company_id: int) -> models.Company | None:
        return self._db.query(models.Company).filter(models.Company.id == company_id).first()

    def get_user_company(self, user: models.User) -> models.Company | None:
        if not user.company_id:
            return None
        return self.get_company_by_id(user.company_id)

    def create_company(self, user: models.User, data: schemas.CompanyCreate) -> models.Company:
        if user.company_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Voce ja pertence a uma empresa. Saia dela antes de criar uma nova.",
            )
        if data.cnpj:
            existing = self._db.query(models.Company).filter(models.Company.cnpj == data.cnpj).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ja existe uma empresa cadastrada com este CNPJ.",
                )
        company = models.Company(
            nome=data.nome,
            cnpj=data.cnpj or None,
            criado_por_user_id=user.id,
        )
        self._db.add(company)
        self._db.flush()  # get company.id before committing
        user.company_id = company.id
        self._db.commit()
        self._db.refresh(company)
        return company

    def update_company(self, user: models.User, data: schemas.CompanyUpdate) -> models.Company:
        company = self.get_user_company(user)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
        if company.criado_por_user_id != user.id and not user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas o criador da empresa pode editar os dados.")
        if data.nome is not None:
            company.nome = data.nome
        if data.cnpj is not None:
            if data.cnpj:
                existing = self._db.query(models.Company).filter(
                    models.Company.cnpj == data.cnpj,
                    models.Company.id != company.id,
                ).first()
                if existing:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CNPJ ja em uso por outra empresa.")
            company.cnpj = data.cnpj or None
        self._db.commit()
        self._db.refresh(company)
        return company

    def leave_company(self, user: models.User) -> None:
        if not user.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
        user.company_id = None
        self._db.commit()

    def get_members(self, user: models.User) -> List[models.User]:
        company = self.get_user_company(user)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
        return self._db.query(models.User).filter(models.User.company_id == company.id).all()

    def create_invite(self, user: models.User, email: str) -> models.WorkspaceInvite:
        company = self.get_user_company(user)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
        if company.criado_por_user_id != user.id and not user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas o criador da empresa pode convidar membros.")
        # Check if email is already a member
        existing_member = self._db.query(models.User).filter(
            models.User.email == email,
            models.User.company_id == company.id,
        ).first()
        if existing_member:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este email ja e membro da empresa.")
        # Check for pending invite
        pending = self._db.query(models.WorkspaceInvite).filter(
            models.WorkspaceInvite.company_id == company.id,
            models.WorkspaceInvite.email == email,
            models.WorkspaceInvite.accepted_at.is_(None),
            models.WorkspaceInvite.expires_at > datetime.now(timezone.utc),
        ).first()
        if pending:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe um convite pendente para este email.")
        invite = models.WorkspaceInvite(
            company_id=company.id,
            email=email,
            token=secrets.token_urlsafe(32),
            created_by_user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self._db.add(invite)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def list_invites(self, user: models.User) -> List[models.WorkspaceInvite]:
        company = self.get_user_company(user)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
        return self._db.query(models.WorkspaceInvite).filter(
            models.WorkspaceInvite.company_id == company.id,
            models.WorkspaceInvite.accepted_at.is_(None),
            models.WorkspaceInvite.expires_at > datetime.now(timezone.utc),
        ).order_by(models.WorkspaceInvite.created_at.desc()).all()

    def accept_invite(self, token: str, user: models.User) -> models.WorkspaceInvite:
        invite = self._db.query(models.WorkspaceInvite).filter(
            models.WorkspaceInvite.token == token,
        ).first()
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convite invalido ou expirado.")
        if invite.accepted_at is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este convite ja foi aceito.")
        if invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Este convite expirou.")
        if user.company_id and user.company_id != invite.company_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Voce ja pertence a outra empresa.")
        user.company_id = invite.company_id
        invite.accepted_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def revoke_invite(self, invite_id: int, user: models.User) -> None:
        company = self.get_user_company(user)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
        invite = self._db.query(models.WorkspaceInvite).filter(
            models.WorkspaceInvite.id == invite_id,
            models.WorkspaceInvite.company_id == company.id,
        ).first()
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convite nao encontrado.")
        self._db.delete(invite)
        self._db.commit()


@router.get(
    "/workspace/",
    response_model=schemas.CompanyResponse,
    summary="Retorna a empresa atual do usuario",
)
async def get_workspace(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    company = request_service.get_user_company(current_user)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce nao pertence a nenhuma empresa.")
    return company


@router.post(
    "/workspace/",
    response_model=schemas.CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova empresa e adiciona o usuario como membro",
)
async def create_workspace(
    data: schemas.CompanyCreate,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    return request_service.create_company(user=current_user, data=data)


@router.patch(
    "/workspace/",
    response_model=schemas.CompanyResponse,
    summary="Atualiza dados da empresa (apenas criador)",
)
async def update_workspace(
    data: schemas.CompanyUpdate,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    return request_service.update_company(user=current_user, data=data)


@router.delete(
    "/workspace/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove o usuario da empresa atual",
)
async def leave_workspace(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    request_service.leave_company(user=current_user)


@router.get(
    "/workspace/members/",
    response_model=List[schemas.CompanyMemberResponse],
    summary="Lista membros da empresa atual",
)
async def get_workspace_members(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    return request_service.get_members(current_user)


@router.post(
    "/workspace/invite",
    response_model=schemas.WorkspaceInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um convite para um email entrar na empresa",
)
@limiter.limit("10/minute")
async def create_invite(
    request: Request,
    data: schemas.WorkspaceInviteCreate,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    return request_service.create_invite(user=current_user, email=data.email)


@router.get(
    "/workspace/invites",
    response_model=List[schemas.WorkspaceInviteResponse],
    summary="Lista convites pendentes da empresa",
)
async def list_invites(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    return request_service.list_invites(current_user)


@router.post(
    "/workspace/accept-invite/{token}",
    response_model=schemas.WorkspaceInviteResponse,
    summary="Aceita um convite pelo token (usuario deve estar logado)",
)
async def accept_invite(
    token: str,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    return request_service.accept_invite(token=token, user=current_user)


@router.delete(
    "/workspace/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga um convite pendente",
)
async def revoke_invite(
    invite_id: int,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    request_service: WorkspaceRequestService = Depends(),
):
    request_service.revoke_invite(invite_id=invite_id, user=current_user)
