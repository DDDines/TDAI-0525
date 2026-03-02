"""Servicos de aplicacao e composicao de dependencias para 'service_container'."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker
from Backend import database, models, schemas
from Backend.application.services.fornecedor_management_service import FornecedorManagementService
from Backend.application.services.file_processing import FileProcessingOrchestratorService
from Backend.application.services.ia_generation_service import IAGenerationService
from Backend.application.services.limit_service import LimitService
from Backend.application.services.product_management_service import ProductManagementService
from Backend.application.services.product_media_service import ProductMediaService
from Backend.application.services.product_repositories import ProductRepositories
from Backend.application.services.web_data_extractor import WebDataExtractorOrchestratorService
from Backend.infrastructure.adapters.file_processing_adapter import FileProcessingServiceAdapter
from Backend.infrastructure.adapters.ia_generation_adapter import IAGenerationServiceAdapter
from Backend.infrastructure.adapters.limit_adapter import LimitServiceAdapter
from Backend.infrastructure.adapters.web_data_extractor_adapter import WebDataExtractorServiceAdapter
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository

class _RequestScopedDependency:
    """Dependencia request-scoped OO parametrizada por factory de sessao."""

    def __init__(self, factory: Callable[[Session], Any]) -> None:
        """Initialize injected dependencies and runtime configuration for Request Scoped Dependency."""
        self._factory = factory

    def __call__(self, session: Session=Depends(database.get_db)) -> Any:
        """Execute call as part of this module workflow."""
        return self._factory(session)

class ServiceContainerDependencySupport:
    """Helpers OO de DI para composicao request-scoped de servicos."""

    @staticmethod
    def get_request_db_session(session: Session=Depends(database.get_db)) -> Session:
        """Retrieve request db session using the current service dependencies."""
        return session

    @staticmethod
    def build_request_scoped_dependency(factory: Callable[[Session], Any]) -> Callable[[Session], Any]:
        """Build request scoped dependency from current inputs and configuration."""
        return _RequestScopedDependency(factory)

    @staticmethod
    def build_file_processing_service() -> FileProcessingOrchestratorService:
        """Build file processing service from current inputs and configuration."""
        return FileProcessingOrchestratorService(FileProcessingServiceAdapter())

    @staticmethod
    def build_web_data_extractor_service() -> WebDataExtractorOrchestratorService:
        """Build web data extractor service from current inputs and configuration."""
        return WebDataExtractorOrchestratorService(WebDataExtractorServiceAdapter())

    @staticmethod
    def build_ia_generation_service() -> IAGenerationService:
        """Build ia generation service from current inputs and configuration."""
        return IAGenerationService(port=IAGenerationServiceAdapter())

    @staticmethod
    def build_limit_service() -> LimitService:
        """Build limit service from current inputs and configuration."""
        return LimitService(port=LimitServiceAdapter())

    @staticmethod
    def get_background_session_provider() -> "SessionProvider":
        """Retrieve background session provider using the current service dependencies."""
        return SessionProvider(database.SessionLocal)

    @staticmethod
    def build_background_session_provider_from_session(
        session: Session,
    ) -> "SessionProvider":
        """Build OO session provider bound to current request engine."""
        bind = session.get_bind()
        if bind is None:
            raise ValueError("Session bind is required to build background session provider.")
        return SessionProvider(sessionmaker(autocommit=False, autoflush=False, bind=bind))


class SessionProviderPort(Protocol):
    """OO contract to open SQLAlchemy sessions for background services."""

    def open_session(self) -> Session:
        """Open and return a session instance."""


class SessionProvider:
    """Concrete session provider backed by a session factory callable."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Store the session factory used to open request/background sessions."""
        self._session_factory = session_factory

    def open_session(self) -> Session:
        """Open a session using the configured factory."""
        return self._session_factory()
@dataclass
class ServiceContainer:
    """Registry simples de servicos OO compartilhados pela aplicacao."""
    file_processing: FileProcessingOrchestratorService = field(default_factory=ServiceContainerDependencySupport.build_file_processing_service)
    web_data_extractor: WebDataExtractorOrchestratorService = field(default_factory=ServiceContainerDependencySupport.build_web_data_extractor_service)
    ia_generation: IAGenerationService = field(default_factory=ServiceContainerDependencySupport.build_ia_generation_service)
    limit: LimitService = field(default_factory=ServiceContainerDependencySupport.build_limit_service)

class DependencyContainer:
    """Container de DI para dependencias request-scoped dos routers."""

    @staticmethod
    def get_db_session(session: Session) -> Session:
        """Retrieve db session using the current service dependencies."""
        return session

    @staticmethod
    def get_product_management_service(session: Session) -> ProductManagementService:
        """Retrieve product management service using the current service dependencies."""
        repos = ProductRepositories.build_product_management_repositories(session=session)
        return ProductManagementService(models=models, schemas=schemas, **repos)

    @staticmethod
    def get_product_media_service(session: Session) -> ProductMediaService:
        """Retrieve product media service using the current service dependencies."""
        repos = ProductRepositories.build_product_media_repositories(session=session)
        return ProductMediaService(schemas=schemas, **repos)

    @staticmethod
    def get_fornecedor_management_service(session: Session) -> FornecedorManagementService:
        """Retrieve fornecedor management service using the current service dependencies."""
        return FornecedorManagementService(models=models, schemas=schemas, fornecedor_repo=FornecedorRepository(session), historico_repo=HistoricoRepository(session))
