"""Module tasks.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Optional

from Backend.application.services.pdf_extraction_task_service import (
    PdfExtractionTaskService,
)
from Backend.application.services.service_container import (
    ServiceContainer,
    ServiceContainerDependencySupport,
)


class TaskWorkflow:

    """Class TaskWorkflow.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, runtime: Optional["TaskRuntime"] = None) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._runtime = runtime or TaskRuntime()

    def process_pdf_extraction_task(
        self,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ) -> None:
        """Execute process_pdf_extraction_task.

        This callable is documented to make behavior explicit for readers.
        """
        self._runtime.process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )


class TaskRuntime:

    """Class TaskRuntime.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(
        self,
        task_service: Optional[PdfExtractionTaskService] = None,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        if task_service is not None:
            self._task_service = task_service
            return

        service_container = ServiceContainer()
        self._task_service = PdfExtractionTaskService(
            db_session_factory=ServiceContainerDependencySupport.get_background_db_session_factory(),
            file_processing_service=service_container.file_processing,
        )

    def process_pdf_extraction_task(
        self,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ) -> None:
        """Execute process_pdf_extraction_task.

        This callable is documented to make behavior explicit for readers.
        """
        self._task_service.process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )
