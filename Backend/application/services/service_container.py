"""Servicos de aplicacao e composicao de dependencias para 'service_container'."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from Backend import database, models, schemas
from Backend.application.services.fornecedor_management_service import (
    FornecedorManagementService,
)
from Backend.application.services.file_processing import FileProcessingOrchestratorService
from Backend.application.services.ia_generation_service import IAGenerationService
from Backend.application.services.limit_service import LimitService
from Backend.application.services.product_management_service import (
    ProductManagementService,
)
from Backend.application.services.product_media_service import ProductMediaService
from Backend.application.services.product_repositories import (
    build_product_management_repositories,
    build_product_media_repositories,
)
from Backend.application.services.web_data_extractor import (
    WebDataExtractorOrchestratorService,
)
from Backend.infrastructure.adapters.file_processing_adapter import (
    FileProcessingServiceAdapter,
)
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository


class _RequestScopedDependency:
    """Dependencia request-scoped OO parametrizada por factory de sessao."""

    def __init__(self, factory: Callable[[Session], Any]) -> None:
        self._factory = factory

    def __call__(
        self,
        session: Session = Depends(database.get_db),
    ) -> Any:
        return self._factory(session)


class ServiceContainerDependencySupport:
    """Helpers OO de DI para composicao request-scoped de servicos."""

    @staticmethod
    def get_request_db_session(session: Session = Depends(database.get_db)) -> Session:
        return session

    @staticmethod
    def build_request_scoped_dependency(
        factory: Callable[[Session], Any],
    ) -> Callable[[Session], Any]:
        return _RequestScopedDependency(factory)

    @staticmethod
    def build_file_processing_service() -> FileProcessingOrchestratorService:
        return FileProcessingOrchestratorService(FileProcessingServiceAdapter())

    @staticmethod
    def build_web_data_extractor_service() -> WebDataExtractorOrchestratorService:
        return WebDataExtractorOrchestratorService(WebDataExtractorServiceAdapter())


_get_request_db_session = ServiceContainerDependencySupport.get_request_db_session
build_request_scoped_dependency = ServiceContainerDependencySupport.build_request_scoped_dependency
_build_file_processing_service = ServiceContainerDependencySupport.build_file_processing_service
_build_web_data_extractor_service = ServiceContainerDependencySupport.build_web_data_extractor_service
SessionDep = Annotated[Session, Depends(_get_request_db_session)]


@dataclass
class ServiceContainer:
    """Registry simples de servicos OO compartilhados pela aplicacao."""

    file_processing: FileProcessingOrchestratorService = field(
        default_factory=_build_file_processing_service
    )
    web_data_extractor: WebDataExtractorOrchestratorService = field(
        default_factory=_build_web_data_extractor_service
    )
    ia_generation: IAGenerationService = field(default_factory=IAGenerationService)
    limit: LimitService = field(default_factory=LimitService)


class DependencyContainer:
    """Container de DI para dependencias request-scoped dos routers."""

    @staticmethod
    def get_db_session(session: Session = Depends(_get_request_db_session)) -> Session:
        return session

    @staticmethod
    def get_product_management_service(
        db: Session = Depends(get_db_session),
    ) -> ProductManagementService:
        repos = build_product_management_repositories(
            session=db,
        )
        return ProductManagementService(
            models=models,
            schemas=schemas,
            **repos,
        )

    @staticmethod
    def get_product_media_service(
        db: Session = Depends(get_db_session),
    ) -> ProductMediaService:
        repos = build_product_media_repositories(
            session=db,
        )
        return ProductMediaService(
            schemas=schemas,
            **repos,
        )

    @staticmethod
    def get_fornecedor_management_service(
        db: Session = Depends(get_db_session),
    ) -> FornecedorManagementService:
        return FornecedorManagementService(
            models=models,
            schemas=schemas,
            fornecedor_repo=FornecedorRepository(db),
            historico_repo=HistoricoRepository(db),
        )
