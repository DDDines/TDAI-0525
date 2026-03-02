"""Module tasks.

Contains backend logic related to tasks and documents its role in the OOP architecture.
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

    """Represent task workflow and centralize responsibilities for this module."""
    def __init__(self, runtime: Optional["TaskRuntime"] = None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._runtime = runtime or TaskRuntime()

    def process_pdf_extraction_task(
        self,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ) -> None:
        """Process pdf extraction task for this workflow."""
        self._runtime.process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )


class TaskRuntime:

    """Represent task runtime and centralize responsibilities for this module."""
    def __init__(
        self,
        task_service: Optional[PdfExtractionTaskService] = None,
    ) -> None:
        """Initialize collaborators and configuration required by this component."""
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
        """Process pdf extraction task for this workflow."""
        self._task_service.process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )
