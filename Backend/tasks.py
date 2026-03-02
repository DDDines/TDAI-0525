"""Document tasks module responsibilities and runtime integration points."""

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

    """Represent Task Workflow and centralize its responsibilities inside this module."""
    def __init__(self, runtime: Optional["TaskRuntime"] = None) -> None:
        """Initialize injected dependencies and runtime configuration for Task Workflow."""
        self._runtime = runtime or TaskRuntime()

    def process_pdf_extraction_task(
        self,
        import_job_id: int,
        page_number: int,
    ) -> None:
        """Execute pdf extraction task and return the normalized execution result."""
        self._runtime.process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
        )


class TaskRuntime:

    """Represent Task Runtime and centralize its responsibilities inside this module."""
    def __init__(
        self,
        task_service: Optional[PdfExtractionTaskService] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Task Runtime."""
        if task_service is not None:
            self._task_service = task_service
            return

        service_container = ServiceContainer()
        self._task_service = PdfExtractionTaskService(
            session_provider=ServiceContainerDependencySupport.get_background_session_provider(),
            file_processing_service=service_container.file_processing,
        )

    def process_pdf_extraction_task(
        self,
        import_job_id: int,
        page_number: int,
    ) -> None:
        """Execute pdf extraction task and return the normalized execution result."""
        self._task_service.process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
        )
